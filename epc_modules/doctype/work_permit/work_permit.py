# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import get_datetime
from frappe.model.document import Document


class WorkPermit(Document):
	def autoname(self):
		project_code = self.project[:4].upper() if self.project else "WP"
		self.permit_number = f"WP-{project_code}-{frappe.generate_hash(length=8).upper()}"

	def validate(self):
		if not self.issued_by:
			self.issued_by = frappe.session.user
		if self.start_date and self.end_date:
			start = get_datetime(self.start_date)
			end = get_datetime(self.end_date)
			if end <= start:
				frappe.throw(_("End Date must be after Start Date"))
		if self.permit_type:
			pt = frappe.get_doc("Permit Type", self.permit_type)
			if pt.requires_jha and not self.jha_conducted:
				frappe.throw(_("JHA must be conducted for this permit type"))
			if pt.requires_ppe_check and not self.ppe_check_completed:
				frappe.throw(_("PPE check is mandatory for this permit type"))