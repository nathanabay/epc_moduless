# Copyright (c) 2024
# License: MIT

import frappe
from frappe.model.document import Document
from frappe.utils import today


class HSEIncident(Document):
    def autoname(self):
        if not self.incident_number:
            project_code = self.project[:4].upper() if self.project else "INC"
            self.incident_number = f"INC-{project_code}-{frappe.generate_hash(length=8).upper()}"

    def validate(self):
        if not self.incident_date:
            self.incident_date = today()
        if not self.reported_by:
            self.reported_by = frappe.session.user
        if not self.reported_date:
            self.reported_date = today()

    def before_save(self):
        if self.status == "Closed" and not self.closure_date:
            self.closure_date = today()