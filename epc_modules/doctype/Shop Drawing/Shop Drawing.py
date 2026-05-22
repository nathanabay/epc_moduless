# Copyright (c) 2026, EPC Development Team and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import nowdate, now_datetime, get_datetime
from frappe.model.document import Document


class ShopDrawing(Document):
    def validate(self):
        self.set_drawing_number()

    def set_drawing_number(self):
        if not self.drawing_number and self.project:
            project_code = frappe.db.get_value("Project", self.project, "project_code") or self.project[:4].upper()
            suffix = frappe.utils.get_random_string(4).upper()
            self.drawing_number = f"SD-{project_code}-{suffix}"

    def on_submit(self):
        if self.status == "Draft":
            self.db_set("status", "Submitted")

    def on_cancel(self):
        self.db_set("status", "Draft")