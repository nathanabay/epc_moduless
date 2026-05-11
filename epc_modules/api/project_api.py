"""
EPC Project API

API endpoints for project-related operations.
"""

import frappe
from frappe import _
from frappe.utils import today, now_datetime, get_datetime
from epc_modules.utils import validate_project_typology, get_epc_logger

logger = get_epc_logger(__name__)


@frappe.whitelist()
def get_polymorphic_boq(project, measurement_method=None):
    """
    Retrieve BOQ items filtered by project and optional measurement method.

    Args:
        project (str): Project name
        measurement_method (str, optional): Filter by measurement method

    Returns:
        list: BOQ items matching criteria
    """
    if not frappe.db.exists("Project", project):
        frappe.throw(_("Project {0} does not exist").format(project))

    filters = {"parent": project}
    if measurement_method:
        filters["measurement_method"] = measurement_method

    boq_items = frappe.get_all(
        "Custom BOQ Item",
        filters=filters,
        fields=["*"]
    )

    return boq_items


@frappe.whitelist()
def submit_dpr(data):
    """
    Submit Daily Progress Report from web or mobile interface.

    Args:
        data (dict): DPR data including project, date, supervisor, entries

    Returns:
        str: Created DPR document name
    """
    frappe.has_permission("Daily Progress Report", "create", throw=True)

    doc = frappe.get_doc({
        "doctype": "Daily Progress Report",
        "project": data.get("project"),
        "report_date": data.get("report_date", today()),
        "supervisor": data.get("supervisor", frappe.session.user),
        "site_zone": data.get("site_zone"),
        "weather_conditions": data.get("weather_conditions"),
        "labor_count": data.get("labor_count"),
        "work_shifts": data.get("work_shifts", 1),
        "progress_entries": data.get("entries", [])
    })

    doc.insert()

    # Trigger progress recalculation
    if hasattr(frappe, 'get_doc'):
        try:
            from epc_modules.utils.boq_calculator import BOQCalculator
            BOQCalculator.aggregate_project_progress(data.get("project"))
        except Exception as e:
            logger.warning(f"Progress recalc failed: {str(e)}")

    return {"name": doc.name, "status": "success"}


@frappe.whitelist()
def get_project_dashboard(project):
    """
    Get dashboard data for a project.

    Args:
        project (str): Project name

    Returns:
        dict: Dashboard metrics
    """
    if not frappe.db.exists("Project", project):
        frappe.throw(_("Project {0} does not exist").format(project))

    doc = frappe.get_doc("Project", project)

    # Get typology
    typology = None
    if doc.project_typology:
        typology = frappe.get_doc("Project Typology", doc.project_typology)

    # Calculate metrics
    total_boq_value = frappe.db.sql("""
        SELECT SUM(total_value)
        FROM `tabCustom BOQ Item`
        WHERE parent = %s
    """, project)[0][0] or 0

    certified_value = frappe.db.sql("""
        SELECT SUM(net_payable)
        FROM `tabRA Bill`
        WHERE project = %s AND docstatus = 1
    """, project)[0][0] or 0

    pending_billing = frappe.db.sql("""
        SELECT SUM(certified_value)
        FROM `tabRA Bill`
        WHERE project = %s AND docstatus = 0
    """, project)[0][0] or 0

    open_ncrs = frappe.db.count("Non-Conformance Report", {
        "project": project,
        "status": ["in", ["Open", "In Progress"]]
    })

    return {
        "project": project,
        "project_name": doc.project_name,
        "status": doc.status,
        "typology": typology.name if typology else None,
        "typology_type": typology.typology_type if typology else None,
        "percent_complete": doc.percent_complete or 0,
        "total_boq_value": total_boq_value,
        "certified_value": certified_value,
        "pending_billing": pending_billing,
        "open_ncrs": open_ncrs,
        "contract_value": doc.contract_value or 0,
        "expected_start": doc.expected_start,
        "expected_end": doc.expected_end
    }


@frappe.whitelist()
def calculate_project_progress(project):
    """
    Calculate and update project progress.

    Args:
        project (str): Project name

    Returns:
        dict: Updated progress metrics
    """
    if not validate_project_typology(project):
        return None

    try:
        from epc_modules.utils.boq_calculator import BOQCalculator
        progress = BOQCalculator.aggregate_project_progress(project)

        # Update project document
        frappe.db.set_value("Project", project, "percent_complete", progress)

        return {
            "project": project,
            "progress_percentage": progress,
            "status": "success"
        }
    except Exception as e:
        logger.error(f"Progress calculation failed for {project}: {str(e)}")
        return {
            "project": project,
            "status": "error",
            "message": str(e)
        }