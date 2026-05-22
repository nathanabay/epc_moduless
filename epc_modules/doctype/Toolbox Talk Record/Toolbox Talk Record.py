# Copyright (c) 2024
# License: MIT

import frappe
from frappe.model.document import Document
from frappe.utils import today


class ToolboxTalkRecord(Document):
    def autoname(self):
        if not self.talk_id:
            project_code = self.project[:4].upper() if self.project else "TT"
            self.talk_id = f"TT-{project_code}-{frappe.generate_hash(length=8).upper()}"

    def validate(self):
        if not self.talk_date:
            self.talk_date = today()
        if not self.talk_presenter:
            self.talk_presenter = frappe.session.user
        self.calculate_attendees()

    def calculate_attendees(self):
        if self.attendees:
            self.total_attendees = len(self.attendees)
        else:
            self.total_attendees = 0