# Copyright (c) EPC Development Team
# License: MIT

import frappe


class DailyProgressReport(frappe.Document):
    pass


def on_doctype_update():
    frappe.db.add_index("Daily Progress Report", ["name"])
