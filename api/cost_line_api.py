"""
Cost Line API Module

API endpoints for Cost Line Breakdown reporting.
"""

import frappe
from frappe import _
from frappe.utils import flt, today
from epc_modules.utils import get_epc_logger

logger = get_epc_logger(__name__)


@frappe.whitelist()
def get_cost_breakdown(project=None):
    """
    Get combined cost breakdown with project-level summary and WBS-level detail.

    Args:
        project (str, optional): Filter by specific project

    Returns:
        dict: {
          "project_level": { "total_estimated": float, "total_actual": float, "variance": float, "by_category": {...} },
          "wbs_level": [ { "wbs_item": str, "wbs_code": str, "cost_lines": [...], "totals": {...} } ]
        }
    """
    frappe.has_permission("Project", "read", throw=True)

    filters = {"is_epc_project": 1}
    if project:
        filters["name"] = project

    projects = frappe.get_all("Project", filters=filters, fields=["name", "project_name"])

    project_level = {
        "total_estimated": 0,
        "total_actual": 0,
        "variance": 0,
        "by_category": {
            "Material": {"estimated": 0, "actual": 0, "variance": 0},
            "Labor": {"estimated": 0, "actual": 0, "variance": 0},
            "Equipment": {"estimated": 0, "actual": 0, "variance": 0},
            "Overhead": {"estimated": 0, "actual": 0, "variance": 0}
        }
    }

    wbs_level = []

    for p in projects:
        breakdowns = frappe.get_all(
            "Cost Line Breakdown",
            filters={"project": p.name},
            fields=["name", "wbs_item", "cost_category", "total_estimated_cost",
                    "total_actual_cost", "variance"]
        )

        for bd in breakdowns:
            cat = bd.cost_category or "Other"
            if cat in project_level["by_category"]:
                project_level["by_category"][cat]["estimated"] += flt(bd.total_estimated_cost)
                project_level["by_category"][cat]["actual"] += flt(bd.total_actual_cost)
                project_level["by_category"][cat]["variance"] += flt(bd.variance)

            project_level["total_estimated"] += flt(bd.total_estimated_cost)
            project_level["total_actual"] += flt(bd.total_actual_cost)
            project_level["variance"] += flt(bd.variance)

        wbs_items = frappe.get_all(
            "WBS Item",
            filters={"project": p.name},
            fields=["name", "wbs_name", "wbs_code"]
        )

        for wi in wbs_items:
            items = frappe.get_all(
                "Cost Line Breakdown",
                filters={"project": p.name, "wbs_item": wi.name},
                fields=["cost_category", "total_estimated_cost", "total_actual_cost", "variance"]
            )

            if items:
                wbs_totals = {"estimated": 0, "actual": 0, "variance": 0}
                cost_lines = []
                for item in items:
                    wbs_totals["estimated"] += flt(item.total_estimated_cost)
                    wbs_totals["actual"] += flt(item.total_actual_cost)
                    wbs_totals["variance"] += flt(item.variance)
                    cost_lines.append({
                        "category": item.cost_category,
                        "estimated": item.total_estimated_cost,
                        "actual": item.total_actual_cost,
                        "variance": item.variance
                    })

                wbs_level.append({
                    "wbs_item": wi.wbs_name,
                    "wbs_code": wi.wbs_code,
                    "cost_lines": cost_lines,
                    "totals": wbs_totals
                })

    return {"project_level": project_level, "wbs_level": wbs_level}


@frappe.whitelist()
def create_cost_breakdown(project, wbs_item=None, cost_category=None, items=None):
    """
    Create a new Cost Line Breakdown with items.
    """
    frappe.has_permission("Cost Line Breakdown", "write", throw=True)

    doc = frappe.new_doc("Cost Line Breakdown")
    doc.project = project
    if wbs_item:
        doc.wbs_item = wbs_item
    if cost_category:
        doc.cost_category = cost_category

    for item in (items or []):
        doc.append("items", {
            "cost_line_item_name": item.get("cost_line_item_name"),
            "cost_category": item.get("cost_category", cost_category),
            "uom": item.get("uom"),
            "quantity": flt(item.get("quantity")),
            "unit_rate": flt(item.get("unit_rate")),
            "estimated_cost": flt(item.get("quantity", 0)) * flt(item.get("unit_rate", 0))
        })

    doc.insert()
    return doc.name


@frappe.whitelist()
def update_cost_line(name, field, value):
    """
    Update a cost line item field.
    """
    frappe.has_permission("Cost Line Breakdown", "write", throw=True)

    doc = frappe.get_doc("Cost Line Breakdown", name)
    if field in ["total_estimated_cost", "total_actual_cost"]:
        doc.set(field, flt(value))
        doc.calculate_totals()
    doc.save()
    return doc.name