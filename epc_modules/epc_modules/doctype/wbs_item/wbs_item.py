# Copyright (c) EPC Development Team
# License: MIT

from frappe.model.document import Document
import frappe


class WBSItem(Document):
    pass


def on_doctype_update():
    frappe.db.add_index("WBS Item", ["name"])
