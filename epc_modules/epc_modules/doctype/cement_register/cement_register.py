# Copyright (c) EPC Development Team
# License: MIT

from frappe.model.document import Document
import frappe


class CementRegister(Document):
    pass


def on_doctype_update():
    frappe.db.add_index("Cement Register", ["name"])
