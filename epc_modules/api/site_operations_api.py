import frappe
from frappe import _
from frappe.utils import nowdate, add_days, get_datetime, flt
from frappe.security.permissions import PermissionError


@frappe.whitelist()
def get_project_rfi_count(project):
    """Get the count of RFIs for a project."""
    if project:
        frappe.has_permission("Project", "read", docname=project, throw=True)
    frappe.has_permission("RFI", "read", throw=True)
    return frappe.db.count("RFI", {"project": project})


@frappe.whitelist()
def create_rfi(project, rfi_type, subject, question, raised_by=None, priority="Medium", wbs_item=None):
    """Create a new RFI record."""
    frappe.has_permission("RFI", "create", throw=True)
    frappe.has_permission("Project", "write", docname=project, throw=True)

    # Validate required fields
    if not project:
        frappe.throw(_("Project is required"))
    if not rfi_type:
        frappe.throw(_("RFI Type is required"))
    if not subject:
        frappe.throw(_("Subject is required"))
    if not question:
        frappe.throw(_("Question is required"))

    if not isinstance(project, str) or not project.strip():
        frappe.throw(_("Project must be a valid string"))
    if not isinstance(subject, str) or not subject.strip():
        frappe.throw(_("Subject must be a non-empty string"))
    if not isinstance(question, str) or not question.strip():
        frappe.throw(_("Question must be a non-empty string"))

    rfi = frappe.new_doc("RFI")
    rfi.project = project
    rfi.rfi_type = rfi_type
    rfi.subject = subject
    rfi.question = question
    rfi.priority = priority
    rfi.raised_by = raised_by or frappe.session.user
    rfi.raised_date = nowdate()
    if wbs_item:
        rfi.wbs_item = wbs_item

    try:
        rfi.insert()
        return {"name": rfi.name, "rfi_number": rfi.rfi_number}
    except PermissionError:
        frappe.throw(_("You do not have permission to create this RFI record"))
    except frappe.ValidationError as e:
        frappe.throw(_(str(e)))


@frappe.whitelist()
def get_rfi_list(project=None, status=None, limit=50):
    """Get list of RFIs with optional filters."""
    frappe.has_permission("RFI", "read", throw=True)
    filters = {}
    if project:
        frappe.has_permission("Project", "read", docname=project, throw=True)
        filters["project"] = project
    if status:
        filters["status"] = status

    # Cap limit to prevent excessive record retrieval
    limit = min(int(limit or 20), 100)

    rfis = frappe.get_list(
        "RFI",
        filters=filters,
        fields=["name", "rfi_number", "project", "subject", "status", "priority", "due_date", "raised_date"],
        order_by="raised_date desc",
        limit=limit
    )
    return rfis


@frappe.whitelist()
def update_rfi_response(rfi_name, response, responded_by=None):
    """Update RFI with response."""
    rfi = frappe.get_doc("RFI", rfi_name)
    frappe.has_permission("RFI", "write", doc=rfi, throw=True)
    frappe.has_permission("Project", "write", docname=rfi.project, throw=True)
    rfi.response = response
    rfi.responded_by = responded_by or frappe.session.user
    rfi.response_date = nowdate()
    if rfi.status == "Open":
        rfi.status = "Pending Review"
    try:
        rfi.save()
        return {"status": rfi.status, "response_date": rfi.response_date}
    except PermissionError:
        frappe.throw(_("You do not have permission to update this RFI"))
    except frappe.ValidationError as e:
        frappe.throw(_(str(e)))


@frappe.whitelist()
def close_rfi(rfi_name):
    """Close an RFI."""
    rfi = frappe.get_doc("RFI", rfi_name)
    frappe.has_permission("RFI", "write", doc=rfi, throw=True)
    frappe.has_permission("Project", "write", docname=rfi.project, throw=True)
    rfi.status = "Closed"
    try:
        rfi.save()
        return {"name": rfi.name, "status": rfi.status}
    except PermissionError:
        frappe.throw(_("You do not have permission to close this RFI"))
    except frappe.ValidationError as e:
        frappe.throw(_(str(e)))


@frappe.whitelist()
def get_rfi_summary(project=None):
    """Get RFI summary statistics using a single aggregation query."""
    frappe.has_permission("RFI", "read", throw=True)
    filters = []
    filter_args = []

    if project:
        frappe.has_permission("Project", "read", docname=project, throw=True)
        filters.append("project = %s")
        filter_args.append(project)

    # Single aggregation query instead of 5 separate COUNT queries
    summary = frappe.db.sql("""
        SELECT
            COUNT(*) AS total,
            SUM(CASE WHEN status = 'Open' THEN 1 ELSE 0 END) AS open_count,
            SUM(CASE WHEN status = 'Pending Review' THEN 1 ELSE 0 END) AS pending_count,
            SUM(CASE WHEN status = 'Closed' THEN 1 ELSE 0 END) AS closed_count,
            SUM(CASE WHEN status IN ('Open', 'Pending Review') AND due_date < %s THEN 1 ELSE 0 END) AS overdue_count
        FROM `tabRFI`
        {filters}
    """.format(filters="WHERE " + " AND ".join(filters) if filters else ""),
    filter_args + ([nowdate()] if filter_args else [nowdate()]), as_dict=True)

    return {
        "total": summary[0].total or 0,
        "open": summary[0].open_count or 0,
        "pending": summary[0].pending_count or 0,
        "closed": summary[0].closed_count or 0,
        "overdue": summary[0].overdue_count or 0
    }


@frappe.whitelist()
def get_rfi_type_defaults(rfi_type_name):
    """Get default values from RFI Type."""
    frappe.has_permission("RFI Type", "read", throw=True)
    rfi_type = frappe.get_doc("RFI Type", rfi_type_name)
    return {
        "priority": rfi_type.default_priority,
        "response_days": rfi_type.response_days
    }