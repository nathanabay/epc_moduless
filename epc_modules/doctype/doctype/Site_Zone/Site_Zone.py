# Copyright (c) EPC Development Team
# License: MIT

import frappe


class SiteZone(frappe.Document):
    pass


def on_doctype_update():
    frappe.db.add_index("Site Zone", ["name"])
