import frappe
from frappe import _


class JobType(frappe.Model):
    def validate(self):
        if self.is_active is None:
            self.is_active = 1
        if not self.sort_order:
            self.sort_order = 0


doctype = "Job Type"
