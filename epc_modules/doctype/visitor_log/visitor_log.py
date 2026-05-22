# Copyright (c) 2026, EPC Development Team and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class VisitorLog(Document):
	def autoname(self):
		project_code = self.project[:4].upper() if self.project else "VIS"
		self.visitor_id = f"VIS-{project_code}-{frappe.generate_hash(length=8).upper()}"

	def validate(self):
		if not self.entry_date:
			self.entry_date = frappe.utils.now()
		if not self.badge_number:
			self.badge_number = f"B-{frappe.utils.now().strftime('%Y%m%d%H%M%S')}"
		if self.status == "Exited" and not self.exit_date:
			self.exit_date = frappe.utils.now()