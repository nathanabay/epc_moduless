# Copyright (c) EPC Development Team
# License: MIT

import frappe


class EquipmentMaintenanceSchedule(frappe.Document):
    pass


def on_doctype_update():
    frappe.db.add_index("Equipment Maintenance Schedule", ["name"])
