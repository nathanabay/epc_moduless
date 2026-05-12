# Copyright (c) EPC Development Team
# License: MIT

import frappe


class ConcreteMixDesign(frappe.Document):
    pass


def on_doctype_update():
    frappe.db.add_index("Concrete Mix Design", ["name"])
