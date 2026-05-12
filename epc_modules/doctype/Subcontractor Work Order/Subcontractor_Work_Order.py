# Copyright (c) EPC Development Team
# License: MIT

import frappe


class SubcontractorWorkOrder(frappe.Document):
    pass


def on_doctype_update():
    frappe.db.add_index("Subcontractor Work Order", ["name"])
