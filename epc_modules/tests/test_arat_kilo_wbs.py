"""
Arat Kilo WBS Tests

Tests for Arat Kilo Building Civil Phase-Based WBS structure.
"""

import frappe
from frappe.test_utils import FrappeTestCase


class TestAratKiloWBS(FrappeTestCase):
    def setUp(self):
        frappe.set_user("Administrator")
        if not frappe.db.exists("Project", "ARAT-KILO"):
            proj = frappe.get_doc({
                "doctype": "Project",
                "project_name": "Arat Kilo Building",
                "is_epc_project": 1,
                "project_typology": "Civil",
                "billing_track": "RA-Billing",
                "status": "Active"
            })
            proj.insert()

    def test_create_arat_kilo_wbs(self):
        """Create WBS hierarchy for Arat Kilo building (Civil, Phase-Based)."""
        from epc_modules.utils.arat_kilo_wbs import create_arat_kilo_wbs_structure

        elements = create_arat_kilo_wbs_structure("ARAT-KILO")
        self.assertGreater(len(elements), 5)
        sections = set()
        for e in elements:
            prefix = e["wbs_code"].split("-")[0] if "-" in e["wbs_code"] else e["wbs_code"]
            sections.add(prefix)
        self.assertIn("DEMO", sections)
        self.assertIn("EXCV", sections)
        self.assertIn("CONS-SUB", sections)
        self.assertIn("CONS-SUP", sections)

    def test_arat_kilo_wbs_api(self):
        """Test the API endpoint for WBS creation."""
        from epc_modules.api.wbs_api import create_arat_kilo_wbs

        result = create_arat_kilo_wbs("ARAT-KILO")
        self.assertIn("elements_created", result)
        self.assertGreater(result["elements_created"], 5)

    def tearDown(self):
        frappe.set_user("Administrator")
        frappe.db.delete("WBS Item", {"project": "ARAT-KILO"})