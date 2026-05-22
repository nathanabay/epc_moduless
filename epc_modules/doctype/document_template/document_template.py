# Copyright (c) 2026, EPC Development Team and contributors
# For license information, please see license.txt

import frappe
import re
from frappe.model.document import Document


class DocumentTemplate(Document):
    def autoname(self):
        self.name = self.template_name

    def validate(self):
        if self.content:
            placeholders = re.findall(r'\{(\w+)\}', self.content)
            self.placeholders = ", ".join(sorted(set(placeholders))) if placeholders else ""

    def render_template(self, context):
        content = self.content or ""
        for key, value in context.items():
            content = content.replace("{" + key + "}", str(value))
        return content