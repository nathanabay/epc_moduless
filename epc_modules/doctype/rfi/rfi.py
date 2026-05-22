# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import nowdate, add_days, get_datetime
from frappe.model.document import Document


class RFI(Document):
    def validate(self):
        self.set_rfi_number()
        self.set_due_date()
        self.validate_dates()
        self.update_status()

    def set_rfi_number(self):
        if not self.rfi_number and self.project:
            project_code = frappe.db.get_value("Project", self.project, "project_code") or self.project[:4].upper()
            suffix = frappe.utils.get_random_string(4).upper()
            self.rfi_number = f"RFI-{project_code}-{suffix}"

    def set_due_date(self):
        if not self.due_date and self.rfi_type and self.raised_date:
            response_days = frappe.db.get_value("RFI Type", self.rfi_type, "response_days") or 7
            self.due_date = add_days(self.raised_date, response_days)

    def validate_dates(self):
        if self.due_date and self.raised_date:
            if get_datetime(self.due_date) < get_datetime(self.raised_date):
                frappe.throw(__("Due Date cannot be before Raised Date"))

    def update_status(self):
        if self.response and self.status == "Open":
            self.status = "Pending Review"
        if self.workflow_state == "Rejected":
            self.status = "Rejected"

    def on_submit(self):
        if self.status == "Draft":
            self.db_set("status", "Open")

    def on_cancel(self):
        self.db_set("status", "Draft")

    def get_context(self):
        return {
            "rfi_number": self.rfi_number,
            "project": self.project,
            "subject": self.subject,
            "question": self.question,
            "response": self.response,
            "raised_by": self.raised_by,
            "raised_date": self.raised_date,
            "due_date": self.due_date,
            "responded_by": self.responded_by,
            "response_date": self.response_date,
            "status": self.status,
        }
