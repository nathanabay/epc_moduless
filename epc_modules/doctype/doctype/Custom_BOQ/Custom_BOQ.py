# Copyright (c) EPC Development Team
# License: MIT

import frappe


class CustomBOQ(frappe.Document):
    pass


def on_doctype_update():
    frappe.db.add_index("Custom BOQ", ["name"])
