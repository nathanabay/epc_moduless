"""
EPC Modules Utilities

Provides shared utility functions and classes for the EPC module.
"""

import frappe
import logging
from typing import Optional, List, Dict, Any

def get_epc_logger(module_name: str) -> logging.Logger:
    """Get a configured logger for the EPC module."""
    logger = logging.getLogger(module_name)
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    return logger


class EPCException(frappe.ValidationError):
    """Custom exception for EPC module errors."""
    pass


def validate_project_typology(project_name: str) -> bool:
    """
    Validate that a project has a valid typology assigned.

    Args:
        project_name: Name of the project

    Returns:
        bool: True if valid

    Raises:
        EPCException: If validation fails
    """
    if not frappe.db.exists("Project", project_name):
        raise EPCException(f"Project {project_name} does not exist")

    project = frappe.get_doc("Project", project_name)
    if not project.get("project_typology"):
        raise EPCException("Project must have a Typology assigned")

    if not frappe.db.exists("Project Typology", project.project_typology):
        raise EPCException(f"Typology {project.project_typology} does not exist")

    return True


def get_active_projects_by_typology(typology_name: str) -> List[str]:
    """Get all active projects for a given typology."""
    return frappe.get_all(
        "Project",
        filters={
            "project_typology": typology_name,
            "status": "Active"
        },
        pluck="name"
    )


def create_site_warehouse(project_name: str, warehouse_name: str = None) -> str:
    """
    Create a default site warehouse for a project.

    Args:
        project_name: Name of the project
        warehouse_name: Optional custom warehouse name

    Returns:
        str: Name of created warehouse
    """
    project = frappe.get_doc("Project", project_name)

    if not warehouse_name:
        warehouse_name = f"{project.name} - Site Stores"

    if frappe.db.exists("Warehouse", warehouse_name):
        return warehouse_name

    # Get company from project
    company = project.company or frappe.defaults.get_user_default("company")

    # Get parent warehouse (handle missing default_warehouse column gracefully)
    parent_warehouse = None
    if company and frappe.db.has_column("Company", "default_warehouse"):
        parent_warehouse = frappe.db.get_value("Company", company, "default_warehouse") or ""

    warehouse = frappe.get_doc({
        "doctype": "Warehouse",
        "warehouse_name": warehouse_name,
        "is_group": 0,
        "parent_warehouse": parent_warehouse or "",
        "company": company,
        "project": project_name
    })

    frappe.has_permission("Warehouse", "create", throw=True)
    warehouse.insert()
    return warehouse.name


def get_vat_account_head() -> Optional[str]:
    """
    Look up VAT account from the Account doctype.

    Returns:
        Account name if found, None otherwise.
    """
    vat_account = frappe.db.get_value(
        "Account",
        {"account_name": ["like", "%VAT%"]},
        "name"
    )
    if not vat_account:
        logger = get_epc_logger("billing")
        logger.warning("No VAT account found in the system. Account head will be empty.")
    return vat_account


def get_default_cost_center() -> Optional[str]:
    """
    Look up the default cost center from the Company defaults.

    Returns:
        Cost center name if found, None otherwise.
    """
    company = frappe.defaults.get_user_default("company")
    if not company:
        logger = get_epc_logger("billing")
        logger.warning("No default company set. Cannot determine cost center.")
        return None

    cost_center = frappe.db.get_value(
        "Company", company, "default_cost_center"
    ) or frappe.db.get_value(
        "Company", company, "cost_center"
    )
    if not cost_center:
        logger = get_epc_logger("billing")
        logger.warning(
            f"No default cost center found for company '{company}'. "
            "Cost center will be empty."
        )
    return cost_center


def log_epc_activity(
    doctype: str,
    docname: str,
    action: str,
    user: str = None,
    meta: Dict[str, Any] = None
) -> None:
    """
    Log EPC module activity for audit trail.

    Args:
        doctype: Document type
        docname: Document name
        action: Action performed
        user: User who performed action
        meta: Additional metadata
    """
    if not user:
        user = frappe.session.user if hasattr(frappe, 'session') else "System"

    doc = frappe.get_doc({
        "doctype": "Activity Log",
        "doctype_ref": doctype,
        "docname_ref": docname,
        "action": action,
        "user": user,
        "ip_address": frappe.local.request_ip if hasattr(frappe, 'local') else None,
        "metadata": frappe.as_json(meta) if meta else None
    })

    frappe.has_permission("Activity Log", "create", throw=True)
    doc.insert()