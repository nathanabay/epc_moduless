# Copyright (c) 2024
import frappe
from frappe import _
from frappe.utils import nowdate, flt
from frappe.model.document import Document


class ItemRequest(Document):
    def validate(self):
        self.set_item_request_number()
        self.validate_items()

    def set_item_request_number(self):
        if not self.item_request_number and self.project:
            project_code = frappe.db.get_value("Project", self.project, "project_code") or self.project[:4].upper()
            suffix = frappe.utils.get_random_string(4).upper()
            self.item_request_number = f"IR-{project_code}-{suffix}"

    def validate_items(self):
        if not self.items:
            frappe.throw(_("At least one item is required"))
        total = sum(flt(item.qty) for item in self.items)
        if total <= 0:
            frappe.throw(_("Item quantities must be greater than zero"))

    def on_submit(self):
        if self.status == "Draft":
            self.db_set("status", "Pending")

    def on_cancel(self):
        self.db_set("status", "Draft")