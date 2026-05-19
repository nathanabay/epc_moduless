"""
Billing API Module

REST API endpoints for dual-track billing operations.
"""

import frappe
from frappe import _
from frappe.utils import today, add_days, flt
from epc_modules.utils import get_epc_logger
from epc_modules.utils.billing_calculator import (
    RABillingCalculator,
    MilestoneBillingCalculator,
    BillingEngine
)

logger = get_epc_logger(__name__)


@frappe.whitelist()
def calculate_ra_bill(project, measurement_books=None):
    """
    Calculate RA Bill totals for a billing period.

    Args:
        project (str): Project name
        measurement_books (list): List of MB references with certified values

    Returns:
        dict: Complete billing calculation
    """
    if not frappe.db.exists("Project", project):
        frappe.throw(_("Project {0} does not exist").format(project))

    project_doc = frappe.get_doc("Project", project)

    # Verify billing track
    if project_doc.billing_track != "RA-Billing":
        frappe.throw(_("Project uses Milestone-Billing, not RA-Billing"))

    mb_values = []
    if measurement_books:
        for mb_ref in measurement_books:
            mb_doc = None
            if frappe.db.exists("Measurement Book", mb_ref.get("name")):
                mb_doc = frappe.get_doc("Measurement Book", mb_ref.get("name"))
            elif frappe.db.exists("Measurement Book", mb_ref.get("measurement_book")):
                mb_doc = frappe.get_doc("Measurement Book", mb_ref.get("measurement_book"))

            if mb_doc:
                mb_values.append({
                    "name": mb_doc.name,
                    "certified_value": mb_ref.get("certified_value", 0),
                    "is_certified": mb_ref.get("is_certified", mb_doc.certification_status == "Certified"),
                    "mb_date": mb_doc.mb_date
                })

    return RABillingCalculator.calculate_ra_bill_totals(project, mb_values)


@frappe.whitelist()
def create_ra_bill(project, data):
    """
    Create a new RA Bill.

    Args:
        project (str): Project name
        data (dict): RA bill data including MB references

    Returns:
        dict: Created RA bill info
    """
    frappe.has_permission("RA Bill", "create", throw=True)

    if not frappe.db.exists("Project", project):
        frappe.throw(_("Project {0} does not exist").format(project))

    # Generate RA bill number
    count = frappe.db.count("RA Bill", {"project": project}) or 0
    ra_bill_number = f"RA-{project[:4].upper()}-{count + 1:04d}"

    # Calculate billing totals
    mb_values = []
    if data.get("measurement_book_refs"):
        for mb_ref in data["measurement_book_refs"]:
            if isinstance(mb_ref, dict):
                mb_values.append({
                    "measurement_book": mb_ref.get("measurement_book"),
                    "certified_value": mb_ref.get("certified_value", 0),
                    "is_certified": mb_ref.get("is_certified", 0)
                })

    calc_result = RABillingCalculator.calculate_ra_bill_totals(project, mb_values)

    # Create RA Bill document
    doc = frappe.get_doc({
        "doctype": "RA Bill",
        "ra_bill_number": ra_bill_number,
        "project": project,
        "billing_period_start": data.get("billing_period_start"),
        "billing_period_end": data.get("billing_period_end"),
        "consulting_engineer": data.get("consulting_engineer"),
        "gross_certified_value": calc_result["gross_certified_value"],
        "mobilization_advance": calc_result["original_advance"],
        "advance_recovered": calc_result["advance_recovered"],
        "cumulative_advance_recovered": calc_result["cumulative_advance_recovered"],
        "net_certified_value": calc_result["net_certified_value"],
        "retention_percentage": calc_result["retention_percentage"],
        "retention_amount": calc_result["retention_amount"],
        "net_payable": calc_result["net_payable"],
        "vat_rate": calc_result["vat_rate"],
        "vat_amount": calc_result["vat_amount"],
        "total_invoice_value": calc_result["total_invoice_value"],
        "status": "Draft",
        "measurement_book_refs": mb_values
    })

    doc.insert()

    logger.info(f"Created RA Bill {ra_bill_number} for project {project}")

    return {
        "name": doc.name,
        "ra_bill_number": doc.ra_bill_number,
        "total_invoice_value": doc.total_invoice_value,
        "status": doc.status
    }


@frappe.whitelist()
def get_project_ra_bills(project, status=None):
    """
    Get RA Bills for a project.

    Args:
        project (str): Project name
        status (str, optional): Filter by status

    Returns:
        list: RA Bills
    """
    if not frappe.db.exists("Project", project):
        frappe.throw(_("Project {0} does not exist").format(project))

    filters = {"project": project}
    if status:
        filters["status"] = status

    bills = frappe.get_all(
        "RA Bill",
        filters=filters,
        fields=["name", "ra_bill_number", "billing_period_start", "billing_period_end",
                "gross_certified_value", "net_payable", "total_invoice_value", "vat_amount",
                "status", "certification_date"],
        order_by="creation desc"
    )

    return bills


@frappe.whitelist()
def get_ra_bill_details(ra_bill_name):
    """
    Get detailed RA Bill with measurement book references.

    Args:
        ra_bill_name (str): RA Bill name

    Returns:
        dict: RA Bill details
    """
    if not frappe.db.exists("RA Bill", ra_bill_name):
        frappe.throw(_("RA Bill {0} does not exist").format(ra_bill_name))

    doc = frappe.get_doc("RA Bill", ra_bill_name)

    return {
        "name": doc.name,
        "ra_bill_number": doc.ra_bill_number,
        "project": doc.project,
        "billing_period_start": doc.billing_period_start,
        "billing_period_end": doc.billing_period_end,
        "consulting_engineer": doc.consulting_engineer,
        "certification_date": doc.certification_date,
        "gross_certified_value": doc.gross_certified_value,
        "mobilization_advance": doc.mobilization_advance,
        "advance_recovered": doc.advance_recovered,
        "cumulative_advance_recovered": doc.cumulative_advance_recovered,
        "net_certified_value": doc.net_certified_value,
        "retention_percentage": doc.retention_percentage,
        "retention_amount": doc.retention_amount,
        "net_payable": doc.net_payable,
        "vat_rate": doc.vat_rate,
        "vat_amount": doc.vat_amount,
        "total_invoice_value": doc.total_invoice_value,
        "invoice_number": doc.invoice_number,
        "invoice_date": doc.invoice_date,
        "sales_invoice": doc.sales_invoice,
        "status": doc.status,
        "measurement_book_refs": [
            {
                "measurement_book": r.measurement_book,
                "mb_date": r.mb_date,
                "certified_value": r.certified_value,
                "is_certified": r.is_certified,
                "remarks": r.remarks
            }
            for r in doc.measurement_book_refs
        ],
        "remarks": doc.remarks
    }


@frappe.whitelist()
def submit_ra_bill_for_certification(ra_bill_name):
    """
    Submit RA Bill for consulting engineer certification.

    Args:
        ra_bill_name (str): RA Bill name

    Returns:
        dict: Submission result
    """
    frappe.has_permission("RA Bill", "write", throw=True)
    if not frappe.db.exists("RA Bill", ra_bill_name):
        frappe.throw(_("RA Bill {0} does not exist").format(ra_bill_name))

    doc = frappe.get_doc("RA Bill", ra_bill_name)

    if doc.status != "Draft":
        frappe.throw(_("RA Bill can only be submitted from Draft status"))

    doc.status = "Submitted"
    doc.save()

    logger.info(f"RA Bill {doc.ra_bill_number} submitted for certification")

    return {
        "name": doc.name,
        "status": doc.status
    }


@frappe.whitelist()
def certify_ra_bill(ra_bill_name, certifying_engineer=None):
    """
    Certify RA Bill and prepare for invoicing.

    Args:
        ra_bill_name (str): RA Bill name
        certifying_engineer (str): Certifying engineer name

    Returns:
        dict: Certification result
    """
    frappe.has_permission("RA Bill", "write", throw=True)
    if not frappe.db.exists("RA Bill", ra_bill_name):
        frappe.throw(_("RA Bill {0} does not exist").format(ra_bill_name))

    doc = frappe.get_doc("RA Bill", ra_bill_name)

    if doc.status != "Submitted":
        frappe.throw(_("RA Bill must be Submitted for certification"))

    doc.status = "Certified"
    doc.certification_date = today()
    if certifying_engineer:
        doc.consulting_engineer = certifying_engineer
    doc.save()

    logger.info(f"RA Bill {doc.ra_bill_number} certified")

    return {
        "name": doc.name,
        "status": doc.status,
        "certification_date": doc.certification_date,
        "net_payable": doc.net_payable,
        "total_invoice_value": doc.total_invoice_value
    }


@frappe.whitelist()
def generate_ra_bill_invoice(ra_bill_name):
    """
    Generate Sales Invoice from certified RA Bill.

    Args:
        ra_bill_name (str): RA Bill name

    Returns:
        dict: Invoice creation result
    """
    if not frappe.db.exists("RA Bill", ra_bill_name):
        frappe.throw(_("RA Bill {0} does not exist").format(ra_bill_name))

    doc = frappe.get_doc("RA Bill", ra_bill_name)

    if doc.status != "Certified":
        frappe.throw(_("RA Bill must be Certified before invoicing"))

    if doc.sales_invoice:
        frappe.throw(_("RA Bill already has a linked sales invoice"))

    frappe.has_permission("Sales Invoice", "create", throw=True)
    project_doc = frappe.get_doc("Project", doc.project)

    # Generate invoice number
    invoice_number = f"INV-RA-{doc.ra_bill_number.split('-')[-1]}"

    # Create sales invoice
    si = frappe.get_doc({
        "doctype": "Sales Invoice",
        "title": f"RA Bill - {doc.ra_bill_number}",
        "project": doc.project,
        "customer": project_doc.customer,
        "due_date": add_days(today(), 30),
        "is_pos": 0,
        "items": [{
            "item_code": "RA Billing",
            "description": f"RA Bill {doc.ra_bill_number} for period {doc.billing_period_start} to {doc.billing_period_end}",
            "qty": 1,
            "rate": doc.net_payable,
            "amount": doc.net_payable,
            "project": doc.project
        }],
        "taxes": [{
            "doctype": "Sales Taxes and Charges",
            "charge_type": "On Net Total",
            "account_head": frappe.db.get_value("Account", {"account_name": ["like", "%VAT%"]}, "name") or "VAT - E",
            "description": "VAT 15% (Proclamation 1341/2024)",
            "rate": 15,
            "cost_center": "Main - E"
        }]
    })

    si.insert()
    si.submit()

    # Update RA Bill
    frappe.db.set_value("RA Bill", ra_bill_name, {
        "invoice_number": si.name,
        "invoice_date": today(),
        "sales_invoice": si.name,
        "status": "Invoiced"
    })

    logger.info(f"Generated invoice {si.name} from RA Bill {doc.ra_bill_number}")

    return {
        "ra_bill": doc.ra_bill_number,
        "sales_invoice": si.name,
        "invoice_amount": doc.total_invoice_value
    }


@frappe.whitelist()
def get_project_milestones(project):
    """
    Get project milestones for milestone billing.

    Args:
        project (str): Project name

    Returns:
        list: Project milestones
    """
    if not frappe.db.exists("Project", project):
        frappe.throw(_("Project {0} does not exist").format(project))

    project_doc = frappe.get_doc("Project", project)

    if project_doc.billing_track != "Milestone-Billing":
        frappe.throw(_("Project uses RA-Billing, not Milestone-Billing"))

    milestones = frappe.get_all(
        "Project Milestone",
        filters={"parent": project},
        fields=["name", "milestone_name", "sequence", "planned_date", "actual_date",
                "trigger_percentage", "invoice_amount", "is_invoiced", "sales_invoice", "status"],
        order_by="sequence asc"
    )

    return milestones


@frappe.whitelist()
def create_milestone(project, data):
    """
    Create a new milestone for a project.

    Args:
        project (str): Project name
        data (dict): Milestone data

    Returns:
        dict: Created milestone info
    """
    frappe.has_permission("Project Milestone", "create", throw=True)

    if not frappe.db.exists("Project", project):
        frappe.throw(_("Project {0} does not exist").format(project))

    project_doc = frappe.get_doc("Project", project)

    if project_doc.billing_track != "Milestone-Billing":
        frappe.throw(_("Project uses RA-Billing, not Milestone-Billing"))

    doc = frappe.get_doc({
        "doctype": "Project Milestone",
        "parent": project,
        "parenttype": "Project",
        "parentfield": "milestones",
        "milestone_name": data.get("milestone_name"),
        "sequence": data.get("sequence", 1),
        "description": data.get("description", ""),
        "planned_date": data.get("planned_date"),
        "trigger_percentage": data.get("trigger_percentage", 0),
        "invoice_amount": data.get("invoice_amount"),
        "status": "Pending"
    })

    doc.insert()

    return {
        "name": doc.name,
        "milestone_name": doc.milestone_name,
        "sequence": doc.sequence,
        "invoice_amount": doc.invoice_amount
    }


@frappe.whitelist()
def check_milestone_triggers(project):
    """
    Check which milestones should be triggered.

    Args:
        project (str): Project name

    Returns:
        list: Milestones ready to invoice
    """
    return MilestoneBillingCalculator.check_milestone_triggers(project)


@frappe.whitelist()
def trigger_milestone_invoice(project, milestone_name):
    """
    Generate invoice for a milestone.

    Args:
        project (str): Project name
        milestone_name (str): Milestone name

    Returns:
        dict: Invoice result
    """
    if not frappe.db.exists("Project", project):
        frappe.throw(_("Project {0} does not exist").format(project))

    result = MilestoneBillingCalculator.generate_milestone_invoice(project, milestone_name)
    return result


@frappe.whitelist()
def get_billing_summary(project):
    """
    Get complete billing summary for a project.

    Args:
        project (str): Project name

    Returns:
        dict: Billing summary
    """
    if not frappe.db.exists("Project", project):
        frappe.throw(_("Project {0} does not exist").format(project))

    return BillingEngine.get_billing_summary(project)


@frappe.whitelist()
def get_advance_recovery_status(project):
    """
    Get advance recovery status for a project.

    Args:
        project (str): Project name

    Returns:
        dict: Advance recovery details
    """
    if not frappe.db.exists("Project", project):
        frappe.throw(_("Project {0} does not exist").format(project))

    project_doc = frappe.get_doc("Project", project)

    original_advance = flt(getattr(project_doc, 'mobilization_advance_amount', 0))
    total_contract = flt(project_doc.contract_value)

    # Get cumulative certified
    cumulative_certified = 0
    if project_doc.billing_track == "RA-Billing":
        cumulative_certified = frappe.db.sql("""
            SELECT SUM(gross_certified_value)
            FROM `tabRA Bill`
            WHERE project = %s AND docstatus = 1
        """, project)[0][0] or 0

    # Calculate current recovery status
    recovery = RABillingCalculator.calculate_advance_recovery(
        original_advance=original_advance,
        current_certified_value=cumulative_certified,
        total_contract_value=total_contract,
        cumulative_certified_value=cumulative_certified
    )

    return {
        "project": project,
        "original_advance": original_advance,
        "total_contract_value": total_contract,
        "cumulative_certified": cumulative_certified,
        "cumulative_recovered": recovery.get("cumulative_certified_value", 0) - cumulative_certified if cumulative_certified > original_advance else 0,
        "remaining_advance": original_advance - cumulative_certified if cumulative_certified < original_advance else 0,
        "recovery_status": recovery.get("status"),
        "completion_percentage": (cumulative_certified / total_contract * 100) if total_contract > 0 else 0
    }


@frappe.whitelist()
def get_vat_calculation(amount, vat_rate=15):
    """
    Calculate VAT for an amount (Ethiopian VAT 15%).

    Args:
        amount (float): Net amount
        vat_rate (float): VAT rate %

    Returns:
        dict: VAT breakdown
    """
    calc = RABillingCalculator.calculate_vat(amount, vat_rate)

    return {
        "net_amount": amount,
        "vat_rate": vat_rate,
        "vat_amount": calc["vat_amount"],
        "total_amount": calc["total_invoice_value"],
        "is_exempt": calc["is_exempt"]
    }


@frappe.whitelist()
def create_ra_bill_template(project_name, data):
    """
    Create RA Bill template for Arat Kilo project from BOQ items.
    """
    if not frappe.db.exists("Project", project_name):
        frappe.throw(_("Project {0} does not exist").format(project_name))

    project = frappe.get_doc("Project", project_name)

    if project.billing_track != "RA-Billing":
        frappe.throw(_("Project uses Milestone-Billing, not RA-Billing"))

    count = frappe.db.count("RA Bill", {"project": project_name}) or 0
    project_code = project_name[:4].upper()
    ra_bill_number = f"RA-{project_code}-{count + 1:04d}"

    boq_items = frappe.get_all(
        "Custom BOQ",
        filters={"project": project_name},
        fields=["name", "item_code", "description", "boq_quantity", "unit_rate",
                "total_value", "wbs_code", "measurement_method"]
    )

    total_boq_value = sum(flt(item.total_value) for item in boq_items)

    cumulative_certified = frappe.db.sql("""
        SELECT SUM(gross_certified_value)
        FROM `tabRA Bill`
        WHERE project = %s AND docstatus = 1
    """, project_name)[0][0] or 0

    calc = RABillingCalculator.calculate_ra_bill_totals(
        project_name,
        [{"certified_value": 0, "is_certified": 0}]
    )

    doc = frappe.get_doc({
        "doctype": "RA Bill",
        "ra_bill_number": ra_bill_number,
        "project": project_name,
        "billing_period_start": data.get("billing_period_start"),
        "billing_period_end": data.get("billing_period_end"),
        "gross_certified_value": 0,
        "mobilization_advance": calc.get("original_advance", 0),
        "advance_recovered": calc.get("advance_recovered", 0),
        "cumulative_advance_recovered": calc.get("cumulative_advance_recovered", 0),
        "net_certified_value": 0,
        "retention_percentage": 10,
        "retention_amount": 0,
        "net_payable": 0,
        "vat_rate": 15,
        "vat_amount": 0,
        "total_invoice_value": 0,
        "status": "Draft",
    })
    doc.insert()

    return {
        "name": doc.name,
        "ra_bill_number": doc.ra_bill_number,
        "project": project_name,
        "boq_item_count": len(boq_items),
        "total_boq_value": total_boq_value,
        "cumulative_certified": cumulative_certified,
        "gross_certified_value": doc.gross_certified_value,
        "status": doc.status
    }


@frappe.whitelist()
def get_ra_bill_schedule(project_name):
    """
    Get projected RA Bill billing schedule based on BOQ and contract value.
    """
    if not frappe.db.exists("Project", project_name):
        frappe.throw(_("Project {0} does not exist").format(project_name))

    project = frappe.get_doc("Project", project_name)

    boq_items = frappe.get_all(
        "Custom BOQ",
        filters={"project": project_name},
        fields=["name", "wbs_code", "total_value"]
    )
    total_boq_value = sum(flt(item.total_value) for item in boq_items)

    existing_bills = frappe.get_all(
        "RA Bill",
        filters={"project": project_name, "docstatus": 1},
        fields=["name", "ra_bill_number", "gross_certified_value", "certification_date"]
    )
    cumulative_certified = sum(flt(b.gross_certified_value) for b in existing_bills)

    contract_value = flt(project.contract_value) or total_boq_value
    avg_bill_value = contract_value * 0.015
    estimated_bills = max(1, int(contract_value / avg_bill_value)) if avg_bill_value > 0 else 12

    return {
        "project": project_name,
        "contract_value": contract_value,
        "total_boq_value": total_boq_value,
        "cumulative_certified": cumulative_certified,
        "outstanding_value": contract_value - cumulative_certified,
        "completed_percentage": (cumulative_certified / contract_value * 100) if contract_value > 0 else 0,
        "estimated_ra_bills": estimated_bills,
        "avg_bill_value": avg_bill_value,
        "existing_bill_count": len(existing_bills),
        "scheduled_bills": [
            {
                "bill_number": i + 1,
                "estimated_value": avg_bill_value,
                "cumulative": avg_bill_value * (i + 1)
            }
            for i in range(estimated_bills)
        ]
    }