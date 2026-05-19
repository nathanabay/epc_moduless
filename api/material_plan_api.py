"""
Material Plan API Module

API endpoints for Material Plan management.
"""

import frappe
from frappe import _
from frappe.utils import today, flt, cstr
from epc_modules.utils import get_epc_logger

logger = get_epc_logger(__name__)


@frappe.whitelist()
def get_material_plan(project=None):
    """
    Get all material plans for a project.

    Args:
        project (str, optional): Filter by project

    Returns:
        dict: { "plans": [ ... ] }
    """
    frappe.has_permission("Material Plan", "read", throw=True)

    filters = {}
    if project:
        filters["project"] = project

    plans = frappe.get_all(
        "Material Plan",
        filters=filters,
        fields=["name", "project", "plan_date", "status", "estimated_total", "notes"]
    )

    for plan in plans:
        item_count = frappe.db.count("Material Plan Item", {"parent": plan.name})
        plan["item_count"] = item_count

    return {"plans": plans}


@frappe.whitelist()
def get_material_plan_details(name):
    """
    Get material plan with all items.

    Args:
        name (str): Material Plan name

    Returns:
        dict: { plan: {...}, items: [...] }
    """
    frappe.has_permission("Material Plan", "read", throw=True)

    doc = frappe.get_doc("Material Plan", name)
    items = frappe.get_all(
        "Material Plan Item",
        filters={"parent": name},
        fields=["name", "item_code", "item_name", "description", "uom",
                "required_quantity", "ordered_quantity", "unit_rate",
                "estimated_cost", "procurement_status", "target_date",
                "supplier", "purchase_order"]
    )

    return {"plan": doc, "items": items}


@frappe.whitelist()
def generate_from_boq(project, boq_filters=None):
    """
    Generate Material Plan Items from Custom BOQ lines.

    Args:
        project (str): Project name
        boq_filters (dict, optional): Filter for BOQ lines

    Returns:
        list: Generated material plan items
    """
    frappe.has_permission("Material Plan", "write", throw=True)

    # Get all Custom BOQ names for this project first
    boq_names = [d.name for d in frappe.get_all("Custom BOQ", filters={"project": project})]
    if not boq_names:
        return []

    boq_items = frappe.get_all(
        "Custom BOQ Item",
        filters={"parent": ["in", boq_names]},
        fields=["item_code", "item_name", "description", "uom", "qty", "rate"]
    )

    generated = []
    for item in boq_items:
        generated.append({
            "item_code": item.item_code,
            "item_name": item.item_name,
            "description": item.description,
            "uom": item.uom,
            "required_quantity": item.qty,
            "unit_rate": item.rate,
            "estimated_cost": flt(item.qty) * flt(item.rate),
            "procurement_status": "Pending"
        })

    return generated


@frappe.whitelist()
def generate_from_wbs(project, wbs_filters=None):
    """
    Generate Material Plan Items from WBS items with material requirements.

    Args:
        project (str): Project name
        wbs_filters (dict, optional): Filter for WBS items

    Returns:
        list: Generated material plan items
    """
    frappe.has_permission("Material Plan", "write", throw=True)

    wbs_items = frappe.get_all(
        "WBS Item",
        filters={"project": project},
        fields=["name", "wbs_name", "material_items"]
    )

    generated = []
    for wbs in wbs_items:
        if wbs.get("material_items"):
            try:
                materials = frappe.parse_json(wbs.material_items) if isinstance(wbs.material_items, str) else wbs.material_items
                for mat in materials:
                    generated.append({
                        "item_code": mat.get("item_code"),
                        "item_name": mat.get("item_name", wbs.wbs_name),
                        "description": mat.get("description", ""),
                        "uom": mat.get("uom"),
                        "required_quantity": mat.get("qty", 0),
                        "unit_rate": mat.get("rate", 0),
                        "estimated_cost": flt(mat.get("qty", 0)) * flt(mat.get("rate", 0)),
                        "procurement_status": "Pending"
                    })
            except Exception:
                pass

    return generated


@frappe.whitelist()
def create_material_plan(project, items=None, plan_date=None, notes=None):
    """
    Create new Material Plan with items.

    Args:
        project (str): Project name
        items (list, optional): List of item dicts
        plan_date (str, optional): Plan date
        notes (str, optional): Notes

    Returns:
        str: New Material Plan name
    """
    frappe.has_permission("Material Plan", "write", throw=True)

    doc = frappe.new_doc("Material Plan")
    doc.project = project
    doc.plan_date = plan_date or today()
    doc.notes = notes

    for item in (items or []):
        doc.append("items", {
            "item_code": item.get("item_code"),
            "item_name": item.get("item_name"),
            "description": item.get("description"),
            "uom": item.get("uom"),
            "required_quantity": flt(item.get("required_quantity")),
            "unit_rate": flt(item.get("unit_rate")),
            "estimated_cost": flt(item.get("required_quantity", 0)) * flt(item.get("unit_rate", 0)),
            "procurement_status": item.get("procurement_status", "Pending"),
            "target_date": item.get("target_date"),
            "supplier": item.get("supplier")
        })

    doc.insert()
    return doc.name


@frappe.whitelist()
def update_item_status(item_name, procurement_status, purchase_order=None):
    """
    Update procurement status of a line item.

    Args:
        item_name (str): Material Plan Item name
        procurement_status (str): New status
        purchase_order (str, optional): Linked PO

    Returns:
        str: Updated item name
    """
    frappe.has_permission("Material Plan", "write", throw=True)

    doc = frappe.get_doc("Material Plan Item", item_name)
    doc.procurement_status = procurement_status
    if purchase_order:
        doc.purchase_order = purchase_order
    doc.save()
    return doc.name


@frappe.whitelist()
def submit_plan(name):
    """
    Change status from Draft to Approved.

    Args:
        name (str): Material Plan name

    Returns:
        str: Updated plan name
    """
    frappe.has_permission("Material Plan", "submit", throw=True)

    doc = frappe.get_doc("Material Plan", name)
    if doc.status == "Draft":
        doc.db_set("status", "Approved")
        doc.reload()

    return doc.name