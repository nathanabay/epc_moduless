# Copyright (c) EPC Development Team
# License: MIT

import frappe


class EquipmentRegister(frappe.Document):
    pass


def on_doctype_update():
    frappe.db.add_index("Equipment Register", ["name"])
