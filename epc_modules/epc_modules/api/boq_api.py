"""
BOQ API Module

REST API endpoints for Bill of Quantities operations.
"""

import frappe
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
        "doctype": "BOQ Item",
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
    if not frappe.db.exists("BOQ Item", item_name):
        frappe.throw(_("BOQ Item {0} does not exist").format(item_name))

    doc = frappe.get_doc("BOQ Item", item_name)

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
    if not frappe.db.exists("BOQ Item", item_name):
        frappe.throw(_("BOQ Item {0} does not exist").format(item_name))

    frappe.delete_doc("BOQ Item", item_name)
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
        "BOQ Item",
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
