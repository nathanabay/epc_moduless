# Copyright (c) EPC Development Team
# License: MIT

import frappe


class RiskRegister(frappe.Document):
    pass


def on_doctype_update():
    frappe.db.add_index("Risk Register", ["name"])
