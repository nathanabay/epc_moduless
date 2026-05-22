# Copyright (c) 2024
import frappe
from frappe import _
from frappe.utils import flt
from frappe.model.document import Document


class Budget(Document):
    def validate(self):
        self.calculate_totals()
        self.autoname()

    def calculate_totals(self):
        for line in self.lines:
            line.variance = flt(line.planned_amount) - flt(line.actual_amount)

        self.total_planned_cost = sum(flt(line.planned_amount) for line in self.lines)
        self.total_actual_cost = sum(flt(line.actual_amount) for line in self.lines)
        self.total_variance = self.total_planned_cost - self.total_actual_cost
        if self.total_planned_cost > 0:
            self.variance_percentage = round((self.total_variance / self.total_planned_cost) * 100, 2)
        else:
            self.variance_percentage = 0

    def autoname(self):
        if not self.budget_code and self.project:
            project_code = frappe.db.get_value("Project", self.project, "project_code") or self.project[:4].upper()
            suffix = frappe.utils.get_random_string(4).upper()
            self.budget_code = f"BUD-{project_code}-{suffix}"

    def on_submit(self):
        if self.status == "Draft":
            self.db_set("status", "Approved")

    def on_cancel(self):
        self.db_set("status", "Draft")

    def sync_actual_costs(self):
        """Sync actual costs from Purchase Orders against budget lines."""
        if not frappe.has_permission("Budget", "write", self.name):
            frappe.throw(_("No permission to sync actual costs for this Budget"))
        cost_codes = [line.cost_code for line in self.lines]
        if not cost_codes:
            return
        actuals = frappe.db.sql("""
            SELECT poi.cost_code, SUM(poi.amount) as total
            FROM `tabPurchase Order Item` poi
            JOIN `tabPurchase Order` po ON po.name = poi.parent
            WHERE po.project = %s AND poi.cost_code IN %s AND po.docstatus = 1
            GROUP BY poi.cost_code
        """, (self.project, tuple(cost_codes)), as_dict=1)
        actuals_map = {r.cost_code: r.total for r in actuals}
        for line in self.lines:
            line.actual_amount = actuals_map.get(line.cost_code, 0) or 0
        self.calculate_totals()
        self.db_set("total_actual_cost", self.total_actual_cost)
        self.db_set("total_variance", self.total_variance)
        if self.total_planned_cost > 0:
            self.db_set("variance_percentage", round((self.total_variance / self.total_planned_cost) * 100, 2))