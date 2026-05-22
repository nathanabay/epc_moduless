# Copyright (c) 2026, EPC Development Team and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class ContractApprovalRoute(Document):
    def validate(self):
        self.validate_approval_levels()

    def validate_approval_levels(self):
        if not self.approval_levels:
            frappe.throw(_("At least one approval level is required"))

        for i, level in enumerate(self.approval_levels, 1):
            if level.approval_level != i:
                frappe.throw(_(f"Approval levels must be sequential starting from 1. Level {i} is missing or incorrect."))

    def get_current_approver(self):
        """Get the current pending approver based on approval history"""
        if not self.approval_levels:
            return None

        for level in self.approval_levels:
            found = False
            for history in self.approval_history or []:
                if history.approval_level == level.approval_level:
                    found = True
                    break
            if not found:
                return level

        return None

    def is_fully_approved(self):
        """Check if all approval levels are completed"""
        if not self.approval_levels:
            return False
        return len(self.approval_history or []) >= len(self.approval_levels)