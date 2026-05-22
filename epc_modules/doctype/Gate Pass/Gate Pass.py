# Copyright (c) 2026, EPC Development Team and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import nowdate, now_datetime, get_datetime
from frappe.model.document import Document


class GatePass(Document):
    def validate(self):
        self.set_gate_pass_number()
        self.validate_vehicle_details()
        self.update_status()

    def set_gate_pass_number(self):
        if not self.gate_pass_number and self.project:
            project_code = frappe.db.get_value("Project", self.project, "project_code") or self.project[:4].upper()
            gp_type = self.gate_pass_type or "IN"
            suffix = frappe.utils.get_random_string(4).upper()
            self.gate_pass_number = f"GP-{gp_type[:2].upper()}-{project_code}-{suffix}"

    def validate_vehicle_details(self):
        if self.gate_pass_type == "Outward" and not self.vehicle_number:
            frappe.throw(_("Vehicle Number is required for Outward Gate Pass"))

    def update_status(self):
        if self.gate_in_date and self.status == "In Transit":
            self.status = "Received"

    def on_submit(self):
        if self.status == "Draft":
            self.db_set("status", "Open")

    def on_cancel(self):
        self.db_set("status", "Draft")