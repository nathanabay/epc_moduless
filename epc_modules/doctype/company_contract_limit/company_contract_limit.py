# Copyright (c) 2026, EPC Development Team and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class CompanyContractLimit(Document):
    def autoname(self):
        self.name = f"CCL-{self.company[:3].upper()}-{self.contract_type[:3].upper() if self.contract_type else 'GEN'}"

    def validate(self):
        self.validate_limits()
        self.check_approval_route()

    def validate_limits(self):
        if self.min_value and self.max_value:
            if self.min_value >= self.max_value:
                frappe.throw(_("Minimum Value must be less than Maximum Value"))

    def check_approval_route(self):
        route = frappe.get_all(
            "Contract Approval Route",
            filters={
                "contract_type": self.contract_type,
                "is_active": 1,
                "max_value": [">=", self.contract_value]
            },
            order_by="max_value asc"
        )
        if not route:
            frappe.throw(_(f"No active approval route found for contract type: {self.contract_type}"))

    def get_approval_route(self):
        routes = frappe.get_all(
            "Contract Approval Route",
            filters={
                "contract_type": self.contract_type,
                "is_active": 1
            },
            order_by="max_value asc"
        )
        for route in routes:
            if self.contract_value <= (route.max_value or 0):
                return frappe.get_doc("Contract Approval Route", route.name)
        return None

    def get_pending_approvers(self):
        route = self.get_approval_route()
        if not route:
            return []

        approved_levels = [h.approval_level for h in (self.approval_history or [])]
        pending = []
        for level in route.approval_levels:
            if level.approval_level not in approved_levels:
                pending.append(level)
        return pending