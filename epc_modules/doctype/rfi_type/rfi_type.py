# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class RFIType(Document):
    def validate(self):
        if self.is_active is None:
            self.is_active = 1
        if not self.response_days:
            self.response_days = 7
