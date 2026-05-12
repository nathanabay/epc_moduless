"""
EPC Modules - Main Application Entry Point

This module serves as the primary entry point for the EPC Project Management
application, providing access to core utilities and configuration.
"""

import frappe
from epc_modules.utils import get_epc_logger

logger = get_epc_logger(__name__)

def get_typology_config(project_name):
    """
    Retrieve and cache typology configuration for a project.

    Args:
        project_name (str): Name of the project

    Returns:
        dict: Typology configuration
    """
    if not frappe.db.exists("Project", project_name):
        frappe.throw(f"Project {project_name} does not exist")

    project = frappe.get_doc("Project", project_name)
    if not project.project_typology:
        frappe.throw("Project does not have a typology assigned")

    return frappe.get_doc("Project Typology", project.project_typology)


def is_epc_project(project_name):
    """Check if a project is managed by the EPC module."""
    if not frappe.db.exists("Project", project_name):
        return False

    project = frappe.get_cached_doc("Project", project_name)
    return bool(project.project_typology)


def get_project_billing_track(project_name):
    """Get the billing track for a project based on its typology."""
    if not is_epc_project(project_name):
        return "standard"

    typology = get_typology_config(project_name)
    return typology.billing_track