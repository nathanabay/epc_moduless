# Copyright (c) 2024
import frappe
from frappe import _
from frappe.utils import nowdate, get_datetime, date_diff, flt
from frappe.model.document import Document


class WorkPackage(Document):
    def validate(self):
        self.set_package_number()
        self.validate_dates()
        self.update_progress()

    def set_package_number(self):
        if not self.package_number and self.project:
            project_code = frappe.db.get_value("Project", self.project, "project_code") or self.project[:4].upper()
            suffix = frappe.utils.get_random_string(4).upper()
            self.package_number = f"WP-{project_code}-{suffix}"

    def validate_dates(self):
        if self.planned_end and self.planned_start:
            if get_datetime(self.planned_end) < get_datetime(self.planned_start):
                frappe.throw(_("Planned End cannot be before Planned Start"))
        if self.actual_end and self.actual_start:
            if get_datetime(self.actual_end) < get_datetime(self.actual_start):
                frappe.throw(_("Actual End cannot be before Actual Start"))

    def update_progress(self):
        if self.tasks:
            total = len(self.tasks)
            completed = sum(1 for t in self.tasks if t.status == "Completed")
            self.progress = flt((completed / total) * 100) if total > 0 else 0

    def on_submit(self):
        if self.status == "Draft":
            self.db_set("status", "Planned")
            if not self.actual_start:
                self.db_set("actual_start", nowdate())

    def on_cancel(self):
        self.db_set("status", "Draft")