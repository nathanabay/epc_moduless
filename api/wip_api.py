"""
WIP API Module

API endpoints for Work-in-Progress reporting.
"""

import frappe
from frappe import _
from frappe.utils import today, flt
from epc_modules.utils import get_epc_logger

logger = get_epc_logger(__name__)

# Default labor rate (USD/hour) - fetched from project or system settings at runtime
# Use get_default_labor_rate() function instead of hardcoded constant


def get_default_labor_rate(project=None):
    """
    Get labor rate for project, falling back to system default.

    Args:
        project (str, optional): Project name to get rate from

    Returns:
        float: Labor rate in USD/hour
    """
    if project:
        try:
            rate = frappe.db.get_value("Project", project, "labor_rate")
            if rate:
                return flt(rate)
        except Exception:
            pass

    # Fallback to system setting
    try:
        default_rate = frappe.db.get_single_value("EPC Settings", "default_labor_rate")
        if default_rate:
            return flt(default_rate)
    except Exception:
        pass

    # Last resort fallback
    return 12


@frappe.whitelist()
def get_wip_report(project=None):
    """
    Get combined WIP report with Financial, Progress, and Resource tabs.

    Args:
        project (str, optional): Filter by specific project

    Returns:
        dict: { "financial": [...], "progress": [...], "resource": [...] }
    """
    frappe.has_permission("Project", "read", throw=True)

    filters = {"is_epc_project": 1}
    if project:
        filters["name"] = project

    projects = frappe.get_all(
        "Project",
        filters=filters,
        fields=["name", "project_name", "contract_value", "percent_complete",
                "project_typology", "status", "expected_start", "expected_end"]
    )

    return {
        "financial": _get_financial_wip(projects),
        "progress": _get_progress_wip(projects),
        "resource": _get_resource_wip(projects)
    }


def _get_financial_wip(projects):
    """
    Calculate Financial WIP per project.

    WIP = Certified value not yet invoiced.
    """
    result = []
    for p in projects:
        # Get certified value from RA Bills (submitted only)
        certified = frappe.db.sql("""
            SELECT SUM(net_payable) as total
            FROM `tabRA Bill`
            WHERE project = %s AND docstatus = 1
        """, p.name, as_dict=1)
        certified_value = certified[0].total if (certified and certified[0].total is not None) else 0

        # Get invoiced value (RA Bills that are Invoiced status)
        invoiced = frappe.db.sql("""
            SELECT SUM(net_payable) as total
            FROM `tabRA Bill`
            WHERE project = %s AND docstatus = 1 AND billing_status = 'Invoiced'
        """, p.name, as_dict=1)
        invoiced_value = invoiced[0].total if (invoiced and invoiced[0].total is not None) else 0

        wip_value = max(0, certified_value - invoiced_value)

        # Get retention settings from project typology
        retention_pct = 10  # default 10%
        retention_recovery_pct = 50  # default 50%
        if p.project_typology:
            try:
                typology = frappe.get_doc("Project Typology", p.project_typology)
                retention_pct = typology.retention_percentage or 10
                retention_recovery_pct = typology.retention_recovery_percentage or 50
            except Exception:
                pass

        retention = wip_value * (retention_pct / 100)
        retention_recoverable = wip_value - retention

        result.append({
            "project": p.name,
            "project_name": p.project_name,
            "contract_value": p.contract_value or 0,
            "certified_value": certified_value,
            "invoiced_value": invoiced_value,
            "wip_value": wip_value,
            "retention": retention,
            "retention_recoverable": retention_recoverable
        })

    return result


def _get_progress_wip(projects):
    """
    Calculate Progress WIP per WBS item.

    Compares actual progress vs planned per WBS element.
    """
    result = []
    for p in projects:
        wbs_items = frappe.get_all(
            "WBS Item",
            filters={"project": p.name},
            fields=["name", "wbs_name", "wbs_code", "percent_complete",
                    "planned_value", "earned_value", "wbs_status",
                    "planned_start", "planned_end", "actual_start", "actual_end"]
        )

        for wbs in wbs_items:
            planned = wbs.percent_complete or 0
            actual = (wbs.earned_value / wbs.planned_value * 100) if wbs.planned_value else 0
            variance = actual - planned

            status = "On Track"
            if variance < -10:
                status = "Critical"
            elif variance < 0:
                status = "Behind"

            result.append({
                "project": p.name,
                "project_name": p.project_name,
                "wbs_item": wbs.wbs_name,
                "wbs_code": wbs.wbs_code,
                "planned_progress": planned,
                "actual_progress": actual,
                "variance": variance,
                "status": status
            })

    return result


def _get_resource_wip(projects):
    """
    Calculate Resource WIP from DPR labor data.
    """
    result = []
    for p in projects:
        # Sum labor from DPR entries
        labor_rate = get_default_labor_rate(p.name)
        labor_data = frappe.db.sql("""
            SELECT
                SUM(labor_count * work_shifts) as total_hours,
                SUM(labor_count * work_shifts * %s) as labor_cost
            FROM `tabDPR Entry`
            WHERE parent IN (
                SELECT name FROM `tabDaily Progress Report`
                WHERE project = %s AND docstatus = 1
            )
        """, (labor_rate, p.name), as_dict=1)

        total_hours = labor_data[0].total_hours if labor_data else 0
        labor_cost = labor_data[0].labor_cost if labor_data else 0

        # Check billing status
        billed_hours = frappe.db.sql("""
            SELECT SUM(qty) as total
            FROM `tabRA Bill MB Reference` rb
            JOIN `tabRA Bill` ra ON rb.parent = ra.name
            WHERE ra.project = %s AND ra.docstatus = 1
        """, p.name, as_dict=1)
        billed = billed_hours[0].total if billed_hours else 0

        result.append({
            "project": p.name,
            "project_name": p.project_name,
            "total_hours": total_hours or 0,
            "labor_cost": labor_cost or 0,
            "billed_hours": billed or 0,
            "unbilled_hours": (total_hours or 0) - (billed or 0),
            "billing_status": "Billed" if (billed or 0) >= (total_hours or 0) else "Unbilled"
        })

    return result