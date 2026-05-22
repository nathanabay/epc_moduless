"""
WBS API Module

REST API endpoints for Work Breakdown Structure operations.
"""

import frappe
from frappe import _
from epc_modules.utils import get_epc_logger
from epc_modules.utils.wbs_generator import WBSStructureGenerator

logger = get_epc_logger(__name__)


@frappe.whitelist()
def get_wbs_hierarchy(project_name):
    """
    Get complete WBS hierarchy for a project.

    Args:
        project_name (str): Project name

    Returns:
        list: Hierarchical WBS elements
    """
    frappe.has_permission("Project", "read", project_name, throw=True)

    if not frappe.db.exists("Project", project_name):
        frappe.throw(_("Project {0} does not exist").format(project_name))

    return WBSStructureGenerator.get_wbs_hierarchy(project_name)


@frappe.whitelist()
def create_wbs_element(project_name, parent_wbs, name, level, is_milestone=0, planned_value=0):
    """
    Create a new WBS element.

    Args:
        project_name (str): Project name
        parent_wbs (str): Parent WBS code
        name (str): Element name
        level (int): WBS level
        is_milestone (int): Is milestone (0 or 1)
        planned_value (float): Planned value

    Returns:
        dict: Created element
    """
    frappe.has_permission("WBS Item", "create", throw=True)
    frappe.has_permission("Project", "read", project_name, throw=True)

    if not frappe.db.exists("Project", project_name):
        frappe.throw(_("Project {0} does not exist").format(project_name))

    project = frappe.get_doc("Project", project_name)

    if not project.project_typology:
        frappe.throw(_("Project does not have a typology assigned"))

    try:
        element = WBSStructureGenerator.add_wbs_element(
            parent_wbs=parent_wbs,
            name=name,
            level=int(level),
            is_milestone=bool(int(is_milestone)),
            planned_value=float(planned_value or 0)
        )
        logger.info(f"Created WBS element {element['wbs_code']} for project {project_name}")
        return element
    except Exception as e:
        frappe.log_error(f"Failed to create WBS element: {str(e)}", "WBS Creation Error")
        frappe.throw(_("Failed to create WBS element: {0}").format(str(e)))


@frappe.whitelist()
def get_wbs_cost_distribution(project_name):
    """
    Get cost distribution across WBS hierarchy.

    Args:
        project_name (str): Project name

    Returns:
        dict: Cost distribution by level and element
    """
    frappe.has_permission("Project", "read", project_name, throw=True)

    if not frappe.db.exists("Project", project_name):
        frappe.throw(_("Project {0} does not exist").format(project_name))

    return WBSStructureGenerator.get_wbs_element_cost_distribution(project_name)


@frappe.whitelist()
def get_wbs_architecture(project_name):
    """
    Get WBS architecture type for a project.

    Args:
        project_name (str): Project name

    Returns:
        dict: Architecture details
    """
    frappe.has_permission("Project", "read", project_name, throw=True)

    if not frappe.db.exists("Project", project_name):
        frappe.throw(_("Project {0} does not exist").format(project_name))

    project = frappe.get_doc("Project", project_name)

    if not project.project_typology:
        return {"architecture": "Phase-Based", "message": "No typology assigned"}

    architecture = WBSStructureGenerator.get_architecture_for_typology(
        project.project_typology
    )

    return {
        "architecture": architecture,
        "typology": project.project_typology
    }


@frappe.whitelist()
def generate_default_wbs(project_name):
    """
    Generate default WBS structure for a project based on typology template.

    Args:
        project_name (str): Project name

    Returns:
        list: Generated WBS elements
    """
    frappe.has_permission("Project", "write", project_name, throw=True)

    if not frappe.db.exists("Project", project_name):
        frappe.throw(_("Project {0} does not exist").format(project_name))

    project = frappe.get_doc("Project", project_name)

    if not project.project_typology:
        frappe.throw(_("Project does not have a typology assigned"))

    try:
        elements = WBSStructureGenerator.create_wbs_structure(
            project_name,
            project.project_typology
        )
        logger.info(f"Generated default WBS for project {project_name}")
        return elements
    except Exception:
        frappe.db.rollback()
        frappe.throw(_("Failed to generate default WBS structure"))


@frappe.whitelist()
def update_wbs_progress(project_name, wbs_code, progress_percent, earned_value=None):
    """
    Update progress for a WBS element.

    Args:
        project_name (str): Project name
        wbs_code (str): WBS code
        progress_percent (float): Progress percentage
        earned_value (float): Optional earned value

    Returns:
        dict: Updated element
    """
    frappe.has_permission("WBS Item", "write", wbs_code, throw=True)

    if not project_name:
        frappe.throw(_("Project name is required"))

    if not frappe.db.exists("Project", project_name):
        frappe.throw(_("Project {0} does not exist").format(project_name))

    if not frappe.db.exists("WBS Item", wbs_code):
        frappe.throw(_("WBS Item {0} does not exist").format(wbs_code))

    doc = frappe.get_doc("WBS Item", wbs_code)
    doc.physical_progress = float(progress_percent)

    if earned_value is not None:
        doc.earned_value = float(earned_value)
    else:
        # Calculate from planned value and progress
        doc.earned_value = (doc.planned_value or 0) * (progress_percent / 100)

    try:
        doc.save()
    except Exception as e:
        frappe.log_error(f"Failed to update WBS progress: {str(e)}", "WBS API Error")
        frappe.throw(_("Failed to update WBS progress: {0}").format(str(e)))

    logger.info(f"Updated WBS {wbs_code} progress to {progress_percent}%")
    return {
        "wbs_code": doc.wbs_code,
        "physical_progress": doc.physical_progress,
        "earned_value": doc.earned_value
    }


@frappe.whitelist()
def get_wbs_children(project_name, parent_wbs):
    """
    Get child elements for a WBS parent.

    Args:
        project_name (str): Project name
        parent_wbs (str): Parent WBS code

    Returns:
        list: Child WBS elements
    """
    frappe.has_permission("WBS Item", "read", throw=True)

    if not frappe.db.exists("Project", project_name):
        frappe.throw(_("Project {0} does not exist").format(project_name))

    children = frappe.get_all(
        "WBS Item",
        filters={"project": project_name, "parent_wbs": parent_wbs},
        fields=["wbs_code", "wbs_name", "level", "is_milestone", "physical_progress", "planned_value", "earned_value"],
        order_by="wbs_code"
    )

    return children


@frappe.whitelist()
def create_arat_kilo_wbs(project_name):
    """Create Arat Kilo specific WBS structure (Civil Phase-Based)."""
    frappe.has_permission("Project", "write", project_name, throw=True)

    if not frappe.db.exists("Project", project_name):
        frappe.throw(_("Project {0} does not exist").format(project_name))

    try:
        from epc_modules.utils.arat_kilo_wbs import create_arat_kilo_wbs as create_fn
        result = create_fn(project_name)
        logger.info(f"Created Arat Kilo WBS for project {project_name}")
        return result
    except Exception:
        frappe.db.rollback()
        frappe.log_error(f"Failed to create Arat Kilo WBS", "WBS Creation Error")
        frappe.throw(_("Failed to create Arat Kilo WBS"))
