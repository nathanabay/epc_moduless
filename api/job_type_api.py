"""
Job Type API Module

API endpoints for Job Type configuration.
"""

import frappe
from frappe import _
from frappe.utils import flt
from epc_modules.utils import get_epc_logger

logger = get_epc_logger(__name__)


@frappe.whitelist()
def get_job_types():
    """
    Get all active job types.

    Returns:
        dict: { "job_types": [ ... ] }
    """
    frappe.has_permission("Job Type", "read", throw=True)

    job_types = frappe.get_all(
        "Job Type",
        filters={"is_active": 1},
        fields=["name", "job_type", "job_category", "description",
                "default_rate", "uom", "is_active", "sort_order"],
        order_by="sort_order, job_type"
    )

    return {"job_types": job_types}


@frappe.whitelist()
def get_job_type_details(name):
    """
    Get job type with breakdown rates.

    Args:
        name (str): Job Type name

    Returns:
        dict: { job_type: {...}, breakdown_rates: [...] }
    """
    frappe.has_permission("Job Type", "read", throw=True)

    doc = frappe.get_doc("Job Type", name)
    breakdown_rates = frappe.get_all(
        "Job Type Breakdown Rate",
        filters={"parent": name},
        fields=["project_typology", "rate", "notes"]
    )

    return {"job_type": doc, "breakdown_rates": breakdown_rates}


@frappe.whitelist()
def create_job_type(job_type, job_category, description=None, default_rate=None, uom=None, breakdown_rates=None):
    """
    Create new job type.

    Args:
        job_type (str): Job type identifier
        job_category (str): Category
        description (str, optional): Description
        default_rate (float, optional): Default rate
        uom (str, optional): Unit of measure
        breakdown_rates (list, optional): List of {project_typology, rate, notes}

    Returns:
        str: New Job Type name
    """
    frappe.has_permission("Job Type", "write", throw=True)

    doc = frappe.new_doc("Job Type")
    doc.job_type = job_type
    doc.job_category = job_category
    doc.description = description
    doc.default_rate = flt(default_rate) if default_rate else 0
    doc.uom = uom or "Hour"

    for br in (breakdown_rates or []):
        doc.append("breakdown_rates", {
            "project_typology": br.get("project_typology"),
            "rate": flt(br.get("rate")),
            "notes": br.get("notes")
        })

    doc.insert()
    return doc.name


@frappe.whitelist()
def update_job_type(name, **kwargs):
    """
    Update job type fields.

    Args:
        name (str): Job Type name
        **kwargs: Fields to update

    Returns:
        str: Updated Job Type name
    """
    frappe.has_permission("Job Type", "write", throw=True)

    doc = frappe.get_doc("Job Type", name)

    allowed_fields = ["job_type", "job_category", "description", "default_rate", "uom", "is_active", "sort_order"]
    for field, value in kwargs.items():
        if field in allowed_fields:
            if field == "default_rate":
                doc.set(field, flt(value))
            else:
                doc.set(field, value)

    doc.save()
    return doc.name


@frappe.whitelist()
def toggle_job_type(name, is_active):
    """
    Enable or disable a job type.

    Args:
        name (str): Job Type name
        is_active (bool): New active status

    Returns:
        str: Updated Job Type name
    """
    frappe.has_permission("Job Type", "write", throw=True)

    doc = frappe.get_doc("Job Type", name)
    doc.is_active = 1 if is_active else 0
    doc.save()
    return doc.name