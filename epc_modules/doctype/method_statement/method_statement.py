# Copyright (c) 2026
# License: MIT

import frappe
from frappe import _
from frappe.utils import flt, today
from frappe.model.document import Document


class MethodStatement(Document):
    def autoname(self):
        project_code = self.project[:4].upper() if self.project else "MS"
        self.ms_number = f"MS-{project_code}-{frappe.generate_hash(length=8).upper()}"

    def validate(self):
        if not self.prepared_date:
            self.prepared_date = today()
        if self.status == "Approved" and not self.approved_by:
            self.approved_by = frappe.session.user
            self.approval_date = today()