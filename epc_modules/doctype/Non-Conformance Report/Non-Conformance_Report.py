# Copyright (c) EPC Development Team
# License: MIT

import frappe


class Non-ConformanceReport(frappe.Document):
    pass


def on_doctype_update():
    frappe.db.add_index("Non-Conformance Report", ["name"])
