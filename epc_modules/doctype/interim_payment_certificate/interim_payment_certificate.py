# Copyright (c) 2026
# License: MIT

import frappe
from frappe import _
from frappe.utils import flt, today
from frappe.model.document import Document


class InterimPaymentCertificate(Document):
    def autoname(self):
        project_code = self.project[:4].upper() if self.project else "IPC"
        self.name = f"IPC-{project_code}-{frappe.generate_hash(length=8).upper()}"

    def validate(self):
        if not self.certification_date:
            self.certification_date = today()
        self.calculate_totals()

    def calculate_totals(self):
        self.gross_certified_value = sum(flt(line.get("this_period_certified", 0)) for line in self.get("lines", []))
        self.retention_amount = self.gross_certified_value * (flt(self.retention_percentage) / 100)
        self.net_certified_value = self.gross_certified_value - self.retention_amount
        self.vat_amount = self.net_certified_value * (flt(self.vat_rate) / 100)
        self.total_invoice_value = self.net_certified_value + self.vat_amount