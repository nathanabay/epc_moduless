import frappe
from frappe import _
from frappe.model.document import Document


class DesignPhase(Document):
    def validate(self):
        self.validate_dates()

    def validate_dates(self):
        if self.planned_start and self.planned_end:
            if self.planned_end < self.planned_start:
                frappe.throw(_("Planned End cannot be before Planned Start"))

    def on_submit(self):
        if self.gate_status == "Pending":
            frappe.throw(_("Quality gate must be passed before submitting this phase"))
