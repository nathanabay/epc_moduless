"""
Reports API Module

REST API endpoints for EPC financial reports generation.
Wires into dashboard_api.py patterns for consistency.
"""

import frappe
from frappe import _
from frappe.utils import today, now_datetime, flt, add_days
from frappe.desk.query_report import get_report_doc, generate_report
from epc_modules.utils import get_epc_logger

logger = get_epc_logger(__name__)


@frappe.whitelist()
def generate_financial_report(data):
    """
    Generate financial report based on report type and wizard data.

    Args:
        data (dict): Report configuration with keys:
            - wizard_name: Financial Report Wizard document name
            - report_type: Type of report to generate
            - project: Project name (optional)
            - wbs_item: WBS Item name (optional)
            - from_date: Start date for Cash Flow reports
            - to_date: End date for Cash Flow reports
            - include_archived: Include archived items
            - group_by: Grouping option (WBS, Cost Line, Job Type, None)
            - output_format: HTML, PDF, or Excel

    Returns:
        dict: Generated report data with success status
    """
    frappe.has_permission("Financial Report Wizard", "write", throw=True)

    wizard_name = data.get("wizard_name")
    report_type = data.get("report_type")

    if not wizard_name or not report_type:
        return {"success": False, "error": "Missing wizard name or report type"}

    wizard_doc = frappe.get_doc("Financial Report Wizard", wizard_name)

    try:
        # Generate report based on type
        if report_type == "Cash Flow":
            result = get_cash_flow_report(
                project=data.get("project"),
                from_date=data.get("from_date"),
                to_date=data.get("to_date")
            )
        elif report_type == "Cost Breakdown":
            result = get_cost_breakdown_report(
                project=data.get("project"),
                wbs_item=data.get("wbs_item"),
                group_by=data.get("group_by")
            )
        elif report_type == "Retention Summary":
            result = get_retention_summary_report(
                project=data.get("project")
            )
        elif report_type == "Billing Summary":
            result = get_billing_summary_report(
                project=data.get("project")
            )
        elif report_type == "Budget vs Actual":
            result = get_budget_variance(
                project=data.get("project")
            )
        elif report_type == "Change Order Summary":
            result = get_change_order_summary(
                project=data.get("project")
            )
        else:
            return {"success": False, "error": f"Unknown report type: {report_type}"}

        # Update wizard with results
        wizard_doc.db_set("status", "Generated")
        wizard_doc.db_set("generated_on", now_datetime())
        wizard_doc.db_set("report_data", frappe.as_json(result))
        wizard_doc.reload()

        return {"success": True, "report_type": report_type, "data": result}

    except Exception as e:
        logger.error(f"Error generating financial report: {str(e)}")
        wizard_doc.db_set("status", "Failed")
        wizard_doc.db_set("remarks", f"Error: {str(e)}")
        wizard_doc.reload()
        return {"success": False, "error": str(e)}


@frappe.whitelist()
def get_cash_flow_report(project=None, from_date=None, to_date=None):
    """
    Generate Cash Flow report based on RA Bill data.

    Args:
        project (str): Project name filter
        from_date (str): Start date
        to_date (str): End date

    Returns:
        dict: Cash flow report data
    """
    frappe.has_permission("RA Bill", "read", throw=True)

    filters = {"docstatus": 1}
    if project:
        filters["project"] = project
    if from_date:
        filters["billing_period_start"] = [">=", from_date]
    if to_date:
        filters["billing_period_end"] = ["<=", to_date]

    # Get RA bills with aggregation
    cash_flow_data = frappe.db.sql("""
        SELECT
            project,
            billing_period_start,
            billing_period_end,
            ra_bill_number,
            gross_certified_value,
            advance_recovered,
            net_certified_value,
            retention_amount,
            vat_amount,
            total_invoice_value,
            certification_date,
            status
        FROM `tabRA Bill`
        WHERE docstatus = 1
        {project_filter}
        {date_filter}
        ORDER BY billing_period_start ASC
    """.format(
        project_filter=f"AND project = '{project}'" if project else "",
        date_filter=f"AND billing_period_start >= '{from_date}' AND billing_period_end <= '{to_date}'" if from_date and to_date else ""
    ), as_dict=1)

    # Calculate aggregates
    total_inflow = sum(flt(r.get("total_invoice_value", 0)) for r in cash_flow_data)
    total_gross = sum(flt(r.get("gross_certified_value", 0)) for r in cash_flow_data)
    total_vat = sum(flt(r.get("vat_amount", 0)) for r in cash_flow_data)
    total_retention = sum(flt(r.get("retention_amount", 0)) for r in cash_flow_data)

    # Build monthly summary
    monthly_summary = {}
    for entry in cash_flow_data:
        month_key = entry.get("billing_period_start", "")[:7] if entry.get("billing_period_start") else "Unknown"
        if month_key not in monthly_summary:
            monthly_summary[month_key] = {
                "month": month_key,
                "bills_count": 0,
                "gross_value": 0,
                "net_value": 0,
                "vat": 0,
                "retention": 0,
                "invoice_value": 0
            }
        monthly_summary[month_key]["bills_count"] += 1
        monthly_summary[month_key]["gross_value"] += flt(entry.get("gross_certified_value", 0))
        monthly_summary[month_key]["net_value"] += flt(entry.get("net_certified_value", 0))
        monthly_summary[month_key]["vat"] += flt(entry.get("vat_amount", 0))
        monthly_summary[month_key]["retention"] += flt(entry.get("retention_amount", 0))
        monthly_summary[month_key]["invoice_value"] += flt(entry.get("total_invoice_value", 0))

    return {
        "report_type": "Cash Flow",
        "project": project,
        "from_date": from_date,
        "to_date": to_date,
        "generated_on": now_datetime(),
        "summary": {
            "total_ra_bills": len(cash_flow_data),
            "total_gross_value": total_gross,
            "total_net_value": total_gross - total_retention,
            "total_vat": total_vat,
            "total_retention": total_retention,
            "total_invoice_value": total_inflow
        },
        "monthly_summary": list(monthly_summary.values()),
        "details": cash_flow_data
    }


@frappe.whitelist()
def get_cost_breakdown_report(project=None, wbs_item=None, group_by="WBS"):
    """
    Generate Cost Breakdown report by grouping Custom BOQ items.

    Args:
        project (str): Project name filter
        wbs_item (str): WBS Item filter
        group_by (str): Grouping option (WBS, Cost Line, Job Type, None)

    Returns:
        dict: Cost breakdown report data
    """
    frappe.has_permission("Custom BOQ", "read", throw=True)

    filters = {}
    if project:
        filters["parent"] = project
    if wbs_item:
        filters["parent_wbs"] = wbs_item

    # Get BOQ items with cost breakdown
    boq_items = frappe.get_all(
        "Custom BOQ",
        filters=filters,
        fields=[
            "name", "item_code", "item_name", "description",
            "measurement_method", "boq_quantity", "uom",
            "unit_rate", "total_value", "parent_wbs",
            "billed_quantity", "pending_quantity", "status"
        ]
    )

    # Group by WBS or Cost Line or Job Type
    cost_breakdown = {}
    for item in boq_items:
        group_key = None
        if group_by == "WBS":
            group_key = item.get("parent_wbs") or "Ungrouped"
        elif group_by == "Cost Line":
            # Group by measurement method (as proxy for cost line)
            group_key = item.get("measurement_method") or "Other"
        elif group_by == "Job Type":
            # Group by status
            group_key = item.get("status") or "Unknown"

        if group_key not in cost_breakdown:
            cost_breakdown[group_key] = {
                "group": group_key,
                "items_count": 0,
                "total_quantity": 0,
                "total_value": 0,
                "billed_value": 0,
                "pending_value": 0
            }

        cost_breakdown[group_key]["items_count"] += 1
        cost_breakdown[group_key]["total_quantity"] += flt(item.get("boq_quantity", 0))
        cost_breakdown[group_key]["total_value"] += flt(item.get("total_value", 0))
        cost_breakdown[group_key]["billed_value"] += flt(item.get("billed_quantity", 0)) * flt(item.get("unit_rate", 0))
        cost_breakdown[group_key]["pending_value"] += flt(item.get("pending_quantity", 0)) * flt(item.get("unit_rate", 0))

    # Calculate totals
    total_value = sum(g.get("total_value", 0) for g in cost_breakdown.values())
    total_billed = sum(g.get("billed_value", 0) for g in cost_breakdown.values())
    total_pending = sum(g.get("pending_value", 0) for g in cost_breakdown.values())

    return {
        "report_type": "Cost Breakdown",
        "project": project,
        "wbs_item": wbs_item,
        "group_by": group_by,
        "generated_on": now_datetime(),
        "summary": {
            "total_items": len(boq_items),
            "total_groups": len(cost_breakdown),
            "total_boq_value": total_value,
            "total_billed_value": total_billed,
            "total_pending_value": total_pending,
            "billing_percentage": round((total_billed / total_value * 100) if total_value > 0 else 0, 2)
        },
        "breakdown": list(cost_breakdown.values()),
        "items": boq_items
    }


@frappe.whitelist()
def get_retention_summary_report(project=None):
    """
    Generate Retention Summary report from RA Bill data.

    Args:
        project (str): Project name filter

    Returns:
        dict: Retention summary report data
    """
    frappe.has_permission("RA Bill", "read", throw=True)

    filters = ["docstatus = 1"]
    if project:
        filters.append(f"project = '{project}'")

    where_clause = " AND ".join(filters) if len(filters) > 1 else filters[0]

    # Get retention data from RA bills
    retention_data = frappe.db.sql("""
        SELECT
            project,
            ra_bill_number,
            certification_date,
            gross_certified_value,
            retention_percentage,
            retention_amount,
            net_payable,
            status
        FROM `tabRA Bill`
        WHERE {where_clause}
        ORDER BY certification_date ASC
    """.format(where_clause=where_clause), as_dict=1)

    # Aggregate retention by project
    project_retention = {}
    total_retention = 0
    for entry in retention_data:
        proj = entry.get("project") or "Unknown"
        ret_amount = flt(entry.get("retention_amount", 0))
        total_retention += ret_amount

        if proj not in project_retention:
            project_retention[proj] = {
                "project": proj,
                "bills_count": 0,
                "total_certified_value": 0,
                "total_retention": 0,
                "avg_retention_pct": 0
            }

        project_retention[proj]["bills_count"] += 1
        project_retention[proj]["total_certified_value"] += flt(entry.get("gross_certified_value", 0))
        project_retention[proj]["total_retention"] += ret_amount

    # Calculate average retention percentage
    for proj_data in project_retention.values():
        if proj_data["total_certified_value"] > 0:
            proj_data["avg_retention_pct"] = round(
                (proj_data["total_retention"] / proj_data["total_certified_value"] * 100), 2
            )

    return {
        "report_type": "Retention Summary",
        "project": project,
        "generated_on": now_datetime(),
        "summary": {
            "total_ra_bills": len(retention_data),
            "total_projects": len(project_retention),
            "total_retention_held": total_retention,
            "total_certified_value": sum(p.get("total_certified_value", 0) for p in project_retention.values())
        },
        "by_project": list(project_retention.values()),
        "details": retention_data
    }


@frappe.whitelist()
def get_billing_summary_report(project=None):
    """
    Generate Billing Summary report from RA Bill data.

    Args:
        project (str): Project name filter

    Returns:
        dict: Billing summary report data
    """
    frappe.has_permission("RA Bill", "read", throw=True)

    filters = ["docstatus = 1"]
    if project:
        filters.append(f"project = '{project}'")

    where_clause = " AND ".join(filters) if len(filters) > 1 else filters[0]

    # Get billing summary data
    billing_data = frappe.db.sql("""
        SELECT
            project,
            ra_bill_number,
            billing_period_start,
            billing_period_end,
            gross_certified_value,
            advance_recovered,
            cumulative_advance_recovered,
            net_certified_value,
            retention_amount,
            vat_amount,
            total_invoice_value,
            certification_date,
            status
        FROM `tabRA Bill`
        WHERE {where_clause}
        ORDER BY billing_period_start ASC
    """.format(where_clause=where_clause), as_dict=1)

    # Aggregate by project
    project_billing = {}
    for entry in billing_data:
        proj = entry.get("project") or "Unknown"

        if proj not in project_billing:
            project_billing[proj] = {
                "project": proj,
                "bills_count": 0,
                "total_certified": 0,
                "total_invoice": 0,
                "total_vat": 0,
                "total_retention": 0,
                "total_advance_recovered": 0
            }

        project_billing[proj]["bills_count"] += 1
        project_billing[proj]["total_certified"] += flt(entry.get("gross_certified_value", 0))
        project_billing[proj]["total_invoice"] += flt(entry.get("total_invoice_value", 0))
        project_billing[proj]["total_vat"] += flt(entry.get("vat_amount", 0))
        project_billing[proj]["total_retention"] += flt(entry.get("retention_amount", 0))
        project_billing[proj]["total_advance_recovered"] += flt(entry.get("advance_recovered", 0))

    # Calculate grand totals
    total_certified = sum(p.get("total_certified", 0) for p in project_billing.values())
    total_invoice = sum(p.get("total_invoice", 0) for p in project_billing.values())
    total_vat = sum(p.get("total_vat", 0) for p in project_billing.values())
    total_retention = sum(p.get("total_retention", 0) for p in project_billing.values())

    return {
        "report_type": "Billing Summary",
        "project": project,
        "generated_on": now_datetime(),
        "summary": {
            "total_ra_bills": len(billing_data),
            "total_projects": len(project_billing),
            "total_certified_value": total_certified,
            "total_invoice_value": total_invoice,
            "total_vat": total_vat,
            "total_retention": total_retention,
            "net_revenue": total_invoice - total_vat
        },
        "by_project": list(project_billing.values()),
        "details": billing_data
    }


@frappe.whitelist()
def get_budget_variance(project=None):
    """
    Generate Budget vs Actual variance report.
    Compares WBS Item planned values against Custom BOQ actuals.

    Args:
        project (str): Project name filter

    Returns:
        dict: Budget variance report data
    """
    frappe.has_permission("WBS Item", "read", throw=True)

    filters = {}
    if project:
        filters["project"] = project

    # Get WBS items with budget data
    wbs_items = frappe.get_all(
        "WBS Item",
        filters=filters,
        fields=[
            "name", "wbs_code", "item_name", "project",
            "planned_value", "planned_start", "planned_end",
            "actual_value", "actual_start", "actual_end",
            "physical_progress", "status"
        ]
    )

    # Get BOQ actuals
    boq_actuals = {}
    if project:
        boq_items = frappe.get_all(
            "Custom BOQ",
            filters={"parent": project},
            fields=["parent_wbs", "total_value", "billed_quantity", "unit_rate"]
        )
        for item in boq_items:
            wbs = item.get("parent_wbs")
            if wbs:
                if wbs not in boq_actuals:
                    boq_actuals[wbs] = {
                        "total_boq_value": 0,
                        "billed_value": 0
                    }
                boq_actuals[wbs]["total_boq_value"] += flt(item.get("total_value", 0))
                boq_actuals[wbs]["billed_value"] += flt(item.get("billed_quantity", 0)) * flt(item.get("unit_rate", 0))

    # Calculate variance
    variance_data = []
    for wbs in wbs_items:
        planned = flt(wbs.get("planned_value", 0))
        actual = flt(wbs.get("actual_value", 0))
        boq_billed = boq_actuals.get(wbs.name, {}).get("billed_value", 0)

        # Use actual_value or fall back to boq_billed
        actual_value = actual if actual > 0 else boq_billed

        variance = actual_value - planned
        variance_pct = (variance / planned * 100) if planned > 0 else 0

        variance_data.append({
            "wbs_code": wbs.get("wbs_code"),
            "wbs_name": wbs.get("item_name"),
            "project": wbs.get("project"),
            "planned_value": planned,
            "actual_value": actual_value,
            "variance": variance,
            "variance_percentage": round(variance_pct, 2),
            "status": wbs.get("status"),
            "physical_progress": wbs.get("physical_progress", 0)
        })

    # Calculate summary
    total_planned = sum(v.get("planned_value", 0) for v in variance_data)
    total_actual = sum(v.get("actual_value", 0) for v in variance_data)
    total_variance = total_actual - total_planned

    return {
        "report_type": "Budget vs Actual",
        "project": project,
        "generated_on": now_datetime(),
        "summary": {
            "total_wbs_items": len(variance_data),
            "total_planned_value": total_planned,
            "total_actual_value": total_actual,
            "total_variance": total_variance,
            "variance_percentage": round((total_variance / total_planned * 100) if total_planned > 0 else 0, 2),
            "over_budget_count": sum(1 for v in variance_data if v.get("variance", 0) > 0),
            "under_budget_count": sum(1 for v in variance_data if v.get("variance", 0) < 0)
        },
        "variance": variance_data
    }


@frappe.whitelist()
def get_change_order_summary(project=None):
    """
    Generate Change Order Summary report.

    Args:
        project (str): Project name filter

    Returns:
        dict: Change order summary report data
    """
    frappe.has_permission("Claim Register", "read", throw=True)

    filters = {}
    if project:
        filters["project"] = project

    # Get change orders (using Claim Register as proxy for change orders)
    change_orders = frappe.get_all(
        "Claim Register",
        filters=filters,
        fields=[
            "name", "claim_number", "project", "claim_type",
            "claim_amount", "status", "claim_date",
            "party", "description"
        ]
    )

    # Group by claim type (change order types)
    by_type = {}
    for order in change_orders:
        claim_type = order.get("claim_type") or "Unknown"

        if claim_type not in by_type:
            by_type[claim_type] = {
                "type": claim_type,
                "count": 0,
                "total_amount": 0,
                "approved_amount": 0,
                "pending_amount": 0
            }

        amount = flt(order.get("claim_amount", 0))
        by_type[claim_type]["count"] += 1
        by_type[claim_type]["total_amount"] += amount

        if order.get("status") in ["Approved", "Certified"]:
            by_type[claim_type]["approved_amount"] += amount
        elif order.get("status") in ["Pending", "Submitted", "Under Review"]:
            by_type[claim_type]["pending_amount"] += amount

    # Status summary
    by_status = {}
    for order in change_orders:
        status = order.get("status") or "Unknown"
        if status not in by_status:
            by_status[status] = {"status": status, "count": 0, "amount": 0}
        by_status[status]["count"] += 1
        by_status[status]["amount"] += flt(order.get("claim_amount", 0))

    return {
        "report_type": "Change Order Summary",
        "project": project,
        "generated_on": now_datetime(),
        "summary": {
            "total_change_orders": len(change_orders),
            "total_amount": sum(flt(o.get("claim_amount", 0)) for o in change_orders),
            "total_approved": sum(flt(t.get("approved_amount", 0)) for t in by_type.values()),
            "total_pending": sum(flt(t.get("pending_amount", 0)) for t in by_type.values())
        },
        "by_type": list(by_type.values()),
        "by_status": list(by_status.values()),
        "details": change_orders
    }


@frappe.whitelist()
def export_to_excel(data, filename="Financial_Report"):
    """
    Export report data to Excel format.

    Args:
        data (dict): Report data to export
        filename (str): Output filename without extension

    Returns:
        dict: File URL on success
    """
    frappe.has_permission("Financial Report Wizard", "read", throw=True)

    import json
    from frappe.utils.xlsxutils import make_xlsx

    try:
        # Convert data to worksheet format
        worksheet_data = []

        if "details" in data:
            # Standard detail format
            for row in data["details"]:
                worksheet_data.append(row)
        elif "variance" in data:
            for row in data["variance"]:
                worksheet_data.append(row)
        elif "breakdown" in data:
            for row in data["breakdown"]:
                worksheet_data.append(row)

        # Create xlsx
        xlsx_file = make_xlsx(
            [worksheet_data],
            filename,
            incl_header=True
        )

        return {"success": True, "file_url": xlsx_file}

    except Exception as e:
        logger.error(f"Error exporting to Excel: {str(e)}")
        return {"success": False, "error": str(e)}


@frappe.whitelist()
def get_report_preview(report_type, project=None):
    """
    Get a preview of report data without saving.

    Args:
        report_type (str): Type of report
        project (str): Project name

    Returns:
        dict: Report preview data
    """
    if report_type == "Cash Flow":
        return get_cash_flow_report(project=project, from_date=None, to_date=None)
    elif report_type == "Cost Breakdown":
        return get_cost_breakdown_report(project=project)
    elif report_type == "Retention Summary":
        return get_retention_summary_report(project=project)
    elif report_type == "Billing Summary":
        return get_billing_summary_report(project=project)
    elif report_type == "Budget vs Actual":
        return get_budget_variance(project=project)
    elif report_type == "Change Order Summary":
        return get_change_order_summary(project=project)
    else:
        return {"error": f"Unknown report type: {report_type}"}