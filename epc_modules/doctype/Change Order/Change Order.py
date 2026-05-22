# Copyright (c) 2024
# License: MIT

import frappe
from frappe.model.document import Document
from frappe import _
from frappe.utils import today


class ChangeOrder(Document):
    def validate(self):
        self.validate_dates()
        self.autoname()

    def autoname(self):
        if not self.change_order_number and self.project:
            project_code = frappe.db.get_value("Project", self.project, "project_code") or self.project[:4].upper()
            suffix = frappe.utils.get_random_string(4).upper()
            self.change_order_number = f"CO-{project_code}-{suffix}"

    def validate_dates(self):
        if self.is_approved and not self.approved_by:
            self.approved_by = frappe.session.user
            self.approval_date = today()

    def on_submit(self):
        if self.status == "Draft":
            self.db_set("status", "Submitted")

    def on_cancel(self):
        self.db_set("status", "Draft")