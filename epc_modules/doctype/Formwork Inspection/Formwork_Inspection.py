# Copyright (c) EPC Development Team
# License: MIT

import frappe


class FormworkInspection(frappe.Document):
    pass


def on_doctype_update():
    frappe.db.add_index("Formwork Inspection", ["name"])
