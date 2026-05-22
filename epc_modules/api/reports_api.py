"""
Reports API Module

REST API endpoints for EPC financial reports generation.
Wires into dashboard_api.py patterns for consistency.
"""

import frappe
from frappe import _
from frappe.utils import today, now_datetime, flt, add_days, date_diff
from frappe.desk.query_report import get_report_doc, generate_report
from epc_modules.utils import get_epc_logger

logger = get_epc_logger(__name__)


# =============================================================================
# Caching Helpers
# =============================================================================

def _get_cached_ref_data(cache_key, generator_fn, ttl=300):
    """
    Get cached reference data or generate and cache it.

    Args:
        cache_key: Unique cache key string
        generator_fn: Callable that returns the data to cache
        ttl: Time-to-live in seconds (default 5 minutes)

    Returns:
        Cached or freshly generated data
    """
    cache = frappe.cache()
    cached = cache.get_value(cache_key)
    if cached is not None:
        return cached

    data = generator_fn()
    cache.set_value(cache_key, data, expires_in_sec=ttl)
    return data


def _invalidate_ref_cache(*keys):
    """Invalidate cached reference data by keys."""
    cache = frappe.cache()
    for key in keys:
        cache.delete_value(key)


# =============================================================================
# Financial Report Functions
# =============================================================================

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

    if not isinstance(data, dict):
        frappe.throw(_("Invalid data: expected a dictionary"))

    wizard_name = data.get("wizard_name")
    report_type = data.get("report_type")

    if not wizard_name or not report_type:
        frappe.throw(_("Missing wizard name or report type"))

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
            frappe.throw(_("Unknown report type: {0}").format(report_type))

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
def get_cash_flow_report(project=None, from_date=None, to_date=None, limit=500):
    """
    Generate Cash Flow report based on RA Bill data.

    Args:
        project (str): Project name filter
        from_date (str): Start date
        to_date (str): End date
        limit (int): Maximum records to return (default 500, capped at 500)

    Returns:
        dict: Cash flow report data
    """
    frappe.has_permission("RA Bill", "read", throw=True)

    # Cap limit at 500 to prevent excessive data retrieval
    limit = min(int(limit or 500), 500)

    filters = {"docstatus": 1}
    if project:
        filters["project"] = project
    if from_date:
        filters["billing_period_start"] = [">=", from_date]
    if to_date:
        filters["billing_period_end"] = ["<=", to_date]

    # Get RA bills with aggregation - use parameterized queries to prevent SQL injection
    query_params = []
    conditions = ["docstatus = 1"]
    if project:
        conditions.append("project = %s")
        query_params.append(project)
    if from_date:
        conditions.append("billing_period_start >= %s")
        query_params.append(from_date)
    if to_date:
        conditions.append("billing_period_end <= %s")
        query_params.append(to_date)

    where_clause = " AND ".join(conditions)
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
        WHERE """ + where_clause + """
        ORDER BY billing_period_start ASC
        LIMIT %(limit)s
    """, tuple(query_params) + ({"limit": limit},), as_dict=1)

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

    # Get BOQ items with cost breakdown (capped at 100 records)
    boq_items = frappe.get_all(
        "Custom BOQ",
        filters=filters,
        fields=[
            "name", "item_code", "item_name", "description",
            "measurement_method", "boq_quantity", "uom",
            "unit_rate", "total_value", "parent_wbs",
            "billed_quantity", "pending_quantity", "status"
        ],
        limit_page_length=100
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
def get_retention_summary_report(project=None, limit=100):
    """
    Generate Retention Summary report from RA Bill data.

    Args:
        project (str): Project name filter
        limit (int): Maximum records to return (default 100, capped at 100)

    Returns:
        dict: Retention summary report data
    """
    frappe.has_permission("RA Bill", "read", throw=True)

    # Cap limit at 100 to prevent excessive data retrieval
    limit = min(int(limit or 100), 100)

    # Use parameterized queries to prevent SQL injection
    query_params = ["docstatus = 1"]
    params = []
    if project:
        query_params.append("project = %s")
        params.append(project)

    where_clause = " AND ".join(query_params)

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
        WHERE """ + where_clause + """
        ORDER BY certification_date ASC
        LIMIT %(limit)s
    """, tuple(params) + ({"limit": limit},), as_dict=1)

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
def get_billing_summary_report(project=None, limit=100):
    """
    Generate Billing Summary report from RA Bill data.

    Args:
        project (str): Project name filter
        limit (int): Maximum records to return (default 100, capped at 100)

    Returns:
        dict: Billing summary report data
    """
    frappe.has_permission("RA Bill", "read", throw=True)

    # Cap limit at 100 to prevent excessive data retrieval
    limit = min(int(limit or 100), 100)

    # Use parameterized queries to prevent SQL injection
    query_params = ["docstatus = 1"]
    params = []
    if project:
        query_params.append("project = %s")
        params.append(project)

    where_clause = " AND ".join(query_params)

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
        WHERE """ + where_clause + """
        ORDER BY billing_period_start ASC
        LIMIT %(limit)s
    """, tuple(params) + ({"limit": limit},), as_dict=1)

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

    # Get WBS items with budget data (capped at 100 records)
    wbs_items = frappe.get_all(
        "WBS Item",
        filters=filters,
        fields=[
            "name", "wbs_code", "item_name", "project",
            "planned_value", "planned_start", "planned_end",
            "actual_value", "actual_start", "actual_end",
            "physical_progress", "status"
        ],
        limit_page_length=100
    )

    # Get BOQ actuals with caching for reference data
    boq_actuals = {}
    if project:
        def get_boq_actuals():
            boq_items = frappe.get_all(
                "Custom BOQ",
                filters={"parent": project},
                fields=["parent_wbs", "total_value", "billed_quantity", "unit_rate"],
                limit_page_length=100
            )
            result = {}
            for item in boq_items:
                wbs = item.get("parent_wbs")
                if wbs:
                    if wbs not in result:
                        result[wbs] = {"total_boq_value": 0, "billed_value": 0}
                    result[wbs]["total_boq_value"] += flt(item.get("total_value", 0))
                    result[wbs]["billed_value"] += flt(item.get("billed_quantity", 0)) * flt(item.get("unit_rate", 0))
            return result

        boq_actuals = _get_cached_ref_data(
            f"boq_actuals_{project}",
            get_boq_actuals,
            ttl=600  # 10 minutes for project-specific data
        )

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

    # Get change orders (using Claim Register as proxy for change orders) (capped at 100 records)
    change_orders = frappe.get_all(
        "Claim Register",
        filters=filters,
        fields=[
            "name", "claim_number", "project", "claim_type",
            "claim_amount", "status", "claim_date",
            "party", "description"
        ],
        limit_page_length=100
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
    import os
    from frappe.utils.xlsxutils import make_xlsx

    try:
        # Build multiple worksheets from all report sections
        worksheets = []

        # Section key -> display name mapping (cost_lines removed - no report returns it)
        section_keys = [
            ("summary", "Summary"),
            ("monthly_summary", "Monthly Summary"),
            ("by_project", "By Project"),
            ("details", "Details"),
            ("breakdown", "Breakdown"),
            ("variance", "Variance"),
            ("by_type", "By Type"),
            ("by_status", "By Status"),
        ]

        for key, sheet_name in section_keys:
            if key in data and isinstance(data[key], list):
                # Convert list of dicts to list of lists for make_xlsx
                rows = []
                if data[key]:
                    # Header row from first item's keys
                    headers = list(data[key][0].keys())
                    rows.append(headers)
                    for row in data[key]:
                        rows.append([row.get(h, "") for h in headers])
                worksheets.append((sheet_name, rows))

        # Fallback: if no sections found, dump the whole data as single sheet
        if not worksheets:
            rows = []
            if isinstance(data, dict):
                for k, v in data.items():
                    if isinstance(v, list):
                        for row in v:
                            rows.append(row)
                    else:
                        rows.append({k: v})
            if rows and isinstance(rows[0], dict):
                headers = list(rows[0].keys())
                rows = [headers] + [[r.get(h, "") for h in headers] for r in rows]
            worksheets.append(("Report", rows or [[]]))

        # Create xlsx with multiple sheets
        xlsx_file = make_xlsx(
            worksheets,
            filename,
            incl_header=True
        )

        # Write xlsx to private files directory and return URL
        timestamp = frappe.utils.now().strftime('%Y%m%d_%H%M%S')
        safe_filename = f"{filename}_{timestamp}.xlsx"
        private_dir = frappe.get_site_path("private", "files")
        os.makedirs(private_dir, exist_ok=True)
        file_path = os.path.join(private_dir, safe_filename)
        with open(file_path, "wb") as f:
            f.write(xlsx_file)
        file_url = f"/private/files/{safe_filename}"

        return {"success": True, "file_url": file_url}

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
    frappe.has_permission("Financial Report Wizard", "read", throw=True)

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
        frappe.throw(_("Unknown report type: {0}").format(report_type))


# =============================================================================
# Project Report Functions
# =============================================================================

@frappe.whitelist()
def generate_project_report(data):
    """
    Generate project report based on report type and wizard data.

    Args:
        data (dict): Report configuration with keys:
            - wizard_name: Project Report Wizard document name
            - report_type: Type of report to generate
            - project: Project name
            - typology_filter: Project Typology filter
            - from_date: Start date
            - to_date: End date
            - include_wbs: Include WBS details
            - include_ncrs: Include NCR details
            - output_format: HTML, PDF, or Excel

    Returns:
        dict: Generated report data with success status
    """
    frappe.has_permission("Project Report Wizard", "write", throw=True)

    if not isinstance(data, dict):
        frappe.throw(_("Invalid data: expected a dictionary"))

    wizard_name = data.get("wizard_name")
    report_type = data.get("report_type")

    if not wizard_name or not report_type:
        frappe.throw(_("Missing wizard name or report type"))

    wizard_doc = frappe.get_doc("Project Report Wizard", wizard_name)

    try:
        # Generate report based on type
        if report_type == "Project Status":
            result = get_project_status_report(project=data.get("project"))
        elif report_type == "WIP Report":
            result = get_wip_report(
                project=data.get("project"),
                include_wbs=data.get("include_wbs")
            )
        elif report_type == "NCR Summary":
            result = get_ncr_summary_report(
                project=data.get("project"),
                from_date=data.get("from_date"),
                to_date=data.get("to_date"),
                include_details=data.get("include_ncrs")
            )
        elif report_type == "DPR Summary":
            result = get_dpr_summary_report(
                project=data.get("project"),
                from_date=data.get("from_date"),
                to_date=data.get("to_date")
            )
        elif report_type == "RFI Log":
            result = get_rfi_log_report(
                project=data.get("project"),
                from_date=data.get("from_date"),
                to_date=data.get("to_date")
            )
        elif report_type == "Inspection Status":
            result = get_inspection_status_report(
                project=data.get("project"),
                include_ncrs=data.get("include_ncrs")
            )
        elif report_type == "Equipment Utilization":
            result = get_equipment_utilization_report(
                project=data.get("project")
            )
        elif report_type == "Team Performance":
            result = get_team_performance_report(
                project=data.get("project"),
                from_date=data.get("from_date"),
                to_date=data.get("to_date")
            )
        else:
            frappe.throw(_("Unknown report type: {0}").format(report_type))

        # Update wizard with results
        wizard_doc.db_set("status", "Generated")
        wizard_doc.db_set("generated_on", now_datetime())
        wizard_doc.db_set("report_data", frappe.as_json(result))
        wizard_doc.reload()

        return {"success": True, "report_type": report_type, "data": result}

    except Exception as e:
        logger.error(f"Error generating project report: {str(e)}")
        wizard_doc.db_set("status", "Failed")
        wizard_doc.reload()
        return {"success": False, "error": str(e)}


@frappe.whitelist()
def get_project_status_report(project):
    """
    Generate Project Status report using dashboard KPIs.

    Args:
        project (str): Project name

    Returns:
        dict: Project status report data
    """
    frappe.has_permission("Project", "read", throw=True)

    if not project:
        frappe.throw(_("Project is required"))

    if not frappe.db.exists("Project", project):
        frappe.throw(_("Project {0} does not exist").format(project))

    # Delegate to dashboard API for KPIs
    from epc_modules.api.dashboard_api import get_project_dashboard_kpis

    kpis = get_project_dashboard_kpis(project)

    # Get additional project info
    project_doc = frappe.get_doc("Project", project)

    # Get typology info
    typology_info = {}
    if project_doc.project_typology:
        typology = frappe.get_doc("Project Typology", project_doc.project_typology)
        typology_info = {
            "name": typology.typology_name,
            "type": typology.typology_type,
            "billing_track": typology.billing_track
        }

    return {
        "report_type": "Project Status",
        "project": project,
        "project_name": project_doc.project_name,
        "generated_on": now_datetime(),
        "summary": {
            "status": project_doc.status,
            "percent_complete": kpis.get("progress", {}).get("percent_complete", 0),
            "total_boq_value": kpis.get("progress", {}).get("total_boq_value", 0),
            "wbs_items": kpis.get("progress", {}).get("wbs_items", 0),
            "completed_wbs": kpis.get("progress", {}).get("completed_wbs", 0),
            "in_progress_wbs": kpis.get("progress", {}).get("in_progress_wbs", 0),
            "open_ncrs": kpis.get("quality", {}).get("open_ncrs", 0),
            "critical_ncrs": kpis.get("quality", {}).get("critical_ncrs", 0),
            "is_blocked": kpis.get("quality", {}).get("is_blocked", False),
            "certified_mbs": kpis.get("measurement_books", {}).get("certified", 0),
            "pending_mbs": kpis.get("measurement_books", {}).get("pending", 0),
            "labor_today": kpis.get("resources", {}).get("labor_today", 0)
        },
        "details": kpis
    }


@frappe.whitelist()
def get_wip_report(project, include_wbs=False):
    """
    Generate WIP (Work In Progress) report from WBS Items.

    Args:
        project (str): Project name
        include_wbs (bool): Include detailed WBS items

    Returns:
        dict: WIP report data
    """
    frappe.has_permission("WBS Item", "read", throw=True)

    if not project:
        frappe.throw(_("Project is required"))

    # Get WBS items with cost and progress data (capped at 100 records)
    wbs_items = frappe.get_all(
        "WBS Item",
        filters={"project": project},
        fields=[
            "name", "wbs_code", "wbs_name", "parent_wbs", "wbs_level",
            "planned_value", "earned_value", "cost_incurred",
            "physical_progress", "wbs_status",
            "planned_start", "planned_end", "actual_start", "actual_end"
        ],
        order_by="wbs_code asc",
        limit_page_length=100
    )

    # Calculate aggregates
    total_planned = sum(flt(w.get("planned_value", 0)) for w in wbs_items)
    total_earned = sum(flt(w.get("earned_value", 0)) for w in wbs_items)
    total_cost = sum(flt(w.get("cost_incurred", 0)) for w in wbs_items)
    avg_progress = sum(flt(w.get("physical_progress", 0)) for w in wbs_items) / len(wbs_items) if wbs_items else 0

    # Group by status
    by_status = {}
    for wbs in wbs_items:
        status = wbs.get("wbs_status") or "Unknown"
        if status not in by_status:
            by_status[status] = {
                "status": status,
                "count": 0,
                "planned_value": 0,
                "earned_value": 0,
                "cost_incurred": 0
            }
        by_status[status]["count"] += 1
        by_status[status]["planned_value"] += flt(wbs.get("planned_value", 0))
        by_status[status]["earned_value"] += flt(wbs.get("earned_value", 0))
        by_status[status]["cost_incurred"] += flt(wbs.get("cost_incurred", 0))

    # Calculate schedule variance (days)
    schedule_analysis = []
    for wbs in wbs_items:
        if wbs.get("planned_end") and wbs.get("actual_end"):
            planned_days = (wbs.planned_end - wbs.planned_start).days if wbs.planned_start else 0
            actual_days = (wbs.actual_end - wbs.actual_start).days if wbs.actual_start else 0
            schedule_variance = actual_days - planned_days
            schedule_analysis.append({
                "wbs_code": wbs.get("wbs_code"),
                "wbs_name": wbs.get("wbs_name"),
                "status": wbs.get("wbs_status"),
                "planned_days": planned_days,
                "actual_days": actual_days,
                "variance_days": schedule_variance,
                "is_delayed": schedule_variance > 0
            })

    return {
        "report_type": "WIP Report",
        "project": project,
        "generated_on": now_datetime(),
        "summary": {
            "total_wbs_items": len(wbs_items),
            "total_planned_value": total_planned,
            "total_earned_value": total_earned,
            "total_cost_incurred": total_cost,
            "cost_variance": total_earned - total_cost,
            "avg_physical_progress": round(avg_progress, 2),
            "schedule_variance_pct": round(((total_earned - total_planned) / total_planned * 100) if total_planned > 0 else 0, 2),
            "cost_variance_pct": round(((total_cost - total_earned) / total_earned * 100) if total_earned > 0 else 0, 2)
        },
        "by_status": list(by_status.values()),
        "schedule_analysis": schedule_analysis,
        "details": wbs_items if include_wbs else []
    }


@frappe.whitelist()
def get_ncr_summary_report(project, from_date=None, to_date=None, include_details=False):
    """
    Generate NCR Summary report from Non-Conformance Reports.

    Args:
        project (str): Project name
        from_date (str): Start date filter
        to_date (str): End date filter
        include_details (bool): Include NCR detail records

    Returns:
        dict: NCR summary report data
    """
    frappe.has_permission("Non-Conformance Report", "read", throw=True)

    if not project:
        frappe.throw(_("Project is required"))

    # Build query filters - use parameterized queries to prevent SQL injection
    query_params = []
    conditions = ["project = %s"]
    query_params.append(project)
    if from_date:
        conditions.append("identified_date >= %s")
        query_params.append(from_date)
    if to_date:
        conditions.append("identified_date <= %s")
        query_params.append(to_date)

    where_clause = " AND ".join(conditions)

    # Get all NCR statistics in a single query using UNION ALL
    ncr_all = frappe.db.sql("""
        SELECT status, severity, COUNT(*) as count
        FROM `tabNon-Conformance Report`
        WHERE """ + where_clause + """
        GROUP BY status, severity
        UNION ALL
        SELECT status, NULL as severity, COUNT(*) as count
        FROM `tabNon-Conformance Report`
        WHERE """ + where_clause + """
        GROUP BY status
    """, tuple(query_params) + tuple(query_params), as_dict=1)

    # Separate by grouping type
    ncr_stats = [r for r in ncr_all if r.severity is not None]
    ncr_by_status = [r for r in ncr_all if r.severity is None]

    # Aggregate statistics
    ncr_summary = {
        "total": 0,
        "open": 0,
        "in_progress": 0,
        "closed": 0,
        "verified": 0,
        "critical": 0,
        "major": 0,
        "minor": 0
    }

    for stat in ncr_stats:
        ncr_summary["total"] += stat.count
        if stat.status == "Open":
            ncr_summary["open"] += stat.count
        elif stat.status == "In Progress":
            ncr_summary["in_progress"] += stat.count
        elif stat.status == "Closed":
            ncr_summary["closed"] += stat.count
        elif stat.status == "Verified":
            ncr_summary["verified"] += stat.count

        if stat.severity == "Critical":
            ncr_summary["critical"] += stat.count
        elif stat.severity == "Major":
            ncr_summary["major"] += stat.count
        elif stat.severity == "Minor":
            ncr_summary["minor"] += stat.count

    # Build by-status breakdown
    by_status = {}
    for stat in ncr_by_status:
        by_status[stat.status] = {
            "status": stat.status,
            "count": stat.count
        }

    # Get detailed NCR records if requested
    details = []
    if include_details:
        details = frappe.get_all(
            "Non-Conformance Report",
            filters={"project": project},
            fields=[
                "name", "ncr_number", "description", "severity",
                "status", "identified_date", "target_close_date",
                "actual_close_date", "closed_by"
            ],
            order_by="identified_date desc",
            limit_page_length=100
        )

    return {
        "report_type": "NCR Summary",
        "project": project,
        "from_date": from_date,
        "to_date": to_date,
        "generated_on": now_datetime(),
        "summary": ncr_summary,
        "by_status": list(by_status.values()),
        "details": details
    }


@frappe.whitelist()
def get_dpr_summary_report(project, from_date=None, to_date=None):
    """
    Generate DPR Summary report from Daily Progress Reports.

    Args:
        project (str): Project name
        from_date (str): Start date filter
        to_date (str): End date filter

    Returns:
        dict: DPR summary report data
    """
    frappe.has_permission("Daily Progress Report", "read", throw=True)

    if not project:
        frappe.throw(_("Project is required"))

    # Build query filters - use parameterized queries to prevent SQL injection
    query_params = []
    conditions = ["project = %s"]
    query_params.append(project)
    if from_date:
        conditions.append("report_date >= %s")
        query_params.append(from_date)
    if to_date:
        conditions.append("report_date <= %s")
        query_params.append(to_date)

    where_clause = " AND ".join(conditions)

    # Combine all DPR aggregations in a single query using CTE
    dpr_stats = frappe.db.sql("""
        WITH dpr_cte AS (
            SELECT
                report_date,
                status,
                COALESCE(weather_conditions, 'Unknown') as weather_conditions,
                labor_count,
                equipment_count,
                overall_progress
            FROM `tabDaily Progress Report`
            WHERE """ + where_clause + """
        )
        SELECT
            'daily' as agg_type,
            report_date,
            NULL as stat_value,
            COUNT(*) as entry_count,
            SUM(labor_count) as total_labor,
            SUM(equipment_count) as total_equipment,
            AVG(overall_progress) as avg_progress
        FROM dpr_cte
        GROUP BY report_date
        UNION ALL
        SELECT
            'status' as agg_type,
            NULL as report_date,
            status as stat_value,
            COUNT(*) as count,
            0 as total_labor,
            0 as total_equipment,
            0 as avg_progress
        FROM dpr_cte
        GROUP BY status
        UNION ALL
        SELECT
            'weather' as agg_type,
            NULL as report_date,
            weather_conditions as stat_value,
            COUNT(*) as count,
            0 as total_labor,
            0 as total_equipment,
            0 as avg_progress
        FROM dpr_cte
        WHERE weather_conditions IS NOT NULL
        GROUP BY weather_conditions
    """, tuple(query_params), as_dict=1)

    # Separate into grouped data
    dpr_data = []
    dpr_by_status = []
    weather_stats = []

    for row in dpr_stats:
        if row.agg_type == 'daily':
            dpr_data.append(row)
        elif row.agg_type == 'status':
            dpr_by_status.append(row)
        elif row.agg_type == 'weather':
            weather_stats.append(row)

    # Calculate totals
    total_entries = len(dpr_data)
    total_labor = sum(flt(d.get("total_labor", 0)) for d in dpr_data)
    total_equipment = sum(flt(d.get("total_equipment", 0)) for d in dpr_data)
    avg_daily_labor = total_labor / total_entries if total_entries > 0 else 0
    avg_daily_equipment = total_equipment / total_entries if total_entries > 0 else 0

    # Build by-status breakdown
    by_status = {}
    for stat in dpr_by_status:
        by_status[stat.stat_value] = {
            "status": stat.stat_value,
            "count": stat.count
        }

    by_weather = []
    for stat in weather_stats:
        by_weather.append({
            "weather": stat.stat_value,
            "count": stat.count
        })

    return {
        "report_type": "DPR Summary",
        "project": project,
        "from_date": from_date,
        "to_date": to_date,
        "generated_on": now_datetime(),
        "summary": {
            "total_entries": total_entries,
            "total_labor_days": int(total_labor),
            "total_equipment_days": int(total_equipment),
            "avg_daily_labor": round(avg_daily_labor, 1),
            "avg_daily_equipment": round(avg_daily_equipment, 1),
            "submission_rate": round((by_status.get("Submitted", {}).get("count", 0) / total_entries * 100) if total_entries > 0 else 0, 2)
        },
        "by_status": list(by_status.values()),
        "by_weather": by_weather,
        "daily_data": dpr_data
    }


@frappe.whitelist()
def get_rfi_age_analysis(project=None, from_date=None, to_date=None):
    """RFI age analysis for overdue tracking."""
    frappe.has_permission("RFI", "read", throw=True)

    filters = {}
    if project:
        filters["project"] = project
    if from_date and to_date:
        filters["raised_date"] = ["between", [from_date, to_date]]

    rfis = frappe.get_all("RFI",
        filters=filters,
        fields=["name", "rfi_number", "project", "subject", "rfi_type",
                "priority", "status", "raised_date", "due_date", "response_date",
                "raised_by", "responded_by"],
        order_by="raised_date desc",
        limit_page_length=100
    )

    overdue = []
    upcoming = []
    current = []
    closed = []

    for rfi in rfis:
        if rfi.response_date:
            rfi.response_days = date_diff(rfi.response_date, rfi.raised_date) if rfi.raised_date else 0
        elif rfi.due_date:
            days_until = date_diff(rfi.due_date, get_today()) if rfi.due_date else 0
            rfi.days_until_due = days_until
            if days_until < 0:
                rfi.overdue_days = abs(days_until)
                overdue.append(rfi)
            elif days_until <= 7:
                upcoming.append(rfi)
            else:
                current.append(rfi)
        elif rfi.status == "Closed":
            closed.append(rfi)
        else:
            current.append(rfi)

    total_rfis = len(rfis)
    closed_count = sum(1 for r in rfis if r.status == "Closed")
    open_count = total_rfis - closed_count

    avg_response = sum(r.get("response_days", 0) for r in rfis if r.get("response_days"))
    avg_response = avg_response / closed_count if closed_count > 0 else 0

    return {
        "report_type": "RFI Age Analysis",
        "project": project,
        "from_date": from_date,
        "to_date": to_date,
        "generated_on": now_datetime(),
        "summary": {
            "total_rfis": total_rfis,
            "open_count": open_count,
            "closed_count": closed_count,
            "overdue_count": len(overdue),
            "upcoming_count": len(upcoming),
            "current_count": len(current),
            "avg_response_days": round(avg_response, 1)
        },
        "overdue": overdue,
        "upcoming": upcoming,
        "current": current,
        "closed": closed
    }


@frappe.whitelist()
def get_rfi_log_report_new(project=None, from_date=None, to_date=None):
    """
    Generate RFI Log report using RFI doctype.

    Args:
        project (str): Project name filter
        from_date (str): Start date filter
        to_date (str): End date filter

    Returns:
        dict: RFI log report data
    """
    frappe.has_permission("RFI", "read", throw=True)

    filters = {}
    if project:
        filters["project"] = project
    if from_date and to_date:
        filters["raised_date"] = ["between", [from_date, to_date]]

    rfis = frappe.get_all("RFI",
        filters=filters,
        fields=["name", "rfi_number", "project", "subject", "rfi_type",
                "priority", "status", "raised_date", "due_date", "response_date",
                "raised_by", "responded_by"],
        order_by="raised_date desc",
        limit_page_length=50
    )

    # Calculate age for open RFIs
    today_date = today()
    for rfi in rfis:
        if rfi.response_date:
            rfi.response_days = date_diff(rfi.response_date, rfi.raised_date) if rfi.raised_date else 0
        elif rfi.status in ["Draft", "Submitted", "Responded"]:
            rfi.age_days = date_diff(today_date, rfi.raised_date) if rfi.raised_date else 0
        else:
            rfi.age_days = 0

    total_rfis = len(rfis)
    closed_rfis = sum(1 for r in rfis if r.status == "Closed")
    open_rfis = sum(1 for r in rfis if r.status in ["Draft", "Submitted", "Responded"])

    avg_response = sum(r.get("response_days", 0) for r in rfis if r.get("response_days"))
    avg_response = avg_response / closed_rfis if closed_rfis > 0 else 0

    # Group by status
    by_status = {}
    for rfi in rfis:
        status = rfi.get("status") or "Unknown"
        if status not in by_status:
            by_status[status] = {"status": status, "count": 0}
        by_status[status]["count"] += 1

    return {
        "report_type": "RFI Log",
        "project": project,
        "from_date": from_date,
        "to_date": to_date,
        "generated_on": now_datetime(),
        "summary": {
            "total_rfis": total_rfis,
            "open_count": open_rfis,
            "closed_count": closed_rfis,
            "closure_rate": round((closed_rfis / total_rfis * 100) if total_rfis > 0 else 0, 2),
            "avg_response_days": round(avg_response, 1)
        },
        "by_status": list(by_status.values()),
        "details": rfis
    }


@frappe.whitelist()
def get_inspection_status_report(project, include_ncrs=False):
    """
    Generate Inspection Status report from ITP and Inspection Records.

    Args:
        project (str): Project name
        include_ncrs (bool): Include linked NCRs

    Returns:
        dict: Inspection status report data
    """
    frappe.has_permission("Project Inspection Plan", "read", throw=True)

    if not project:
        frappe.throw(_("Project is required"))

    # Get Project Inspection Plans (ITPs)
    itp_plans = frappe.get_all(
        "Project Inspection Plan",
        filters={"project": project},
        fields=[
            "name", "status", "inspection_type",
            "planned_start_date", "planned_end_date"
        ],
        order_by="planned_start_date desc",
        limit_page_length=100
    )

    # Get Inspection Records
    inspection_records = frappe.db.sql("""
        SELECT
            ir.name,
            ir.parent,
            ir.hold_point,
            ir.status,
            ir.scheduled_date,
            ir.actual_date,
            ir.inspector,
            ir.non_conformance
        FROM `tabInspection Record` ir
        INNER JOIN `tabProject Inspection Plan` pip ON ir.parent = pip.name
        WHERE pip.project = %s
        ORDER BY ir.scheduled_date DESC
    """, (project,), as_dict=1)

    # Group ITPs by status
    itp_by_status = {}
    for itp in itp_plans:
        status = itp.get("status") or "Unknown"
        if status not in itp_by_status:
            itp_by_status[status] = {
                "status": status,
                "count": 0
            }
        itp_by_status[status]["count"] += 1

    # Group inspection records by status
    inspection_by_status = {}
    for rec in inspection_records:
        status = rec.get("status") or "Unknown"
        if status not in inspection_by_status:
            inspection_by_status[status] = {
                "status": status,
                "count": 0,
                "pass_count": 0,
                "fail_count": 0
            }
        inspection_by_status[status]["count"] += 1
        if status == "Pass":
            inspection_by_status[status]["pass_count"] += 1
        elif status == "Fail":
            inspection_by_status[status]["fail_count"] += 1

    # Get linked NCRs from inspections
    linked_ncrs = []
    if include_ncrs:
        ncr_links = frappe.db.sql("""
            SELECT DISTINCT ir.non_conformance, ncr.ncr_number, ncr.severity, ncr.status
            FROM `tabInspection Record` ir
            INNER JOIN `tabProject Inspection Plan` pip ON ir.parent = pip.name
            INNER JOIN `tabNon-Conformance Report` ncr ON ir.non_conformance = ncr.name
            WHERE pip.project = %s AND ir.non_conformance IS NOT NULL
        """, (project,), as_dict=1)
        linked_ncrs = list(ncr_links)

    # Calculate summary
    total_itps = len(itp_plans)
    total_inspections = len(inspection_records)
    pass_rate = 0
    if total_inspections > 0:
        pass_count = sum(1 for i in inspection_records if i.get("status") == "Pass")
        pass_rate = round((pass_count / total_inspections * 100), 2)

    return {
        "report_type": "Inspection Status",
        "project": project,
        "generated_on": now_datetime(),
        "summary": {
            "total_itps": total_itps,
            "total_inspections": total_inspections,
            "pass_rate": pass_rate,
            "linked_ncrs": len(linked_ncrs)
        },
        "itp_by_status": list(itp_by_status.values()),
        "inspection_by_status": list(inspection_by_status.values()),
        "itp_plans": itp_plans,
        "inspection_records": inspection_records,
        "linked_ncrs": linked_ncrs
    }


@frappe.whitelist()
def get_equipment_utilization_report(project):
    """
    Generate Equipment Utilization report.

    Args:
        project (str): Project name

    Returns:
        dict: Equipment utilization report data
    """
    frappe.has_permission("Equipment Register", "read", throw=True)

    if not project:
        frappe.throw(_("Project is required"))

    # Get equipment assigned to project (with caching)
    def get_equipment_list():
        return frappe.get_all(
            "Equipment Register",
            filters={"project": project},
            fields=[
                "name", "equipment_name", "equipment_category",
                "equipment_status", "ownership_type",
                "hour_meter_reading", "odometer_reading"
            ],
            limit_page_length=100
        )

    equipment = _get_cached_ref_data(
        f"equipment_list_{project}",
        get_equipment_list,
        ttl=300  # 5 minutes
    )

    # Group by category and status
    by_category = {}
    for eq in equipment:
        cat = eq.get("equipment_category") or "Unknown"
        if cat not in by_category:
            by_category[cat] = {
                "category": cat,
                "total": 0,
                "in_use": 0,
                "available": 0,
                "maintenance": 0
            }
        by_category[cat]["total"] += 1
        status = eq.get("equipment_status") or "Unknown"
        if status == "In Use":
            by_category[cat]["in_use"] += 1
        elif status == "Available":
            by_category[cat]["available"] += 1
        elif status in ["Under Maintenance", "Under Repair"]:
            by_category[cat]["maintenance"] += 1

    # Group by status
    by_status = {}
    for eq in equipment:
        status = eq.get("equipment_status") or "Unknown"
        if status not in by_status:
            by_status[status] = {
                "status": status,
                "count": 0
            }
        by_status[status]["count"] += 1

    # Get utilization logs (with caching)
    def get_utilization_logs():
        return frappe.get_all(
            "Equipment Utilization Log",
            filters={"project": project},
            fields=[
                "name", "equipment", "work_date",
                "hours_used", "utilization_percentage"
            ],
            order_by="work_date desc",
            limit_page_length=100
        )

    utilization_logs = _get_cached_ref_data(
        f"utilization_logs_{project}",
        get_utilization_logs,
        ttl=180  # 3 minutes
    )

    # Calculate aggregates
    total_equipment = len(equipment)
    in_use = sum(1 for e in equipment if e.get("equipment_status") == "In Use")
    utilization_rate = round((in_use / total_equipment * 100) if total_equipment > 0 else 0, 2)

    return {
        "report_type": "Equipment Utilization",
        "project": project,
        "generated_on": now_datetime(),
        "summary": {
            "total_equipment": total_equipment,
            "in_use": in_use,
            "utilization_rate": utilization_rate,
            "total_utilization_logs": len(utilization_logs)
        },
        "by_category": list(by_category.values()),
        "by_status": list(by_status.values()),
        "details": equipment,
        "utilization_logs": utilization_logs
    }


@frappe.whitelist()
def get_team_performance_report(project, from_date=None, to_date=None):
    """
    Generate Team Performance report from DPR labor data.

    Args:
        project (str): Project name
        from_date (str): Start date filter
        to_date (str): End date filter

    Returns:
        dict: Team performance report data
    """
    frappe.has_permission("Daily Progress Report", "read", throw=True)

    if not project:
        frappe.throw(_("Project is required"))

    # Build query filters - use parameterized queries to prevent SQL injection
    query_params = []
    conditions = ["project = %s"]
    query_params.append(project)
    if from_date:
        conditions.append("report_date >= %s")
        query_params.append(from_date)
    if to_date:
        conditions.append("report_date <= %s")
        query_params.append(to_date)

    where_clause = " AND ".join(conditions)

    # Combine all team performance aggregations in a single query using CTE
    team_stats = frappe.db.sql("""
        WITH team_cte AS (
            SELECT
                report_date,
                supervisor,
                work_shifts,
                labor_count,
                equipment_count,
                overall_progress
            FROM `tabDaily Progress Report`
            WHERE """ + where_clause + """
        )
        SELECT
            'daily' as agg_type,
            report_date,
            NULL as stat_value,
            0 as dpr_count,
            SUM(labor_count) as total_labor,
            SUM(equipment_count) as total_equipment,
            AVG(overall_progress) as avg_progress
        FROM team_cte
        GROUP BY report_date
        UNION ALL
        SELECT
            'supervisor' as agg_type,
            NULL as report_date,
            supervisor as stat_value,
            COUNT(*) as dpr_count,
            SUM(labor_count) as total_labor,
            SUM(equipment_count) as total_equipment,
            0 as avg_progress
        FROM team_cte
        GROUP BY supervisor
        UNION ALL
        SELECT
            'shift' as agg_type,
            NULL as report_date,
            work_shifts as stat_value,
            COUNT(*) as count,
            0 as total_labor,
            0 as total_equipment,
            0 as avg_progress
        FROM team_cte
        WHERE work_shifts IS NOT NULL
        GROUP BY work_shifts
    """, tuple(query_params), as_dict=1)

    # Separate into grouped data
    labor_data = []
    supervisor_data = []
    shift_data = []

    for row in team_stats:
        if row.agg_type == 'daily':
            labor_data.append(row)
        elif row.agg_type == 'supervisor':
            supervisor_data.append(row)
        elif row.agg_type == 'shift':
            shift_data.append(row)

    # Calculate aggregates
    total_entries = len(labor_data)
    total_labor = sum(flt(d.get("total_labor", 0)) for d in labor_data)
    total_equipment = sum(flt(d.get("total_equipment", 0)) for d in labor_data)
    avg_daily_labor = total_labor / total_entries if total_entries > 0 else 0
    avg_daily_equipment = total_equipment / total_entries if total_entries > 0 else 0

    # Calculate productivity (progress per labor day)
    productivity = []
    for day in labor_data:
        labor = flt(day.get("total_labor", 0))
        progress = flt(day.get("avg_progress", 0))
        if labor > 0:
            productivity.append({
                "report_date": day.get("report_date"),
                "labor": int(labor),
                "progress": round(progress, 2),
                "productivity": round((progress / labor), 4)
            })

    return {
        "report_type": "Team Performance",
        "project": project,
        "from_date": from_date,
        "to_date": to_date,
        "generated_on": now_datetime(),
        "summary": {
            "total_dpr_entries": total_entries,
            "total_labor_days": int(total_labor),
            "total_equipment_days": int(total_equipment),
            "avg_daily_labor": round(avg_daily_labor, 1),
            "avg_daily_equipment": round(avg_daily_equipment, 1),
            "total_supervisors": len(supervisor_data)
        },
        "daily_data": labor_data,
        "supervisor_summary": supervisor_data,
        "shift_distribution": shift_data,
        "productivity": productivity
    }


@frappe.whitelist()
def export_project_report_to_excel(data, filename="Project_Report"):
    """
    Export project report data to Excel format.

    Args:
        data (dict): Report data to export
        filename (str): Output filename without extension

    Returns:
        dict: File URL on success
    """
    frappe.has_permission("Project Report Wizard", "read", throw=True)

    import json
    import os
    from frappe.utils.xlsxutils import make_xlsx

    try:
        # Build worksheets from all report sections
        worksheets = []

        # Section key -> display name mapping
        section_keys = [
            ("summary", "Summary"),
            ("details", "Details"),
            ("by_status", "By Status"),
            ("by_category", "By Category"),
            ("daily_data", "Daily Data"),
            ("supervisor_summary", "Supervisors"),
            ("productivity", "Productivity"),
            ("itp_plans", "ITP Plans"),
            ("inspection_records", "Inspections"),
            ("linked_ncrs", "Linked NCRs"),
            ("wbs_items", "WBS Items"),
            ("utilization_logs", "Utilization Logs")
        ]

        for key, sheet_name in section_keys:
            if key in data and isinstance(data[key], list) and data[key]:
                # Convert list of dicts to list of lists for make_xlsx
                rows = []
                if data[key]:
                    headers = list(data[key][0].keys())
                    rows.append(headers)
                    for row in data[key]:
                        rows.append([row.get(h, "") for h in headers])
                worksheets.append((sheet_name, rows))

        # Fallback: if no sections found, dump the whole data as single sheet
        if not worksheets:
            rows = []
            if isinstance(data, dict):
                for k, v in data.items():
                    if isinstance(v, list):
                        for row in v:
                            rows.append(row)
            if rows and isinstance(rows[0], dict):
                headers = list(rows[0].keys())
                rows = [headers] + [[r.get(h, "") for h in headers] for r in rows]
            worksheets.append(("Report", rows or [[]]))

        # Create xlsx with multiple sheets
        xlsx_file = make_xlsx(
            worksheets,
            filename,
            incl_header=True
        )

        # Write xlsx to private files directory and return URL
        timestamp = frappe.utils.now().strftime('%Y%m%d_%H%M%S')
        safe_filename = f"{filename}_{timestamp}.xlsx"
        private_dir = frappe.get_site_path("private", "files")
        os.makedirs(private_dir, exist_ok=True)
        file_path = os.path.join(private_dir, safe_filename)
        with open(file_path, "wb") as f:
            f.write(xlsx_file)
        file_url = f"/private/files/{safe_filename}"

        return {"success": True, "file_url": file_url}

    except Exception as e:
        logger.error(f"Error exporting to Excel: {str(e)}")
        return {"success": False, "error": str(e)}

# =============================================================================
# Operations Reports Functions
# =============================================================================

@frappe.whitelist()
def get_transmittal_report(project=None, status=None):
    """Transmittal report with acknowledgment tracking."""
    frappe.has_permission("Transmittal", "read", throw=True)

    filters = {}
    if project:
        filters["project"] = project
    if status:
        filters["status"] = status

    def get_transmittal_list():
        return frappe.get_all("Transmittal",
            filters=filters,
            fields=["name", "transmittal_number", "project", "transmittal_type",
                    "subject", "transmittal_date", "recipient_name", "acknowledged",
                    "acknowledgement_date", "status"],
            order_by="creation desc",
            limit_page_length=100
        )

    cache_key = f"transmittal_list_{project or 'all'}_{status or 'all'}"
    transmittals = _get_cached_ref_data(cache_key, get_transmittal_list, ttl=120)

    pending = sum(1 for t in transmittals if not t.acknowledged)
    acknowledged = sum(1 for t in transmittals if t.acknowledged)

    return {
        "transmittals": transmittals,
        "total_count": len(transmittals),
        "pending_acknowledgment": pending,
        "acknowledged": acknowledged
    }


@frappe.whitelist()
def get_transmittal_summary(project):
    """Transmittal summary by type."""
    frappe.has_permission("Transmittal", "read", throw=True)

    if not project:
        frappe.throw(_("Project is required"))

    if not frappe.db.exists("Project", project):
        frappe.throw(_("Project {0} does not exist").format(project))

    try:
        summary = frappe.db.sql("""
            SELECT transmittal_type, COUNT(*) as count,
                   SUM(CASE WHEN acknowledged = 1 THEN 1 ELSE 0 END) as ack_count
            FROM `tabTransmittal`
            WHERE project = %s
            GROUP BY transmittal_type
        """, (project,), as_dict=1)
    except Exception as e:
        logger.error(f"Error getting transmittal summary: {str(e)}")
        frappe.throw(_("Failed to get transmittal summary"))

    return {"project": project, "by_type": summary}


@frappe.whitelist()
def get_work_package_status_report(project=None):
    """Work package status report with progress and delays."""
    frappe.has_permission("Work Package", "read", throw=True)

    filters = {}
    if project:
        filters["project"] = project

    packages = frappe.get_all("Work Package",
        filters=filters,
        fields=["name", "package_code", "package_name", "wbs_item",
                "package_type", "assigned_to", "planned_start", "planned_end",
                "actual_start", "actual_end", "progress", "status"],
        order_by="creation desc",
        limit_page_length=100
    )

    # Calculate delays
    from frappe.utils import today as get_today, date_diff
    for pkg in packages:
        if pkg.planned_end and not pkg.actual_end:
            pkg.delay_days = date_diff(pkg.planned_end, get_today()) if pkg.planned_end and pkg.planned_end < get_today() else 0
        else:
            pkg.delay_days = 0

    by_status = {}
    for pkg in packages:
        status = pkg.status or "Planning"
        if status not in by_status:
            by_status[status] = 0
        by_status[status] += 1

    return {
        "packages": packages,
        "total_count": len(packages),
        "by_status": by_status
    }


@frappe.whitelist()
def get_work_package_resource_utilization(project):
    """Work package resource utilization report."""
    frappe.has_permission("Work Package", "read", throw=True)

    if not project:
        frappe.throw(_("Project is required"))

    if not frappe.db.exists("Project", project):
        frappe.throw(_("Project {0} does not exist").format(project))

    # Try to get labor data from Daily Progress Report linked to work packages
    resource_data = frappe.db.sql("""
        SELECT
            wp.package_code,
            wp.package_name,
            COALESCE(SUM(dpr.labor_count), 0) as total_labor,
            COALESCE(SUM(dpr.equipment_count), 0) as total_equipment
        FROM `tabWork Package` wp
        LEFT JOIN `tabDaily Progress Report` dpr
            ON dpr.project = wp.project
            AND dpr.work_package = wp.name
        WHERE wp.project = %s
        GROUP BY wp.name, wp.package_code, wp.package_name
    """, (project,), as_dict=1)

    total_labor = sum(flt(r.get("total_labor", 0)) for r in resource_data)
    total_equipment = sum(flt(r.get("total_equipment", 0)) for r in resource_data)

    packages = frappe.get_all("Work Package",
        filters={"project": project},
        fields=["name", "package_code", "package_name", "status", "progress"],
        limit_page_length=100
    )

    return {
        "project": project,
        "total_labor": int(total_labor),
        "total_equipment": int(total_equipment),
        "packages": packages,
        "resource_breakdown": resource_data
    }


@frappe.whitelist()
def get_item_request_report(project=None, status=None):
    """Item request report with status breakdown."""
    frappe.has_permission("Item Request", "read", throw=True)

    filters = {}
    if project:
        filters["project"] = project
    if status:
        filters["status"] = status

    requests = frappe.get_all("Item Request",
        filters=filters,
        fields=["name", "request_number", "project", "request_type",
                "priority", "request_date", "required_date", "status",
                "approved_by"],
        order_by="creation desc",
        limit_page_length=100
    )

    by_status = {"Draft": 0, "Approved": 0, "Procured": 0, "Fulfilled": 0, "Cancelled": 0}
    for req in requests:
        s = req.status or "Draft"
        if s in by_status:
            by_status[s] += 1

    by_priority = {"Low": 0, "Medium": 0, "High": 0, "Urgent": 0}
    for req in requests:
        p = req.priority or "Medium"
        if p in by_priority:
            by_priority[p] += 1

    return {
        "requests": requests,
        "total_count": len(requests),
        "by_status": by_status,
        "by_priority": by_priority
    }


@frappe.whitelist()
def get_item_request_pending_approval(project=None):
    """Get item requests pending approval."""
    frappe.has_permission("Item Request", "read", throw=True)

    filters = {"status": "Draft"}
    if project:
        filters["project"] = project

    pending = frappe.get_all("Item Request",
        filters=filters,
        fields=["name", "request_number", "project", "request_type",
                "priority", "request_date", "required_date"],
        limit_page_length=100
    )

    return {"pending_requests": pending, "count": len(pending)}


@frappe.whitelist()
def get_gate_pass_report(project=None, from_date=None, to_date=None):
    """Gate pass log report with material reconciliation."""
    frappe.has_permission("Gate Pass", "read", throw=True)

    filters = {}
    if project:
        filters["project"] = project
    if from_date and to_date:
        filters["gate_pass_date"] = ["between", [from_date, to_date]]

    gate_passes = frappe.get_all("Gate Pass",
        filters=filters,
        fields=["name", "gate_pass_number", "gate_pass_type", "project",
                "vehicle_number", "material_description", "quantity", "uom",
                "gate_pass_date", "status"],
        order_by="gate_pass_date desc",
        limit_page_length=100
    )

    inward = [g for g in gate_passes if g.gate_pass_type == "Inward"]
    outward = [g for g in gate_passes if g.gate_pass_type == "Outward"]

    return {
        "gate_passes": gate_passes,
        "total_count": len(gate_passes),
        "inward_count": len(inward),
        "outward_count": len(outward),
        "inward_total_qty": sum(g.get("quantity", 0) for g in inward),
        "outward_total_qty": sum(g.get("quantity", 0) for g in outward)
    }


@frappe.whitelist()
def get_gate_pass_material_reconciliation(project, from_date=None, to_date=None):
    """Material reconciliation: inward vs outward quantities."""
    frappe.has_permission("Gate Pass", "read", throw=True)
    from frappe.utils import add_days, today

    if not from_date:
        from_date = add_days(today(), -30)
    if not to_date:
        to_date = today()

    # Get inward materials
    inward = frappe.db.sql("""
        SELECT material_description, SUM(quantity) as qty, uom
        FROM `tabGate Pass`
        WHERE project = %s AND gate_pass_type = 'Inward'
        AND gate_pass_date BETWEEN %s AND %s
        GROUP BY material_description, uom
    """, (project, from_date, to_date), as_dict=1)

    # Get outward materials
    outward = frappe.db.sql("""
        SELECT material_description, SUM(quantity) as qty, uom
        FROM `tabGate Pass`
        WHERE project = %s AND gate_pass_type = 'Outward'
        AND gate_pass_date BETWEEN %s AND %s
        GROUP BY material_description, uom
    """, (project, from_date, to_date), as_dict=1)

    return {
        "inward": inward,
        "outward": outward,
        "from_date": from_date,
        "to_date": to_date
    }
