# Copyright (c) 2024
import frappe
from frappe import _
from frappe.utils import nowdate, get_datetime
from frappe.model.document import Document


class SiteInstruction(Document):
    def validate(self):
        self.set_instruction_number()

    def set_instruction_number(self):
        if not self.instruction_number and self.project:
            project_code = frappe.db.get_value("Project", self.project, "project_code") or self.project[:4].upper()
            suffix = frappe.utils.get_random_string(4).upper()
            self.instruction_number = f"SI-{project_code}-{suffix}"

    def on_submit(self):
        if self.status == "Draft":
            self.db_set("status", "Issued")

    def on_cancel(self):
        self.db_set("status", "Draft")