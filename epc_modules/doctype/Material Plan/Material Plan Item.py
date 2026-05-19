import frappe
from frappe import _
from frappe.utils import flt


class MaterialPlanItem(frappe.Model):
    def validate(self):
        if self.required_quantity and self.unit_rate:
            self.estimated_cost = flt(self.required_quantity) * flt(self.unit_rate)


doctype = "Material Plan Item"