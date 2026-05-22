# Copyright (c) 2024
import frappe
from frappe import _
from frappe.utils import flt, now
from frappe.model.document import Document


class CostLineBreakdown(Document):
    def validate(self):
        self.calculate_totals()

    def calculate_totals(self):
        total_estimated = sum(flt(item.estimated_cost or 0) for item in self.items)
        total_actual = sum(flt(item.actual_cost or 0) for item in self.items)
        self.total_estimated_cost = total_estimated
        self.total_actual_cost = total_actual
        self.variance = flt(self.total_actual_cost) - flt(self.total_estimated_cost)