# Copyright (c) 2024
# License: MIT

import frappe
from frappe.model.document import Document
from frappe.utils import today


class SafetyInspection(Document):
    def autoname(self):
        if not self.inspection_number:
            project_code = self.project[:4].upper() if self.project else "SFT"
            self.inspection_number = f"SFT-{project_code}-{frappe.generate_hash(length=8).upper()}"

    def validate(self):
        if not self.inspection_date:
            self.inspection_date = today()
        if not self.inspector:
            self.inspector = frappe.session.user
        self.calculate_compliance()

    def calculate_compliance(self):
        if self.checklist_items:
            self.total_checklist_items = len(self.checklist_items)
            self.items_complied = sum(1 for item in self.checklist_items if item.status == "Complied")
            if self.total_checklist_items > 0:
                self.compliance_percentage = round((self.items_complied / self.total_checklist_items) * 100, 2)
            else:
                self.compliance_percentage = 0
        else:
            self.total_checklist_items = 0
            self.items_complied = 0
            self.compliance_percentage = 0