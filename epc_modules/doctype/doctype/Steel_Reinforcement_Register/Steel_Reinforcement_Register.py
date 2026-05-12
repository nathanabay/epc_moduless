# Copyright (c) EPC Development Team
# License: MIT

import frappe


class SteelReinforcementRegister(frappe.Document):
    pass


def on_doctype_update():
    frappe.db.add_index("Steel Reinforcement Register", ["name"])
