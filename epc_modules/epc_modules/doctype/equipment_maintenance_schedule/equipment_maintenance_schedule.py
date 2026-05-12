# Copyright (c) EPC Development Team
# License: MIT

from frappe.model.document import Document
import frappe


class EquipmentMaintenanceSchedule(Document):
    pass


def on_doctype_update():
    frappe.db.add_index("Equipment Maintenance Schedule", ["name"])
