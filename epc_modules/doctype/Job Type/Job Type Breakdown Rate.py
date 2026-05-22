# Copyright (c) 2024
import frappe
from frappe import _
from frappe.utils import flt
from frappe.model.document import Document


class JobTypeBreakdownRate(Document):
    def validate(self):
        if self.rate and self.rate < 0:
            frappe.throw(_("Rate cannot be negative"))