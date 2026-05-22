# Copyright (c) 2026, EPC Development Team and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class Transmittal(Document):
    def validate(self):
        self.set_transmittal_number()
        self.validate_documents()

    def set_transmittal_number(self):
        if not self.transmittal_number and self.project:
            project_code = frappe.db.get_value("Project", self.project, "project_code") or self.project[:4].upper()
            suffix = frappe.utils.get_random_string(4).upper()
            self.transmittal_number = f"TR-{project_code}-{suffix}"

    def validate_documents(self):
        if not self.documents:
            frappe.throw(_("At least one document is required"))

    def on_submit(self):
        if self.status == "Draft":
            self.db_set("status", "Issued")

    def on_cancel(self):
        self.db_set("status", "Draft")