import frappe
from frappe import _
from frappe.utils import today, add_months, flt
from frappe.utils.pdf import get_pdf


@frappe.whitelist()
def create_estimation(project, data):
    """Create Estimation with markup calculation."""
    if not isinstance(data, dict):
        frappe.throw(_("Invalid data format. Expected a dictionary."))
    frappe.has_permission("Estimation", "create", throw=True)
    frappe.has_permission("Project", "write", doc=frappe.get_doc("Project", project), throw=True)
    if not project:
        frappe.throw(_("Project is required"))
    if not data.get("customer"):
        frappe.throw(_("Customer is required"))
    if not isinstance(data.get("items", []), list):
        frappe.throw(_("Items must be a list"))
    project_code = project[:4].upper() if project else "EST"
    est_number = f"EST-{project_code}-{frappe.generate_hash(length=8).upper()}"

    doc = frappe.get_doc({
        "doctype": "Estimation",
        "estimate_number": est_number,
        "project": project,
        "estimate_title": data.get("estimate_title"),
        "customer": data.get("customer"),
        "estimate_date": today(),
        "valid_until": data.get("valid_until"),
        "items": data.get("items", []),
        "markup_percentage": data.get("markup_percentage", 10),
        "vat_percentage": data.get("vat_percentage", 15),
        "status": "Draft"
    })
    try:
        doc.insert()
        doc.calculate_totals()
        doc.save()
        return {"name": doc.name, "estimate_number": est_number}
    except frappe.ValidationError as e:
        frappe.log_error(frappe.get_traceback(), "Finance API Validation Error")
        frappe.throw(_("Validation failed: {0}").format(str(e)))
    except frappe.DuplicateEntryError as e:
        frappe.log_error(frappe.get_traceback(), "Finance API Duplicate Entry Error")
        frappe.throw(_("Duplicate entry: {0}").format(str(e)))
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Finance API Error")
        frappe.throw(_("Failed to create Estimation: {0}").format(str(e)))


@frappe.whitelist()
def convert_estimation_to_boq(name):
    """Convert approved estimation to Custom BOQ."""
    doc = frappe.get_doc("Estimation", name)
    frappe.has_permission("Estimation", "write", doc=doc, throw=True)
    frappe.has_permission("Project", "write", doc=frappe.get_doc("Project", doc.project), throw=True)
    try:
        boq_name = doc.convert_to_boq()
        return {"boq_name": boq_name, "status": "Converted"}
    except Exception:
        frappe.log_error(frappe.get_traceback(), "Finance API Error")
        frappe.throw(_("Failed to convert Estimation to BOQ"))


@frappe.whitelist()
def get_estimation_list(project=None, status=None):
    """Get estimations filtered by project and status."""
    frappe.has_permission("Estimation", "read", throw=True)
    filters = {}
    if project:
        frappe.has_permission("Project", "read", doc=frappe.get_doc("Project", project), throw=True)
        filters["project"] = project
    if status:
        # Validate status parameter against allowed values
        allowed_statuses = ["Draft", "Submitted", "Approved", "Rejected", "Converted"]
        if not isinstance(status, str) or status not in allowed_statuses:
            frappe.throw(_("Invalid status value. Allowed values: {0}").format(", ".join(allowed_statuses)))
        filters["status"] = status
    return frappe.get_list(
        "Estimation",
        filters=filters,
        fields=["name", "estimate_number", "project", "estimate_title",
                "grand_total", "status", "estimate_date", "converted_to_boq"],
        order_by="creation desc",
        limit_page_length=20
    )


@frappe.whitelist()
def create_budget(project, data):
    """Create Budget with cost breakdown."""
    if not isinstance(data, dict):
        frappe.throw(_("Invalid data format. Expected a dictionary."))
    frappe.has_permission("Budget", "create", throw=True)
    frappe.has_permission("Project", "write", doc=frappe.get_doc("Project", project), throw=True)
    if not project:
        frappe.throw(_("Project is required"))
    if not isinstance(data.get("lines", []), list):
        frappe.throw(_("Budget lines must be a list"))
    project_code = project[:4].upper() if project else "BUD"
    bud_code = f"BUD-{project_code}-{frappe.generate_hash(length=8).upper()}"

    doc = frappe.get_doc({
        "doctype": "Budget",
        "budget_code": bud_code,
        "project": project,
        "budget_type": data.get("budget_type", "Original"),
        "budget_date": today(),
        "lines": data.get("lines", []),
        "status": "Draft"
    })
    try:
        doc.insert()
        doc.calculate_totals()
        doc.save()
        return {"name": doc.name, "budget_code": bud_code}
    except frappe.ValidationError as e:
        frappe.log_error(frappe.get_traceback(), "Finance API Validation Error")
        frappe.throw(_("Validation failed: {0}").format(str(e)))
    except frappe.DuplicateEntryError as e:
        frappe.log_error(frappe.get_traceback(), "Finance API Duplicate Entry Error")
        frappe.throw(_("Duplicate entry: {0}").format(str(e)))
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Finance API Error")
        frappe.throw(_("Failed to create Budget: {0}").format(str(e)))


@frappe.whitelist()
def get_budget_variance(project):
    """Get budget variance report for a project."""
    frappe.has_permission("Project", "read", doc=frappe.get_doc("Project", project), throw=True)
    budgets = frappe.get_list("Budget",
        filters={"project": project, "docstatus": 1},
        fields=["name", "budget_code", "total_planned_cost", "total_actual_cost",
                "total_variance", "variance_percentage", "status"],
        order_by="creation desc"
    )
    return budgets


@frappe.whitelist()
def create_change_order(project, data):
    """Create Change Order with impact assessment."""
    if not isinstance(data, dict):
        frappe.throw(_("Invalid data format. Expected a dictionary."))
    frappe.has_permission("Change Order", "create", throw=True)
    frappe.has_permission("Project", "write", doc=frappe.get_doc("Project", project), throw=True)
    if not project:
        frappe.throw(_("Project is required"))
    if not data.get("change_title"):
        frappe.throw(_("Change title is required"))
    if not data.get("description"):
        frappe.throw(_("Description is required"))
    project_code = project[:4].upper() if project else "CO"
    co_number = f"CO-{project_code}-{frappe.generate_hash(length=8).upper()}"

    doc = frappe.get_doc({
        "doctype": "Change Order",
        "change_order_number": co_number,
        "project": project,
        "wbs_item": data.get("wbs_item"),
        "change_title": data.get("change_title"),
        "change_category": data.get("change_category"),
        "description": data.get("description"),
        "reason": data.get("reason"),
        "cost_impact": data.get("cost_impact", 0),
        "schedule_impact_days": data.get("schedule_impact_days", 0),
        "status": "Draft"
    })
    try:
        doc.insert()
        return {"name": doc.name, "change_order_number": co_number}
    except frappe.ValidationError as e:
        frappe.log_error(frappe.get_traceback(), "Finance API Validation Error")
        frappe.throw(_("Validation failed: {0}").format(str(e)))
    except frappe.DuplicateEntryError as e:
        frappe.log_error(frappe.get_traceback(), "Finance API Duplicate Entry Error")
        frappe.throw(_("Duplicate entry: {0}").format(str(e)))
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Finance API Error")
        frappe.throw(_("Failed to create Change Order: {0}").format(str(e)))


@frappe.whitelist()
def get_change_order_summary(project):
    """Get change order summary with total cost impact."""
    frappe.has_permission("Project", "read", doc=frappe.get_doc("Project", project), throw=True)
    cos = frappe.get_list("Change Order",
        filters={"project": project},
        fields=["name", "change_order_number", "change_title", "change_category",
                "cost_impact", "schedule_impact_days", "status", "is_approved"]
    )
    total_cost = sum(flt(co.get("cost_impact", 0)) for co in cos)
    total_days = sum(co.get("schedule_impact_days", 0) for co in cos)
    return {"change_orders": cos, "total_cost_impact": total_cost, "total_schedule_impact_days": total_days}