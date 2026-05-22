# Copyright (c) 2026, EPC Development Team and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class SafetyObservation(Document):
	def autoname(self):
		project_code = self.project[:4].upper() if self.project else "SO"
		self.observation_number = f"SO-{project_code}-{frappe.generate_hash(length=8).upper()}"

	def validate(self):
		if not self.observation_date:
			self.observation_date = frappe.utils.today()
		if not self.observed_by:
			self.observed_by = frappe.session.user
		if self.status == "Closed" and not self.actual_close_date:
			self.actual_close_date = frappe.utils.today()