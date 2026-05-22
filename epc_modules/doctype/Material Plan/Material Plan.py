# Copyright (c) 2024
import frappe
from frappe import _
from frappe.utils import flt, now
from frappe.model.document import Document


class MaterialPlan(Document):
    def validate(self):
        self.calculate_totals()

    def calculate_totals(self):
        total = sum(flt(item.estimated_cost or 0) for item in self.items)
        self.estimated_total = total

    def on_submit(self):
        if self.status == "Draft":
            self.db_set("status", "Approved")
