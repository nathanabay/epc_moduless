import frappe
from frappe.model.document import Document


class BuildingProgram(Document):
    def validate(self):
        self.calculate_total_area()

    def calculate_total_area(self):
        total = 0
        for space in self.spaces:
            space.total_area_sqm = space.quantity * space.unit_area_sqm
            total += space.total_area_sqm
        self.total_area_sqm = total
