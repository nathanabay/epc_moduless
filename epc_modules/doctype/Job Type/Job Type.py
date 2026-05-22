# Copyright (c) 2024
import frappe
from frappe import _
from frappe.model.document import Document


class JobType(Document):
    def validate(self):
        if self.is_active is None:
            self.is_active = 1
        if not self.sort_order:
            self.sort_order = 0
