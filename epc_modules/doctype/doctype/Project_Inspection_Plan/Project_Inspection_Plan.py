# Copyright (c) EPC Development Team
# License: MIT

import frappe


class ProjectInspectionPlan(frappe.Document):
    pass


def on_doctype_update():
    frappe.db.add_index("Project Inspection Plan", ["name"])
