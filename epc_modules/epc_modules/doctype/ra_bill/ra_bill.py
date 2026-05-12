# Copyright (c) EPC Development Team
# License: MIT

from frappe.model.document import Document
import frappe


class RABill(Document):
    pass


def on_doctype_update():
    frappe.db.add_index("RA Bill", ["name"])
