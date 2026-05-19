"""
BOQ API Module

REST API endpoints for Bill of Quantities operations.
"""

import frappe
import os
from frappe import _
from epc_modules.utils import get_epc_logger
from epc_modules.utils.boq_calculator import BOQCalculator

logger = get_epc_logger(__name__)


@frappe.whitelist()
def calculate_polymorphic_boq(project_name, items=None):
    """
    Calculate BOQ based on project's typology.

    Args:
        project_name (str): Project name
        items (list): Optional list of BOQ items

    Returns:
        dict: Calculated BOQ results
    """
    if not frappe.db.exists("Project", project_name):
        frappe.throw(_("Project {0} does not exist").format(project_name))

    project = frappe.get_doc("Project", project_name)

    if not project.is_epc_project:
        return {"error": "Not an EPC project"}

    calculator = BOQCalculator(project_name, project.project_typology)
    return calculator.calculate_boq(items)


@frappe.whitelist()
def get_boq_summary(project_name):
    """
    Get BOQ summary for a project.

    Args:
        project_name (str): Project name

    Returns:
        dict: BOQ summary
    """
    if not frappe.db.exists("Project", project_name):
        frappe.throw(_("Project {0} does not exist").format(project_name))

    project = frappe.get_doc("Project", project_name)

    calculator = BOQCalculator(project_name, project.project_typology)
    return calculator.get_summary()


@frappe.whitelist()
def get_wbs_structure(project_name):
    """
    Get WBS structure for a project.

    Args:
        project_name (str): Project name

    Returns:
        list: WBS hierarchy
    """
    if not frappe.db.exists("Project", project_name):
        frappe.throw(_("Project {0} does not exist").format(project_name))

    from epc_modules.utils.wbs_generator import WBSStructureGenerator

    project = frappe.get_doc("Project", project_name)

    if not project.project_typology:
        return []

    return WBSStructureGenerator.create_wbs_structure(
        project_name,
        project.project_typology
    )


@frappe.whitelist()
def add_boq_item(project_name, item_code, quantity, rate=None, wbs_code=None):
    """
    Add an item to the project BOQ.

    Args:
        project_name (str): Project name
        item_code (str): Item code
        quantity (float): Quantity
        rate (float): Optional rate
        wbs_code (str): Optional WBS code

    Returns:
        dict: Created BOQ item
    """
    if not frappe.db.exists("Project", project_name):
        frappe.throw(_("Project {0} does not exist").format(project_name))

    if not frappe.db.exists("Item", item_code):
        frappe.throw(_("Item {0} does not exist").format(item_code))

    project = frappe.get_doc("Project", project_name)

    doc = frappe.get_doc({
        "doctype": "Custom BOQ",
        "project": project_name,
        "item_code": item_code,
        "qty": quantity,
        "rate": rate or frappe.db.get_value("Item", item_code, "valuation_rate") or 0,
        "wbs_code": wbs_code
    })
    doc.insert(ignore_permissions=True)

    logger.info(f"Added BOQ item {item_code} to project {project_name}")

    return {
        "name": doc.name,
        "item_code": item_code,
        "qty": quantity,
        "amount": doc.amount
    }


@frappe.whitelist()
def update_boq_item(item_name, quantity=None, rate=None):
    """
    Update a BOQ item.

    Args:
        item_name (str): BOQ item name
        quantity (float): New quantity
        rate (float): New rate

    Returns:
        dict: Updated item
    """
    if not frappe.db.exists("Custom BOQ", item_name):
        frappe.throw(_("Custom BOQ {0} does not exist").format(item_name))

    doc = frappe.get_doc("Custom BOQ", item_name)

    if quantity is not None:
        doc.qty = quantity
    if rate is not None:
        doc.rate = rate

    doc.save(ignore_permissions=True)

    return {
        "name": doc.name,
        "qty": doc.qty,
        "rate": doc.rate,
        "amount": doc.amount
    }


@frappe.whitelist()
def delete_boq_item(item_name):
    """
    Delete a BOQ item.

    Args:
        item_name (str): BOQ item name
    """
    if not frappe.db.exists("Custom BOQ", item_name):
        frappe.throw(_("Custom BOQ {0} does not exist").format(item_name))

    frappe.delete_doc("Custom BOQ", item_name)
    logger.info(f"Deleted BOQ item {item_name}")


@frappe.whitelist()
def get_boq_items(project_name, wbs_code=None):
    """
    Get BOQ items for a project or WBS element.

    Args:
        project_name (str): Project name
        wbs_code (str): Optional WBS code filter

    Returns:
        list: BOQ items
    """
    filters = {"project": project_name}
    if wbs_code:
        filters["wbs_code"] = wbs_code

    items = frappe.get_all(
        "Custom BOQ",
        filters=filters,
        fields=["*"],
        order_by="idx"
    )

    return items


@frappe.whitelist()
def calculate_project_value(project_name):
    """
    Calculate total project value from BOQ.

    Args:
        project_name (str): Project name

    Returns:
        dict: Project value breakdown
    """
    project = frappe.get_doc("Project", project_name)

    calculator = BOQCalculator(project_name, project.project_typology)
    summary = calculator.get_summary()

    return {
        "project_name": project_name,
        "boq_value": summary.get("total_value", 0),
        "contract_value": project.contract_value or 0,
        "variance": (project.contract_value or 0) - summary.get("total_value", 0),
        "item_count": summary.get("item_count", 0)
    }


@frappe.whitelist()
def import_boq_from_csv(project_name, csv_path=None):
    """Import BOQ from CSV file for Arat Kilo project."""
    if not frappe.db.exists("Project", project_name):
        frappe.throw(_("Project {0} does not exist").format(project_name))

    if csv_path is None:
        csv_path = os.path.join(
            os.path.dirname(frappe.get_app_path("epc_bespo")),
            "Arat Kilo  BOQ for BID.csv"
        )

    if not os.path.exists(csv_path):
        frappe.throw(_("BOQ CSV file not found at {0}").format(csv_path))

    from epc_modules.utils.boq_importer import AratKiloBOQImporter

    importer = AratKiloBOQImporter()
    items = importer.parse_csv(csv_path)
    result = importer.import_to_project(project_name, items)

    logger.info(f"Imported {result['count']} BOQ items for project {project_name}")
    return result


@frappe.whitelist()
def get_boq_section_summary(project_name):
    """Get BOQ summary grouped by sections."""
    from frappe.utils import flt

    items = frappe.get_all(
        "Custom BOQ",
        filters={"project": project_name},
        fields=["item_code", "total_value", "boq_quantity", "unit_rate", "wbs_code"]
    )

    sections = {}
    for item in items:
        # Extract section from wbs_code (e.g., "DEMO-011" -> "01")
        section = "MISC"
        if item.get("wbs_code"):
            for sec_id, sec_info in AratKiloBOQImporter.SECTION_MAP.items():
                if item.wbs_code.startswith(sec_info["wbs_prefix"]):
                    section = sec_id
                    break

        if section not in sections:
            sections[section] = {"count": 0, "total_value": 0, "total_qty": 0}
        sections[section]["count"] += 1
        sections[section]["total_value"] += flt(item.total_value)
        sections[section]["total_qty"] += flt(item.boq_quantity)

    return {
        "project": project_name,
        "sections": sections,
        "grand_total": sum(s["total_value"] for s in sections.values())
    }


# Import this at module level for reference
from epc_modules.utils.boq_importer import AratKiloBOQImporter
