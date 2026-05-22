"""
Kanban API Module

API endpoint for Kanban project board.
"""

import frappe
from frappe import _
from frappe.utils import today, add_days, flt
from epc_modules.utils import get_epc_logger

logger = get_epc_logger(__name__)


def calculate_health(project_dict):
    """
    Calculate health status for a project.

    Args:
        project_dict (dict): Project data with open_ncrs, percent_complete

    Returns:
        str: "Healthy" | "At Risk" | "Critical"
    """
    open_ncrs = project_dict.get("open_ncrs", 0)

    health = "Healthy"
    if open_ncrs >= 4:
        health = "Critical"
    elif open_ncrs >= 1:
        health = "At Risk"
    return health


def calculate_date_status(start_date, end_date):
    """
    Calculate date-based status for a project.

    Args:
        start_date (str): Project start date (YYYY-MM-DD)
        end_date (str): Project end date (YYYY-MM-DD)

    Returns:
        str: "Upcoming Start" | "In Progress" | "Near Deadline" | "Overdue"
    """
    if not start_date or not end_date:
        return "In Progress"

    today_date = today()
    try:
        from datetime import datetime
        start = datetime.strptime(start_date, "%Y-%m-%d")
        end = datetime.strptime(end_date, "%Y-%m-%d")
        today_dt = datetime.strptime(today_date, "%Y-%m-%d")

        if today_dt < start:
            return "Upcoming Start"
        elif today_dt > end:
            return "Overdue"
        elif (end - today_dt).days <= 30:
            return "Near Deadline"
        else:
            return "In Progress"
    except (ValueError, TypeError):
        return "In Progress"


@frappe.whitelist()
def get_projects():
    """
    Get all EPC projects with pre-calculated health and date_status fields.

    Returns:
        dict: { "projects": [ ... ] }
    """
    frappe.has_permission("Project", "read", throw=True)

    # Fetch all active EPC projects
    projects = frappe.get_all(
        "Project",
        filters={"is_epc_project": 1},
        fields=[
            "name",
            "project_name",
            "customer",
            "city",
            "project_typology",
            "status",
            "percent_complete",
            "contract_value",
            "expected_start",
            "expected_end",
            "is_epc_project"
        ]
    )

    # Collect project names for batch queries
    project_names = [p.name for p in projects]

    # Batch query: count NCRs per project
    ncr_counts = dict(frappe.db.sql(f"""
        SELECT project, COUNT(*) as cnt
        FROM `tabNon-Conformance Report`
        WHERE project IN ({", ".join(["%s"] * len(project_names))})
        AND status IN ('Open', 'In Progress')
        GROUP BY project
    """, project_names))

    # Batch query: count work orders per project
    wo_counts = dict(frappe.db.sql(f"""
        SELECT project, COUNT(*) as cnt
        FROM `tabSubcontractor Work Order`
        WHERE project IN ({", ".join(["%s"] * len(project_names))})
        AND docstatus != 2
        GROUP BY project
    """, project_names))

    # Batch query: count cost sheets per project
    cs_counts = dict(frappe.db.sql(f"""
        SELECT parent, COUNT(*) as cnt
        FROM `tabCustom BOQ`
        WHERE parent IN ({", ".join(["%s"] * len(project_names))})
        GROUP BY parent
    """, project_names))

    result = []
    for p in projects:
        # Get typology name
        typology = None
        if p.get("project_typology"):
            try:
                typology_doc = frappe.get_doc("Project Typology", p.project_typology)
                typology = typology_doc.name
            except Exception:
                typology = p.project_typology

        # Build project dict using pre-batched counts
        project_dict = {
            "name": p.name,
            "project_name": p.project_name,
            "customer": p.customer,
            "location": p.city,  # Fixed: use p.city directly, not SQL alias
            "typology": typology,
            "status": p.status,
            "percent_complete": p.percent_complete or 0,
            "contract_value": p.contract_value or 0,
            "expected_start": p.expected_start,
            "expected_end": p.expected_end,
            "open_ncrs": ncr_counts.get(p.name, 0),
            "work_orders": wo_counts.get(p.name, 0),
            "cost_sheets": cs_counts.get(p.name, 0),
            "health": "Healthy",
            "date_status": "In Progress"
        }

        # Calculate health
        project_dict["health"] = calculate_health(project_dict)

        # Calculate date status
        project_dict["date_status"] = calculate_date_status(
            p.expected_start, p.expected_end
        )

        result.append(project_dict)

    return {"projects": result}