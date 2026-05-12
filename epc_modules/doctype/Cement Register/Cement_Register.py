# Copyright (c) EPC Development Team
# License: MIT

import frappe


class CementRegister(frappe.Document):
    pass


def on_doctype_update():
    frappe.db.add_index("Cement Register", ["name"])
