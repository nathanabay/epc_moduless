"""
Typology API Module

REST API endpoints for typology operations.
"""

import frappe
from frappe import _
from epc_modules.utils import get_epc_logger
from epc_modules.utils.typology_engine import TypologyEngine

logger = get_epc_logger(__name__)


@frappe.whitelist()
def get_typology_config(typology_name):
    """
    Get complete UI configuration for a typology.

    Args:
        typology_name (str): Typology name

    Returns:
        dict: Complete UI configuration
    """
    frappe.has_permission("Project Typology", "read", throw=True)

    if not frappe.db.exists("Project Typology", typology_name):
        frappe.throw(_("Typology {0} does not exist").format(typology_name))

    config = TypologyEngine.get_ui_config(typology_name)
    return config


@frappe.whitelist()
def get_field_visibility(typology_name):
    """
    Get field visibility settings for a typology.

    Args:
        typology_name (str): Typology name

    Returns:
        dict: Field visibility settings
    """
    frappe.has_permission("Project Typology", "read", throw=True)

    if not frappe.db.exists("Project Typology", typology_name):
        frappe.throw(_("Typology {0} does not exist").format(typology_name))

    return TypologyEngine.get_field_visibility(typology_name)


@frappe.whitelist()
def get_tab_visibility(typology_name):
    """
    Get tab visibility settings for a typology.

    Args:
        typology_name (str): Typology name

    Returns:
        dict: Tab visibility settings
    """
    frappe.has_permission("Project Typology", "read", throw=True)

    if not frappe.db.exists("Project Typology", typology_name):
        frappe.throw(_("Typology {0} does not exist").format(typology_name))

    return TypologyEngine.get_tab_visibility(typology_name)


@frappe.whitelist()
def get_all_typologies(include_inactive=0):
    """
    Get all available typologies.

    Args:
        include_inactive (int): Include inactive typologies (0 or 1)

    Returns:
        list: List of typology configurations
    """
    frappe.has_permission("Project Typology", "read", throw=True)

    return TypologyEngine.get_all_typologies(bool(include_inactive))


@frappe.whitelist()
def get_measurement_methods(typology_name):
    """
    Get available measurement methods for a typology.

    Args:
        typology_name (str): Typology name

    Returns:
        list: Allowed measurement methods
    """
    frappe.has_permission("Project Typology", "read", throw=True)

    if not frappe.db.exists("Project Typology", typology_name):
        frappe.throw(_("Typology {0} does not exist").format(typology_name))

    return TypologyEngine.get_measurement_methods(typology_name)


@frappe.whitelist()
def get_required_fields(typology_name):
    """
    Get list of required fields for a typology.

    Args:
        typology_name (str): Typology name

    Returns:
        list: Required field names
    """
    frappe.has_permission("Project Typology", "read", throw=True)

    if not frappe.db.exists("Project Typology", typology_name):
        frappe.throw(_("Typology {0} does not exist").format(typology_name))

    return TypologyEngine.get_required_fields(typology_name)


@frappe.whitelist()
def get_project_typology(project_name):
    """
    Get typology configuration for a project.

    Args:
        project_name (str): Project name

    Returns:
        dict: Typology configuration
    """
    frappe.has_permission("Project", "read", project_name, throw=True)

    project = frappe.get_doc("Project", project_name)

    if not project.project_typology:
        frappe.throw(_("Project does not have a typology assigned"))

    return {
        "typology_name": project.project_typology,
        "config": TypologyEngine.get_ui_config(project.project_typology)
    }


@frappe.whitelist()
def check_typology_requirements(project_name, check_type):
    """
    Check specific typology requirements for a project.

    Args:
        project_name (str): Project name
        check_type (str): Type of check (tbe, measurement_book, spatial_zones)

    Returns:
        dict: Check result
    """
    frappe.has_permission("Project", "read", project_name, throw=True)

    if not frappe.db.exists("Project", project_name):
        frappe.throw(_("Project {0} does not exist").format(project_name))

    project = frappe.get_doc("Project", project_name)

    if not project.project_typology:
        return {"required": False, "message": "No typology assigned"}

    typology = frappe.get_cached_doc("Project Typology", project.project_typology)

    checks = {
        "tbe": lambda: typology.requires_tbe,
        "measurement_book": lambda: typology.requires_measurement_book,
        "spatial_zones": lambda: typology.requires_spatial_zones,
        "itp": lambda: typology.requires_itp,
    }

    if check_type not in checks:
        frappe.throw(_("Invalid check type: {0}").format(check_type))

    required = checks[check_type]()

    return {
        "required": bool(required),
        "typology_type": typology.typology_type,
        "typology_name": typology.name
    }


@frappe.whitelist()
def get_inventory_strategy_for_project(project_name):
    """
    Get inventory strategy for a project.

    Args:
        project_name (str): Project name

    Returns:
        dict: Inventory strategy configuration
    """
    frappe.has_permission("Project", "read", project_name, throw=True)

    if not frappe.db.exists("Project", project_name):
        frappe.throw(_("Project {0} does not exist").format(project_name))

    project = frappe.get_doc("Project", project_name)

    if not project.project_typology:
        return {"strategy": "standard", "message": "No typology assigned"}

    typology = frappe.get_cached_doc("Project Typology", project.project_typology)

    strategy_map = {
        "Spatial-Zone": {
            "strategy": "spatial_zone",
            "requires_zones": True,
            "allow_bulk": False
        },
        "Bulk-Warehouse": {
            "strategy": "bulk_warehouse",
            "requires_zones": False,
            "allow_bulk": True
        },
        "Hidden": {
            "strategy": "hidden",
            "requires_zones": False,
            "allow_bulk": False
        }
    }

    return strategy_map.get(typology.inventory_strategy, {
        "strategy": "standard",
        "requires_zones": False,
        "allow_bulk": True
    })