# tests/test_ra_bill_template.py
import frappe, unittest

class TestRABillTemplate(unittest.TestCase):
    def setUp(self):
        frappe.set_user("Administrator")
        if not frappe.db.exists("Project", "ARAT-KILO"):
            proj = frappe.get_doc({
                "doctype": "Project",
                "project_name": "Arat Kilo Building",
                "is_epc_project": 1,
                "project_typology": "Civil",
                "billing_track": "RA-Billing",
                "status": "Active",
                "contract_value": 300000000,
                "mobilization_advance_amount": 30000000,
            })
            proj.insert()

    def test_create_ra_bill_template(self):
        """Create RA Bill template from BOQ items."""
        from epc_modules.api.billing_api import create_ra_bill_template

        result = create_ra_bill_template("ARAT-KILO", {
            "billing_period_start": "2024-01-01",
            "billing_period_end": "2024-01-31",
        })
        self.assertIn("ra_bill_number", result)
        self.assertIn("gross_certified_value", result)
        self.assertTrue(result["ra_bill_number"].startswith("RA-"))

    def test_get_ra_bill_schedule(self):
        """Get RA Bill billing schedule from BOQ."""
        from epc_modules.api.billing_api import get_ra_bill_schedule

        schedule = get_ra_bill_schedule("ARAT-KILO")
        self.assertIn("scheduled_bills", schedule)
        self.assertGreater(schedule["total_contract"], 0)

    def tearDown(self):
        frappe.set_user("Administrator")
        if frappe.db.exists("RA Bill", {"project": "ARAT-KILO"}):
            frappe.db.sql("DELETE FROM `tabRA Bill` WHERE project = 'ARAT-KILO'")
        frappe.db.commit()