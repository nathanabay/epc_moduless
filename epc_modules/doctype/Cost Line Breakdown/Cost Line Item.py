import frappe
from frappe import _
from frappe.utils import flt


class CostLineItem(frappe.Model):
    def validate(self):
        if self.quantity and self.unit_rate:
            self.estimated_cost = flt(self.quantity) * flt(self.unit_rate)


doctype = "Cost Line Item"