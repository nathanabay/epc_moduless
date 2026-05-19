"""
Tests for Financial Report Wizard

Unit tests for the Financial Report Wizard doctype and reports API.
"""

import frappe
import unittest
from frappe.utils import today, add_days, now_datetime
from frappe.tests.utils import FrappeTestCase


class TestFinancialReportWizard(FrappeTestCase):
    """Test cases for Financial Report Wizard."""

    def setUp(self):
        """Set up test data."""
        # Create a test project if it doesn't exist
        if not frappe.db.exists("Project", "_Test EPC Project"):
            self.test_project = frappe.get_doc({
                "doctype": "Project",
                "project_name": "_Test EPC Project",
                "status": "Active",
                "is_epc_project": 1,
                "project_typology": "Electromechanical"
            }).insert()
        else:
            self.test_project = frappe.get_doc("Project", "_Test EPC Project")

    def tearDown(self):
        """Clean up test data."""
        # Clean up test wizard if it exists
        frappe.db.delete("Financial Report Wizard", {"wizard_id": ["like", "FRW-TEST-%"]})

    def test_wizard_creation(self):
        """Test basic wizard document creation."""
        wizard = frappe.get_doc({
            "doctype": "Financial Report Wizard",
            "report_name": "Test Cash Flow Report",
            "report_type": "Cash Flow",
            "project": self.test_project.name,
            "from_date": add_days(today(), -30),
            "to_date": today(),
            "group_by": "WBS",
            "output_format": "HTML"
        })
        wizard.insert()

        # Verify auto-generated wizard_id
        self.assertIsNotNone(wizard.wizard_id)
        self.assertTrue(wizard.wizard_id.startswith("FRW-"))

        # Verify default values
        self.assertEqual(wizard.status, "Draft")
        self.assertEqual(wizard.output_format, "HTML")

        # Clean up
        wizard.delete()

    def test_wizard_autoname_generation(self):
        """Test that wizard_id is auto-generated correctly."""
        wizard = frappe.get_doc({
            "doctype": "Financial Report Wizard",
            "report_name": "Test Report",
            "report_type": "Billing Summary"
        })
        wizard.insert()

        # Check format FRW-YYYYMMDD-XXX
        self.assertRegex(wizard.wizard_id, r"FRW-\d{8}-\d{3}")

        # Clean up
        wizard.delete()

    def test_date_validation(self):
        """Test that from_date < to_date validation works."""
        wizard = frappe.get_doc({
            "doctype": "Financial Report Wizard",
            "report_name": "Test Report",
            "report_type": "Cash Flow",
            "from_date": today(),
            "to_date": add_days(today(), -30)  # to_date before from_date
        })

        # This should throw validation error
        with self.assertRaises(frappe.ValidationError):
            wizard.insert()

    def test_wizard_generates_custom_report(self):
        """Test that wizard can generate various report types."""
        report_types = ["Cash Flow", "Cost Breakdown", "Retention Summary", "Billing Summary"]

        for report_type in report_types:
            wizard = frappe.get_doc({
                "doctype": "Financial Report Wizard",
                "report_name": f"Test {report_type}",
                "report_type": report_type,
                "project": self.test_project.name
            })
            wizard.insert()

            # Trigger report generation
            result = wizard.generate_report()

            # Verify result structure
            self.assertIsNotNone(result)
            self.assertIn("report_type", result)
            self.assertEqual(result["report_type"], report_type)

            # Verify wizard status updated
            wizard.reload()
            self.assertIn(wizard.status, ["Generated", "Failed"])

            # Clean up
            wizard.delete()

    def test_cash_flow_report(self):
        """Test Cash Flow report generation."""
        from epc_modules.api.reports_api import get_cash_flow_report

        # Get report with test project filter
        result = get_cash_flow_report(
            project=self.test_project.name,
            from_date=add_days(today(), -365),
            to_date=today()
        )

        # Verify result structure
        self.assertEqual(result["report_type"], "Cash Flow")
        self.assertIn("summary", result)
        self.assertIn("monthly_summary", result)
        self.assertIn("details", result)

        # Verify summary keys
        summary_keys = ["total_ra_bills", "total_gross_value", "total_vat", "total_retention", "total_invoice_value"]
        for key in summary_keys:
            self.assertIn(key, result["summary"])

    def test_cost_breakdown_report(self):
        """Test Cost Breakdown report generation."""
        from epc_modules.api.reports_api import get_cost_breakdown_report

        result = get_cost_breakdown_report(
            project=self.test_project.name,
            group_by="WBS"
        )

        # Verify structure
        self.assertEqual(result["report_type"], "Cost Breakdown")
        self.assertIn("breakdown", result)
        self.assertIn("summary", result)
        self.assertIn("total_boq_value", result["summary"])

    def test_retention_summary_report(self):
        """Test Retention Summary report generation."""
        from epc_modules.api.reports_api import get_retention_summary_report

        result = get_retention_summary_report(project=self.test_project.name)

        # Verify structure
        self.assertEqual(result["report_type"], "Retention Summary")
        self.assertIn("by_project", result)
        self.assertIn("total_retention_held", result["summary"])

    def test_budget_variance_report(self):
        """Test Budget vs Actual variance report generation."""
        from epc_modules.api.reports_api import get_budget_variance

        result = get_budget_variance(project=self.test_project.name)

        # Verify structure
        self.assertEqual(result["report_type"], "Budget vs Actual")
        self.assertIn("variance", result)
        self.assertIn("summary", result)

        # Verify summary has required keys
        self.assertIn("total_planned_value", result["summary"])
        self.assertIn("total_actual_value", result["summary"])
        self.assertIn("total_variance", result["summary"])

    def test_billing_summary_report(self):
        """Test Billing Summary report generation."""
        from epc_modules.api.reports_api import get_billing_summary_report

        result = get_billing_summary_report(project=self.test_project.name)

        # Verify structure
        self.assertEqual(result["report_type"], "Billing Summary")
        self.assertIn("by_project", result)
        self.assertIn("details", result)

    def test_change_order_summary_report(self):
        """Test Change Order Summary report generation."""
        from epc_modules.api.reports_api import get_change_order_summary

        result = get_change_order_summary(project=self.test_project.name)

        # Verify structure
        self.assertEqual(result["report_type"], "Change Order Summary")
        self.assertIn("by_type", result)
        self.assertIn("by_status", result)
        self.assertIn("summary", result)

    def test_generate_financial_report_api(self):
        """Test the main generate_financial_report API function."""
        from epc_modules.api.reports_api import generate_financial_report

        wizard = frappe.get_doc({
            "doctype": "Financial Report Wizard",
            "report_name": "API Test Report",
            "report_type": "Cost Breakdown",
            "project": self.test_project.name
        }).insert()

        data = {
            "wizard_name": wizard.name,
            "report_type": "Cost Breakdown",
            "project": self.test_project.name,
            "group_by": "WBS",
            "output_format": "HTML"
        }

        result = generate_financial_report(data)

        # Verify success
        self.assertTrue(result.get("success"))

        # Verify wizard status updated
        wizard.reload()
        self.assertEqual(wizard.status, "Generated")

        # Clean up
        wizard.delete()

    def test_report_preview_function(self):
        """Test the get_report_preview function."""
        from epc_modules.api.reports_api import get_report_preview

        # Test preview for each report type
        report_types = ["Cash Flow", "Cost Breakdown", "Billing Summary"]

        for report_type in report_types:
            result = get_report_preview(report_type, project=self.test_project.name)

            # Preview should return report structure
            self.assertIn("report_type", result)
            self.assertEqual(result["report_type"], report_type)

    def test_wizard_with_all_output_formats(self):
        """Test wizard with different output formats."""
        output_formats = ["HTML", "PDF", "Excel"]

        for format_type in output_formats:
            wizard = frappe.get_doc({
                "doctype": "Financial Report Wizard",
                "report_name": f"Test {format_type}",
                "report_type": "Billing Summary",
                "output_format": format_type
            })
            wizard.insert()

            self.assertEqual(wizard.output_format, format_type)

            # Clean up
            wizard.delete()


def create_test_ra_bill(project, start_date, end_date, gross_value, status="Submitted"):
    """Helper function to create test RA Bill."""
    ra_bill = frappe.get_doc({
        "doctype": "RA Bill",
        "project": project,
        "billing_period_start": start_date,
        "billing_period_end": end_date,
        "gross_certified_value": gross_value,
        "retention_percentage": 10,
        "retention_amount": gross_value * 0.10,
        "net_certified_value": gross_value * 0.90,
        "vat_amount": gross_value * 0.90 * 0.15,
        "total_invoice_value": gross_value * 0.90 * 1.15,
        "status": status
    })

    if status == "Approved":
        ra_bill.certification_date = today()

    ra_bill.insert()
    if status == "Approved":
        ra_bill.submit()

    return ra_bill


if __name__ == "__main__":
    unittest.main()
