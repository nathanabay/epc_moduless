# Copyright (c) 2024
import frappe
from frappe import _
from frappe.utils import flt
from frappe.model.document import Document


class CostLineItem(Document):
    def validate(self):
        if self.quantity and self.unit_rate:
            self.estimated_cost = flt(self.quantity) * flt(self.unit_rate)