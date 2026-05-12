# Copyright (c) EPC Development Team
# License: MIT

import frappe


class CuringRecord(frappe.Document):
    pass


def on_doctype_update():
    frappe.db.add_index("Curing Record", ["name"])
