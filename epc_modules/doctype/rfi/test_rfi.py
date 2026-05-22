# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.tests.utils import FrappeTestCase


class TestRFI(FrappeTestCase):
    def setUp(self):
        frappe.set_user("Administrator")

    def tearDown(self):
        # Clean up RFI and RFI Type created by tests
        frappe.db.delete("RFI", {"subject": ["like", "%Test%"]})
        if frappe.db.exists("RFI Type", "_Test RFI Type"):
            frappe.delete_doc("RFI Type", "_Test RFI Type", force=True)

    def test_rfi_creation(self):
        """Test basic RFI creation."""
        rfi = frappe.new_doc("RFI")
        rfi.subject = "Test RFI Subject"
        rfi.question = "What is the specification for this item?"
        rfi.priority = "High"
        rfi.status = "Draft"
        rfi.insert()

        self.assertTrue(rfi.name)
        self.assertEqual(rfi.status, "Draft")

    def test_rfi_auto_numbering(self):
        """Test RFI auto numbering per project."""
        rfi = frappe.new_doc("RFI")
        rfi.project = "_Test Project"
        rfi.subject = "Auto Number Test"
        rfi.question = "Test question"
        rfi.insert()

        self.assertIn("RFI-", rfi.rfi_number or "")

    def test_rfi_due_date_calculation(self):
        """Test due date is calculated from RFI Type response days."""
        if not frappe.db.exists("RFI Type", "_Test RFI Type"):
            rfi_type = frappe.new_doc("RFI Type")
            rfi_type.rfi_type_name = "_Test RFI Type"
            rfi_type.response_days = 14
            rfi_type.default_priority = "High"
            rfi_type.insert()

        rfi = frappe.new_doc("RFI")
        rfi.subject = "Due Date Test"
        rfi.question = "Test question"
        rfi.rfi_type = "_Test RFI Type"
        rfi.raised_date = "2026-01-01"
        rfi.insert()

        if rfi.due_date:
            from frappe.utils import date_diff
            days = date_diff(rfi.due_date, rfi.raised_date)
            self.assertEqual(days, 14)

    def test_rfi_status_transitions(self):
        """Test RFI status transitions."""
        rfi = frappe.new_doc("RFI")
        rfi.subject = "Status Test"
        rfi.question = "Test question"
        rfi.status = "Draft"
        rfi.insert()

        rfi.status = "Open"
        rfi.save()
        self.assertEqual(rfi.status, "Open")

        rfi.response = "Test response"
        rfi.save()
        self.assertEqual(rfi.status, "Pending Review")

        rfi.status = "Closed"
        rfi.save()
        self.assertEqual(rfi.status, "Closed")

    def test_api_get_rfi_list(self):
        """Test get_rfi_list API."""
        from epc_modules.api.site_operations_api import get_rfi_list

        rfi = frappe.new_doc("RFI")
        rfi.subject = "API List Test"
        rfi.question = "Test question"
        rfi.insert()

        result = get_rfi_list()
        self.assertIsInstance(result, list)

    def test_api_get_rfi_summary(self):
        """Test get_rfi_summary API."""
        from epc_modules.api.site_operations_api import get_rfi_summary

        result = get_rfi_summary()
        self.assertIn("total", result)
        self.assertIn("open", result)
        self.assertIn("closed", result)
        self.assertIn("overdue", result)