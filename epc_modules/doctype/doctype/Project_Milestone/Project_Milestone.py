# Copyright (c) EPC Development Team
# License: MIT

import frappe


class ProjectMilestone(frappe.Document):
    pass


def on_doctype_update():
    frappe.db.add_index("Project Milestone", ["name"])
