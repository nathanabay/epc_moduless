# Copyright (c) EPC Development Team
# License: MIT

import frappe


class WBSItem(frappe.Document):
    pass


def on_doctype_update():
    frappe.db.add_index("WBS Item", ["name"])
