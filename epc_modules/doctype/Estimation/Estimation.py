# Copyright (c) 2024
import frappe
from frappe import _
from frappe.utils import flt, today
from frappe.model.document import Document


class Estimation(Document):
    def validate(self):
        self.calculate_totals()
        self.validate_items()

    def calculate_totals(self):
        for item in self.items:
            item.amount = flt(item.qty) * flt(item.rate)

        self.base_total = sum(flt(item.amount) for item in self.items)
        self.markup_amount = self.base_total * (flt(self.markup_percentage) / 100)
        self.total_before_vat = self.base_total + self.markup_amount
        self.vat_amount = self.total_before_vat * (flt(self.vat_percentage) / 100)
        self.grand_total = self.total_before_vat + self.vat_amount

    def validate_items(self):
        if not self.items:
            frappe.throw(_("At least one item is required"))

    def autoname(self):
        if not self.estimate_number and self.project:
            project_code = frappe.db.get_value("Project", self.project, "project_code") or self.project[:4].upper()
            suffix = frappe.utils.get_random_string(4).upper()
            self.estimate_number = f"EST-{project_code}-{suffix}"

    def on_submit(self):
        if self.status == "Draft":
            self.db_set("status", "Submitted")

    def on_cancel(self):
        self.db_set("status", "Draft")
        if self.converted_to_boq:
            frappe.throw(_("Cannot cancel - Estimation already converted to BOQ"))

    def convert_to_boq(self):
        """Convert approved estimation to Custom BOQ."""
        if not frappe.has_permission("Estimation", "write", self.name, throw=True):
            return
        if self.converted_to_boq:
            frappe.throw(_("Estimation already converted to BOQ"))
        if self.status not in ["Approved", "Submitted"]:
            frappe.throw(_("Only Approved or Submitted estimations can be converted"))

        boq_doc = frappe.get_doc({
            "doctype": "Custom BOQ",
            "project": self.project
        })

        for item in self.items:
            boq_doc.append("items", {
                "item_code": item.item_code,
                "description": item.description or item.item_name,
                "qty": item.qty,
                "uom": item.uom,
                "rate": item.rate,
                "total_value": item.amount
            })

        boq_doc.insert()
        self.converted_to_boq = 1
        self.boq_reference = boq_doc.name
        self.status = "Converted"
        self.save()
        return boq_doc.name