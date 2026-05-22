"""
Measurement Book API Module

REST API endpoints for Measurement Book operations (Civil projects).
"""

import frappe
from frappe import _
from frappe.utils import today, flt
from epc_modules.utils import get_epc_logger
from epc_modules.utils.boq_calculator import BOQCalculator

logger = get_epc_logger(__name__)


@frappe.whitelist()
def create_measurement_book(data):
    """
    Create a new Measurement Book entry.

    Args:
        data (dict): MB data

    Returns:
        dict: Created MB document info
    """
    frappe.has_permission("Measurement Book", "create", throw=True)

    project = data.get("project")
    if not project:
        frappe.throw(_("Project is required"))

    if not frappe.db.exists("Project", project):
        frappe.throw(_("Project {0} does not exist").format(project))

    doc = frappe.get_doc({
        "doctype": "Measurement Book",
        "project": project,
        "mb_code": data.get("mb_code") or _generate_mb_code(project),
        "mb_date": data.get("mb_date", today()),
        "wbs_item": data.get("wbs_item"),
        "supervisor": data.get("supervisor", frappe.session.user),
        "site_zone": data.get("site_zone"),
        "location_description": data.get("location_description"),
        "work_description": data.get("work_description"),
        "boq_reference": data.get("boq_reference"),
        "measurement_entries": _prepare_mb_entries(data.get("entries", [])),
        "remarks": data.get("remarks")
    })

    doc.insert()

    return {
        "name": doc.name,
        "mb_code": doc.mb_code,
        "status": "Draft"
    }


@frappe.whitelist()
def get_measurement_books(project, status=None):
    """
    Get Measurement Books for a project.

    Args:
        project (str): Project name
        status (str, optional): Filter by status

    Returns:
        list: Measurement Books
    """
    if not frappe.db.exists("Project", project):
        frappe.throw(_("Project {0} does not exist").format(project))

    filters = {"project": project}
    if status:
        filters["certification_status"] = status

    books = frappe.get_all(
        "Measurement Book",
        filters=filters,
        fields=["name", "mb_code", "mb_date", "certification_status", "total_quantity", "certified_by", "certified_date"],
        order_by="mb_date desc"
    )

    return books


@frappe.whitelist()
def get_mb_details(mb_name):
    """
    Get detailed Measurement Book entry.

    Args:
        mb_name (str): MB document name

    Returns:
        dict: MB details with entries
    """
    if not frappe.db.exists("Measurement Book", mb_name):
        frappe.throw(_("Measurement Book {0} does not exist").format(mb_name))

    doc = frappe.get_doc("Measurement Book", mb_name)

    return {
        "name": doc.name,
        "project": doc.project,
        "mb_code": doc.mb_code,
        "mb_date": doc.mb_date,
        "wbs_item": doc.wbs_item,
        "supervisor": doc.supervisor,
        "site_zone": doc.site_zone,
        "location_description": doc.location_description,
        "work_description": doc.work_description,
        "boq_reference": doc.boq_reference,
        "total_quantity": doc.total_quantity,
        "certification_status": doc.certification_status,
        "certified_by": doc.certified_by,
        "certified_date": doc.certified_date,
        "remarks": doc.remarks,
        "entries": [
            {
                "sl_no": e.sl_no,
                "item_code": e.item_code,
                "item_description": e.item_description,
                "uom": e.uom,
                "length": e.length,
                "breadth": e.breadth,
                "height": e.height,
                "no_of_items": e.no_of_items,
                "quantity": e.quantity,
                "remarks": e.remarks
            }
            for e in doc.measurement_entries
        ]
    }


@frappe.whitelist()
def submit_mb_for_certification(mb_name):
    """
    Submit Measurement Book for certification.

    Args:
        mb_name (str): MB document name

    Returns:
        dict: Submission result
    """
    if not frappe.db.exists("Measurement Book", mb_name):
        frappe.throw(_("Measurement Book {0} does not exist").format(mb_name))

    doc = frappe.get_doc("Measurement Book", mb_name)

    if doc.certification_status != "Draft":
        frappe.throw(_("MB can only be submitted from Draft status"))

    frappe.has_permission("Measurement Book", "write", mb_name, throw=True)

    doc.certification_status = "Submitted"
    doc.save()

    logger.info(f"Measurement Book {mb_name} submitted for certification")

    return {
        "name": doc.name,
        "status": "Submitted"
    }


@frappe.whitelist()
def certify_measurement_book(mb_name, certifying_authority):
    """
    Certify a Measurement Book (Approve).

    Args:
        mb_name (str): MB document name
        certifying_authority (str): User certifying

    Returns:
        dict: Certification result
    """
    if not frappe.db.exists("Measurement Book", mb_name):
        frappe.throw(_("Measurement Book {0} does not exist").format(mb_name))

    doc = frappe.get_doc("Measurement Book", mb_name)

    if doc.certification_status != "Submitted":
        frappe.throw(_("MB must be in Submitted status for certification"))

    frappe.has_permission("Measurement Book", "write", mb_name, throw=True)

    doc.certification_status = "Certified"
    doc.certified_by = certifying_authority or frappe.session.user
    doc.certified_date = today()
    doc.save()

    # Update BOQ billed quantity
    _update_boq_billed_quantity(doc)

    logger.info(f"Measurement Book {mb_name} certified by {doc.certified_by}")

    return {
        "name": doc.name,
        "status": "Certified",
        "certified_by": doc.certified_by,
        "certified_date": doc.certified_date
    }


@frappe.whitelist()
def reject_measurement_book(mb_name, reason):
    """
    Reject a Measurement Book.

    Args:
        mb_name (str): MB document name
        reason (str): Rejection reason

    Returns:
        dict: Rejection result
    """
    if not frappe.db.exists("Measurement Book", mb_name):
        frappe.throw(_("Measurement Book {0} does not exist").format(mb_name))

    doc = frappe.get_doc("Measurement Book", mb_name)

    if doc.certification_status not in ["Draft", "Submitted"]:
        frappe.throw(_("MB cannot be rejected in current status"))

    frappe.has_permission("Measurement Book", "write", mb_name, throw=True)

    doc.certification_status = "Rejected"
    doc.remarks = f"{doc.remarks or ''}\n\nRejection Reason: {reason}".strip()
    doc.save()

    logger.info(f"Measurement Book {mb_name} rejected: {reason}")

    return {
        "name": doc.name,
        "status": "Rejected"
    }


@frappe.whitelist()
def resubmit_measurement_book(mb_name):
    """
    Resubmit a rejected Measurement Book.

    Args:
        mb_name (str): MB document name

    Returns:
        dict: Resubmission result
    """
    if not frappe.db.exists("Measurement Book", mb_name):
        frappe.throw(_("Measurement Book {0} does not exist").format(mb_name))

    doc = frappe.get_doc("Measurement Book", mb_name)

    if doc.certification_status != "Rejected":
        frappe.throw(_("MB must be in Rejected status for resubmission"))

    frappe.has_permission("Measurement Book", "write", mb_name, throw=True)

    doc.certification_status = "Draft"
    doc.save()

    return {
        "name": doc.name,
        "status": "Draft"
    }


@frappe.whitelist()
def get_cumulative_measurements(project, wbs_item=None, item_code=None):
    """
    Get cumulative measurements for a project.

    Args:
        project (str): Project name
        wbs_item (str, optional): Filter by WBS item
        item_code (str, optional): Filter by item code

    Returns:
        dict: Cumulative measurements
    """
    filters = {
        "project": project,
        "certification_status": "Certified"
    }

    if wbs_item:
        filters["wbs_item"] = wbs_item

    books = frappe.get_all(
        "Measurement Book",
        filters=filters,
        fields=["name"]
    )

    cumulative = {}

    for book in books:
        doc = frappe.get_doc("Measurement Book", book.name)
        for entry in doc.measurement_entries:
            key = entry.item_code
            if item_code and key != item_code:
                continue

            if key not in cumulative:
                cumulative[key] = {
                    "item_code": entry.item_code,
                    "item_description": entry.item_description,
                    "uom": entry.uom,
                    "total_quantity": 0,
                    "mb_count": 0
                }

            cumulative[key]["total_quantity"] += entry.quantity
            cumulative[key]["mb_count"] += 1

    return {
        "project": project,
        "wbs_item": wbs_item,
        "item_code": item_code,
        "cumulative_measurements": list(cumulative.values())
    }


def _generate_mb_code(project):
    """Generate unique MB code."""
    prefix = f"MB-{project[:4].upper()}"
    return f"{prefix}-{frappe.generate_hash(length=8).upper()}"


def _prepare_mb_entries(entries):
    """Prepare MB entries from raw data."""
    prepared = []
    for i, entry in enumerate(entries):
        prepared.append({
            "sl_no": entry.get("sl_no", i + 1),
            "item_code": entry.get("item_code"),
            "item_description": entry.get("item_description", ""),
            "uom": entry.get("uom"),
            "length": flt(entry.get("length", 0)),
            "breadth": flt(entry.get("breadth", 0)),
            "height": flt(entry.get("height", 0)),
            "no_of_items": entry.get("no_of_items", 1),
            "quantity": flt(entry.get("quantity", 0)),
            "remarks": entry.get("remarks", "")
        })
    return prepared


def _update_boq_billed_quantity(mb_doc):
    """Update BOQ item with billed quantity from certified MB."""
    if not mb_doc.boq_reference:
        return

    boq_items = {}
    for entry in mb_doc.measurement_entries:
        if entry.item_code not in boq_items:
            boq_items[entry.item_code] = 0
        boq_items[entry.item_code] += entry.quantity

    for item_code, qty in boq_items.items():
        # Find corresponding BOQ item
        boq_item = frappe.get_all(
            "Custom BOQ",
            filters={"parent": mb_doc.project, "item_code": item_code},
            fields=["name", "billed_quantity"]
        )

        for item in boq_item:
            current_billed = flt(item.billed_quantity)
            frappe.db.set_value("Custom BOQ", item.name, {
                "billed_quantity": current_billed + qty
            })

    logger.info(f"Updated BOQ billed quantities for MB {mb_doc.name}")