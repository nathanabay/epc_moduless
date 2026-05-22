# Copyright (c) 2026, EPC Development Team and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class MachineRepair(Document):
    def autoname(self):
        if self.machine:
            date_str = self.repair_date.replace("-", "") if self.repair_date else frappe.utils.today().replace("-", "")
            self.name = f"MR-{self.machine[:3].upper()}-{date_str}"

    def validate(self):
        if not self.status:
            self.status = "Open"

    def before_submit(self):
        if not self.work_performed:
            frappe.throw(_("Work Performed is required before submission"))

    def on_submit(self):
        self.db_set("status", "Completed")

    def on_update_after_submit(self):
        if self.status == "Completed":
            self.db_set("status", "Verified")

    def verify_repair(self):
        self.status = "Verified"
        self.verified_by = frappe.session.user
        self.verified_on = frappe.utils.now()
        self.db_set({
            "status": "Verified",
            "verified_by": self.verified_by,
            "verified_on": self.verified_on
        })