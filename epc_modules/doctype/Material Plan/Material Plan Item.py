# Copyright (c) 2024
import frappe
from frappe import _
from frappe.utils import flt
from frappe.model.document import Document


class MaterialPlanItem(Document):
    def validate(self):
        if self.required_quantity and self.unit_rate:
            self.estimated_cost = flt(self.required_quantity) * flt(self.unit_rate)