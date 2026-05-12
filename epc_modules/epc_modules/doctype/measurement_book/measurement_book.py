# Copyright (c) EPC Development Team
# License: MIT

from frappe.model.document import Document
import frappe


class MeasurementBook(Document):
    pass


def on_doctype_update():
    frappe.db.add_index("Measurement Book", ["name"])
