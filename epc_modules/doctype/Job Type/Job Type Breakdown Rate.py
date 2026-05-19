import frappe
from frappe import _
from frappe.utils import flt


class JobTypeBreakdownRate(frappe.Model):
    def validate(self):
        if self.rate and self.rate < 0:
            frappe.throw(_("Rate cannot be negative"))


doctype = "Job Type Breakdown Rate"