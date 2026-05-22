# Copyright (c) 2026, EPC Development Team and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import flt


class SiteAttendance(Document):
    def autoname(self):
        project_code = self.project[:4].upper() if self.project else "SA"
        self.attendance_id = f"SA-{project_code}-{frappe.generate_hash(length=8).upper()}"

    def validate(self):
        if not self.recorded_by:
            self.recorded_by = frappe.session.user
        self.calculate_totals()

    def calculate_totals(self):
        if self.entries:
            self.total_labor_count = sum(1 for e in self.entries if e.present)
            self.regular_hours_total = sum(flt(e.regular_hours) for e in self.entries if e.present)
            self.overtime_hours_total = sum(flt(e.overtime_hours) for e in self.entries if e.present)
        else:
            self.total_labor_count = 0
            self.regular_hours_total = 0
            self.overtime_hours_total = 0