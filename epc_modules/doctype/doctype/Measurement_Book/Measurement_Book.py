# Copyright (c) EPC Development Team
# License: MIT

import frappe


class MeasurementBook(frappe.Document):
    pass


def on_doctype_update():
    frappe.db.add_index("Measurement Book", ["name"])
