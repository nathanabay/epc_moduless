"""
DPR API Module

REST API endpoints for Daily Progress Report operations.
"""

import frappe
from frappe import _
from frappe.utils import today, now_datetime, nowdate
from epc_modules.utils import get_epc_logger
from epc_modules.utils.boq_calculator import BOQCalculator

logger = get_epc_logger(__name__)


@frappe.whitelist(methods=["POST"])
def submit_dpr_entry(data):
    """
    Submit a DPR entry from mobile or web interface.

    Args:
        data (dict): DPR entry data

    Returns:
        dict: Result with doc name
    """
    frappe.has_permission("Daily Progress Report", "create", throw=True)

    project = data.get("project")
    if not project:
        frappe.throw(_("Project is required"))

    if not frappe.db.exists("Project", project):
        frappe.throw(_("Project {0} does not exist").format(project))

    # Validate integer fields (HTTP params arrive as strings)
    labor_count = data.get("labor_count")
    work_shifts = data.get("work_shifts", 1)
    overall_progress = data.get("overall_progress")

    try:
        if labor_count is not None:
            labor_count = int(labor_count)
        if work_shifts is not None:
            work_shifts = int(work_shifts)
        if overall_progress is not None:
            overall_progress = int(overall_progress)
    except (ValueError, TypeError):
        frappe.throw(_("Invalid numeric value for labor_count, work_shifts, or overall_progress"))

    # Create DPR document
    doc = frappe.get_doc({
        "doctype": "Daily Progress Report",
        "project": project,
        "report_date": data.get("report_date", today()),
        "supervisor": data.get("supervisor", frappe.session.user),
        "site_zone": data.get("site_zone"),
        "weather_conditions": data.get("weather_conditions"),
        "labor_count": labor_count,
        "work_shifts": work_shifts,
        "overall_progress": overall_progress,
        "remarks": data.get("remarks"),
        "status": "Draft",
        "progress_entries": _prepare_dpr_entries(data.get("entries", []))
    })

    try:
        doc.insert()
    except Exception:
        frappe.log_error(
            title=_("DPR Insert Failed"),
            message=f"Failed to insert DPR for project {project}"
        )
        frappe.throw(_("Failed to create DPR entry. Please contact administrator."))

    # Auto-submit if supervisor is the session user
    if data.get("auto_submit", False):
        frappe.has_permission("Daily Progress Report", "submit", doc.name, throw=True)
        try:
            doc.submit()
        except Exception:
            frappe.throw(_("Auto-submit failed. DPR was created but not submitted."))

    # Trigger progress recalculation
    try:
        BOQCalculator.aggregate_project_progress(project)
    except Exception:
        logger.warning("Progress recalc failed for project: %s", project)

    return {
        "name": doc.name,
        "status": doc.status,
        "report_date": doc.report_date
    }


@frappe.whitelist(methods=["GET"])
def get_dpr_entries(project, from_date=None, to_date=None, limit_page_length=20, limit_start=0):
    """
    Get DPR entries for a project.

    Args:
        project (str): Project name
        from_date (str): Start date filter
        to_date (str): End date filter
        limit_page_length (int): Pagination limit (max 100)
        limit_start (int): Pagination offset

    Returns:
        list: DPR entries
    """
    frappe.has_permission("Daily Progress Report", "read", throw=True)

    if not frappe.db.exists("Project", project):
        frappe.throw(_("Project {0} does not exist").format(project))

    # Enforce max pagination
    limit_page_length = min(int(limit_page_length), 100) if limit_page_length else 20

    filters = {"project": project}
    if from_date:
        filters["report_date"] = [">=", from_date]
    if to_date:
        filters["report_date"] = ["<=", to_date]

    entries = frappe.get_list(
        "Daily Progress Report",
        filters=filters,
        fields=["name", "project", "report_date", "supervisor", "status",
                "labor_count", "work_shifts", "overall_progress", "site_zone", "weather_conditions"],
        order_by="report_date desc",
        limit_page_length=limit_page_length,
        limit_start=int(limit_start) if limit_start else 0
    )

    return entries


@frappe.whitelist()
def get_dpr_entry_details(dpr_name):
    """
    Get detailed DPR entry with progress entries.

    Args:
        dpr_name (str): DPR document name

    Returns:
        dict: DPR details
    """
    frappe.has_permission("Daily Progress Report", "read", dpr_name, throw=True)

    if not frappe.db.exists("Daily Progress Report", dpr_name):
        frappe.throw(_("DPR {0} does not exist").format(dpr_name))

    doc = frappe.get_doc("Daily Progress Report", dpr_name)

    return {
        "name": doc.name,
        "project": doc.project,
        "report_date": doc.report_date,
        "supervisor": doc.supervisor,
        "site_zone": doc.site_zone,
        "weather_conditions": doc.weather_conditions,
        "labor_count": doc.labor_count,
        "work_shifts": doc.work_shifts,
        "overall_progress": doc.overall_progress,
        "status": doc.status,
        "remarks": doc.remarks,
        "progress_entries": [
            {
                "wbs_item": e.wbs_item,
                "activity": e.activity,
                "unit": e.unit,
                "planned_quantity": e.planned_quantity,
                "actual_quantity": e.actual_quantity,
                "progress_percent": e.progress_percent,
                "remarks": e.remarks
            }
            for e in doc.progress_entries
        ]
    }


@frappe.whitelist(methods=["POST"])
def update_dpr_progress(dpr_name, progress_entries):
    """
    Update progress entries for an existing DPR.

    Args:
        dpr_name (str): DPR document name
        progress_entries (list): Updated entries

    Returns:
        dict: Result
    """
    frappe.has_permission("Daily Progress Report", "write", dpr_name, throw=True)

    if not frappe.db.exists("Daily Progress Report", dpr_name):
        frappe.throw(_("DPR {0} does not exist").format(dpr_name))

    doc = frappe.get_doc("Daily Progress Report", dpr_name)

    if doc.status == "Submitted":
        frappe.throw(_("Cannot update submitted DPR"))

    # Clear existing entries
    doc.progress_entries = []

    # Add new entries
    for entry in progress_entries:
        doc.append("progress_entries", entry)

    doc.save()

    return {
        "name": doc.name,
        "entries_count": len(doc.progress_entries)
    }


@frappe.whitelist(methods=["POST"])
def approve_dpr(dpr_name):
    """
    Approve a DPR document.

    Args:
        dpr_name (str): DPR document name

    Returns:
        dict: Approval result
    """
    frappe.has_permission("Daily Progress Report", "write", dpr_name, throw=True)

    if not frappe.db.exists("Daily Progress Report", dpr_name):
        frappe.throw(_("DPR {0} does not exist").format(dpr_name))

    doc = frappe.get_doc("Daily Progress Report", dpr_name)

    if doc.status == "Approved":
        return {"status": "already_approved", "name": doc.name}

    frappe.has_permission("Daily Progress Report", "submit", dpr_name, throw=True)
    doc.status = "Approved"
    doc.save()

    # Trigger progress aggregation
    BOQCalculator.aggregate_project_progress(doc.project)

    return {
        "name": doc.name,
        "status": "approved"
    }


@frappe.whitelist()
def get_wbs_progress_summary(project):
    """
    Get WBS progress summary from DPR entries.

    Args:
        project (str): Project name

    Returns:
        dict: WBS progress summary
    """
    frappe.has_permission("Project", "read", project, throw=True)

    if not frappe.db.exists("Project", project):
        frappe.throw(_("Project {0} does not exist").format(project))

    # Get all WBS items for project
    wbs_items = frappe.get_list(
        "WBS Item",
        filters={"project": project},
        fields=["name", "wbs_code", "wbs_name", "physical_progress", "planned_value", "earned_value"]
    )

    # Get DPR entries
    dpr_entries = frappe.get_list(
        "DPR Entry",
        filters={"parenttype": "Daily Progress Report", "parent": project},
        fields=["wbs_item", "actual_quantity", "progress_percent"],
        group_by="wbs_item"
    )

    # Create lookup for DPR data
    dpr_lookup = {e.wbs_item: e for e in dpr_entries if e.wbs_item}

    summary = {
        "project": project,
        "total_wbs_items": len(wbs_items),
        "wbs_details": []
    }

    total_planned = 0
    total_earned = 0

    for wbs in wbs_items:
        dpr_data = dpr_lookup.get(wbs.name, {})
        planned = wbs.planned_value or 0
        earned = dpr_data.get("progress_percent", 0) / 100 * planned

        summary["wbs_details"].append({
            "wbs_code": wbs.wbs_code,
            "wbs_name": wbs.wbs_name,
            "planned_value": planned,
            "earned_value": earned,
            "progress_percent": (earned / planned * 100) if planned > 0 else 0
        })

        total_planned += planned
        total_earned += earned

    summary["total_planned"] = total_planned
    summary["total_earned"] = total_earned
    summary["overall_progress"] = (total_earned / total_planned * 100) if total_planned > 0 else 0

    return summary


def _prepare_dpr_entries(entries):
    """Prepare DPR entries from raw data."""
    prepared = []
    for i, entry in enumerate(entries):
        prepared.append({
            "wbs_item": entry.get("wbs_item"),
            "boq_item": entry.get("boq_item"),
            "activity": entry.get("activity", ""),
            "measurement_method": entry.get("measurement_method"),
            "unit": entry.get("unit"),
            "planned_quantity": entry.get("planned_quantity", 0),
            "quantity_executed": entry.get("quantity_executed", 0),
            "cumulative_quantity": entry.get("cumulative_quantity", 0),
            "percent_complete": entry.get("percent_complete", 0),
            "is_milestone_achieved": entry.get("is_milestone_achieved", 0),
            "remarks": entry.get("remarks", "")
        })
    return prepared