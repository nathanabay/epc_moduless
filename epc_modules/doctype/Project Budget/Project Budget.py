import frappe
from frappe.model.document import Document


class ProjectBudget(Document):
    def autoname(self):
        if not self.budget_code:
            self.budget_code = f"PB-{self.project[:4].upper() if self.project else 'PROJ'}-{frappe.generate_hash(length=8).upper()}"

    def validate(self):
        self.calculate_totals()

    def calculate_totals(self):
        self.total_planned_cost = sum(frappe.utils.flt(line.get("planned_cost", 0)) for line in self.get("lines", []))
        self.total_actual_cost = sum(frappe.utils.flt(line.get("actual_cost", 0)) for line in self.get("lines", []))
        self.total_variance = self.total_planned_cost - self.total_actual_cost
        if self.total_planned_cost:
            self.variance_percentage = (self.total_variance / self.total_planned_cost) * 100