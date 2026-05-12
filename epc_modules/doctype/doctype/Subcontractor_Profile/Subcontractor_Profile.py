# Copyright (c) EPC Development Team
# License: MIT

import frappe


class SubcontractorProfile(frappe.Document):
    pass


def on_doctype_update():
    frappe.db.add_index("Subcontractor Profile", ["name"])
