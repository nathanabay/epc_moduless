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


@frappe.whitelist()
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

    # Create DPR document
    doc = frappe.get_doc({
        "doctype": "Daily Progress Report",
        "project": project,
        "report_date": data.get("report_date", today()),
        "supervisor": data.get("supervisor", frappe.session.user),
        "site_zone": data.get("site_zone"),
        "weather_conditions": data.get("weather_conditions"),
        "labor_count": data.get("labor_count"),
        "work_shifts": data.get("work_shifts", 1),
        "overall_progress": data.get("overall_progress"),
        "remarks": data.get("remarks"),
        "status": "Draft",
        "progress_entries": _prepare_dpr_entries(data.get("entries", []))
    })

    doc.insert()

    # Auto-submit if supervisor is the session user
    if data.get("auto_submit", False):
        doc.submit()

    # Trigger progress recalculation
    try:
        BOQCalculator.aggregate_project_progress(project)
    except Exception as e:
        logger.warning(f"Progress recalc failed: {str(e)}")

    return {
        "name": doc.name,
        "status": doc.status,
        "report_date": doc.report_date
    }


@frappe.whitelist()
def get_dpr_entries(project, from_date=None, to_date=None):
    """
    Get DPR entries for a project.

    Args:
        project (str): Project name
        from_date (str): Start date filter
        to_date (str): End date filter

    Returns:
        list: DPR entries
    """
    if not frappe.db.exists("Project", project):
        frappe.throw(_("Project {0} does not exist").format(project))

    filters = {"project": project}
    if from_date:
        filters["report_date"] = [">=", from_date]
    if to_date:
        filters["report_date"] = ["<=", to_date]

    entries = frappe.get_all(
        "Daily Progress Report",
        filters=filters,
        fields=["*"],
        order_by="report_date desc"
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


@frappe.whitelist()
def update_dpr_progress(dpr_name, progress_entries):
    """
    Update progress entries for an existing DPR.

    Args:
        dpr_name (str): DPR document name
        progress_entries (list): Updated entries

    Returns:
        dict: Result
    """
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

    doc.save(ignore_permissions=True)

    return {
        "name": doc.name,
        "entries_count": len(doc.progress_entries)
    }


@frappe.whitelist()
def approve_dpr(dpr_name):
    """
    Approve a DPR document.

    Args:
        dpr_name (str): DPR document name

    Returns:
        dict: Approval result
    """
    if not frappe.db.exists("Daily Progress Report", dpr_name):
        frappe.throw(_("DPR {0} does not exist").format(dpr_name))

    doc = frappe.get_doc("Daily Progress Report", dpr_name)

    if doc.status == "Approved":
        return {"status": "already_approved", "name": doc.name}

    doc.status = "Approved"
    doc.save(ignore_permissions=True)

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
    if not frappe.db.exists("Project", project):
        frappe.throw(_("Project {0} does not exist").format(project))

    # Get all WBS items for project
    wbs_items = frappe.get_all(
        "WBS Item",
        filters={"project": project},
        fields=["name", "wbs_code", "wbs_name", "physical_progress", "planned_value", "earned_value"]
    )

    # Get DPR entries
    dpr_entries = frappe.get_all(
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