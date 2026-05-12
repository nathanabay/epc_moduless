# Copyright (c) EPC Development Team
# License: MIT

import frappe


class ClaimRegister(frappe.Document):
    pass


def on_doctype_update():
    frappe.db.add_index("Claim Register", ["name"])
