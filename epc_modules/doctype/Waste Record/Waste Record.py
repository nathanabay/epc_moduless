# Copyright (c) 2026, EPC Development Team and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import nowdate
from frappe.model.document import Document


class WasteRecord(Document):
    def validate(self):
        self.set_record_number()
        self.update_hazardous_flag()

    def set_record_number(self):
        if not self.record_number and self.project:
            project_code = frappe.db.get_value("Project", self.project, "project_code") or self.project[:4].upper()
            suffix = frappe.utils.get_random_string(4).upper()
            self.record_number = f"WR-{project_code}-{suffix}"

    def update_hazardous_flag(self):
        if self.waste_type == "Hazardous":
            self.is_hazardous = 1

    def on_submit(self):
        if self.status == "Draft":
            self.db_set("status", "Generated")

    def on_cancel(self):
        self.db_set("status", "Draft")