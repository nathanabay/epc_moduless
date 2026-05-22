"""
Tests for Project Report Wizard

Unit tests for the Project Report Wizard doctype and reports API.
"""

import frappe
import unittest
from frappe.utils import today, add_days, now_datetime
from frappe.tests.utils import FrappeTestCase


class TestProjectReportWizard(FrappeTestCase):
    """Test cases for Project Report Wizard."""

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
        frappe.db.delete("Project Report Wizard", {"wizard_id": ["like", "PRW-TEST-%"]})

    def test_wizard_creation(self):
        """Test basic wizard document creation."""
        wizard = frappe.get_doc({
            "doctype": "Project Report Wizard",
            "report_name": "Test Project Status Report",
            "report_type": "Project Status",
            "project": self.test_project.name,
            "output_format": "HTML"
        })
        wizard.insert()

        # Verify auto-generated wizard_id
        self.assertIsNotNone(wizard.wizard_id)
        self.assertTrue(wizard.wizard_id.startswith("PRW-"))

        # Verify default values
        self.assertEqual(wizard.status, "Draft")
        self.assertEqual(wizard.output_format, "HTML")

        # Clean up
        wizard.delete()

    def test_wizard_autoname_generation(self):
        """Test that wizard_id is auto-generated correctly."""
        wizard = frappe.get_doc({
            "doctype": "Project Report Wizard",
            "report_name": "Test Report",
            "report_type": "NCR Summary"
        })
        wizard.insert()

        # Check format PRW-YYYYMMDD-XXX
        self.assertRegex(wizard.wizard_id, r"PRW-\d{8}-\d{3}")

        # Clean up
        wizard.delete()

    def test_date_validation(self):
        """Test that from_date < to_date validation works."""
        wizard = frappe.get_doc({
            "doctype": "Project Report Wizard",
            "report_name": "Test Report",
            "report_type": "DPR Summary",
            "from_date": today(),
            "to_date": add_days(today(), -30)  # to_date before from_date
        })

        # This should throw validation error
        with self.assertRaises(frappe.ValidationError):
            wizard.insert()

    def test_project_status_report(self):
        """Test Project Status report generation."""
        from epc_modules.api.reports_api import get_project_status_report

        result = get_project_status_report(project=self.test_project.name)

        # Verify result structure
        self.assertEqual(result["report_type"], "Project Status")
        self.assertIn("summary", result)
        self.assertIn("details", result)

        # Verify summary keys
        summary_keys = ["status", "percent_complete", "wbs_items", "open_ncrs"]
        for key in summary_keys:
            self.assertIn(key, result["summary"])

    def test_wip_report(self):
        """Test WIP Report generation."""
        from epc_modules.api.reports_api import get_wip_report

        result = get_wip_report(
            project=self.test_project.name,
            include_wbs=False
        )

        # Verify structure
        self.assertEqual(result["report_type"], "WIP Report")
        self.assertIn("summary", result)
        self.assertIn("by_status", result)

        # Verify summary has required keys
        summary_keys = ["total_wbs_items", "total_planned_value", "total_cost_incurred"]
        for key in summary_keys:
            self.assertIn(key, result["summary"])

    def test_wip_report_with_wbs_details(self):
        """Test WIP Report with WBS details included."""
        from epc_modules.api.reports_api import get_wip_report

        result = get_wip_report(
            project=self.test_project.name,
            include_wbs=True
        )

        # Verify structure
        self.assertEqual(result["report_type"], "WIP Report")
        self.assertIn("details", result)

    def test_ncr_summary_report(self):
        """Test NCR Summary report generation."""
        from epc_modules.api.reports_api import get_ncr_summary_report

        result = get_ncr_summary_report(
            project=self.test_project.name,
            from_date=add_days(today(), -365),
            to_date=today()
        )

        # Verify structure
        self.assertEqual(result["report_type"], "NCR Summary")
        self.assertIn("summary", result)
        self.assertIn("by_status", result)

        # Verify summary has required keys
        summary_keys = ["total", "open", "in_progress", "closed", "critical", "major", "minor"]
        for key in summary_keys:
            self.assertIn(key, result["summary"])

    def test_ncr_summary_report_with_details(self):
        """Test NCR Summary report with details included."""
        from epc_modules.api.reports_api import get_ncr_summary_report

        result = get_ncr_summary_report(
            project=self.test_project.name,
            from_date=add_days(today(), -365),
            to_date=today(),
            include_details=True
        )

        # Verify structure
        self.assertEqual(result["report_type"], "NCR Summary")
        self.assertIn("details", result)

    def test_dpr_summary_report(self):
        """Test DPR Summary report generation."""
        from epc_modules.api.reports_api import get_dpr_summary_report

        result = get_dpr_summary_report(
            project=self.test_project.name,
            from_date=add_days(today(), -365),
            to_date=today()
        )

        # Verify structure
        self.assertEqual(result["report_type"], "DPR Summary")
        self.assertIn("summary", result)
        self.assertIn("by_status", result)
        self.assertIn("daily_data", result)

        # Verify summary has required keys
        summary_keys = ["total_entries", "total_labor_days", "total_equipment_days"]
        for key in summary_keys:
            self.assertIn(key, result["summary"])

    def test_rfi_log_report(self):
        """Test RFI Log report generation."""
        from epc_modules.api.reports_api import get_rfi_log_report

        result = get_rfi_log_report(
            project=self.test_project.name,
            from_date=add_days(today(), -365),
            to_date=today()
        )

        # Verify structure
        self.assertEqual(result["report_type"], "RFI Log")
        self.assertIn("summary", result)
        self.assertIn("by_status", result)
        self.assertIn("details", result)

        # Verify summary has required keys
        summary_keys = ["total_rfis", "open_rfis", "closed_rfis", "closure_rate"]
        for key in summary_keys:
            self.assertIn(key, result["summary"])

    def test_inspection_status_report(self):
        """Test Inspection Status report generation."""
        from epc_modules.api.reports_api import get_inspection_status_report

        result = get_inspection_status_report(project=self.test_project.name)

        # Verify structure
        self.assertEqual(result["report_type"], "Inspection Status")
        self.assertIn("summary", result)
        self.assertIn("itp_by_status", result)
        self.assertIn("inspection_by_status", result)

        # Verify summary has required keys
        summary_keys = ["total_itps", "total_inspections", "pass_rate"]
        for key in summary_keys:
            self.assertIn(key, result["summary"])

    def test_inspection_status_report_with_ncrs(self):
        """Test Inspection Status report with linked NCRs."""
        from epc_modules.api.reports_api import get_inspection_status_report

        result = get_inspection_status_report(
            project=self.test_project.name,
            include_ncrs=True
        )

        # Verify structure
        self.assertEqual(result["report_type"], "Inspection Status")
        self.assertIn("linked_ncrs", result)

    def test_equipment_utilization_report(self):
        """Test Equipment Utilization report generation."""
        from epc_modules.api.reports_api import get_equipment_utilization_report

        result = get_equipment_utilization_report(project=self.test_project.name)

        # Verify structure
        self.assertEqual(result["report_type"], "Equipment Utilization")
        self.assertIn("summary", result)
        self.assertIn("by_category", result)
        self.assertIn("by_status", result)

        # Verify summary has required keys
        summary_keys = ["total_equipment", "in_use", "utilization_rate"]
        for key in summary_keys:
            self.assertIn(key, result["summary"])

    def test_team_performance_report(self):
        """Test Team Performance report generation."""
        from epc_modules.api.reports_api import get_team_performance_report

        result = get_team_performance_report(
            project=self.test_project.name,
            from_date=add_days(today(), -365),
            to_date=today()
        )

        # Verify structure
        self.assertEqual(result["report_type"], "Team Performance")
        self.assertIn("summary", result)
        self.assertIn("daily_data", result)
        self.assertIn("supervisor_summary", result)

        # Verify summary has required keys
        summary_keys = ["total_dpr_entries", "total_labor_days", "avg_daily_labor"]
        for key in summary_keys:
            self.assertIn(key, result["summary"])

    def test_generate_project_report_api(self):
        """Test the main generate_project_report API function."""
        from epc_modules.api.reports_api import generate_project_report

        wizard = frappe.get_doc({
            "doctype": "Project Report Wizard",
            "report_name": "API Test Report",
            "report_type": "Project Status",
            "project": self.test_project.name
        }).insert()

        data = {
            "wizard_name": wizard.name,
            "report_type": "Project Status",
            "project": self.test_project.name,
            "output_format": "HTML"
        }

        result = generate_project_report(data)

        # Verify success
        self.assertTrue(result.get("success"))

        # Verify wizard status updated
        wizard.reload()
        self.assertEqual(wizard.status, "Generated")

        # Clean up
        wizard.delete()

    def test_generate_all_report_types(self):
        """Test generation of all report types."""
        from epc_modules.api.reports_api import generate_project_report

        report_types = [
            "Project Status",
            "WIP Report",
            "NCR Summary",
            "DPR Summary",
            "RFI Log",
            "Inspection Status",
            "Equipment Utilization",
            "Team Performance"
        ]

        for report_type in report_types:
            wizard = frappe.get_doc({
                "doctype": "Project Report Wizard",
                "report_name": f"Test {report_type}",
                "report_type": report_type,
                "project": self.test_project.name
            }).insert()

            data = {
                "wizard_name": wizard.name,
                "report_type": report_type,
                "project": self.test_project.name,
                "output_format": "HTML"
            }

            result = generate_project_report(data)

            # Verify success
            self.assertTrue(result.get("success"), f"Failed for {report_type}")

            # Verify wizard status updated
            wizard.reload()
            self.assertIn(wizard.status, ["Generated", "Failed"])

            # Clean up
            wizard.delete()

    def test_wizard_with_all_output_formats(self):
        """Test wizard with different output formats."""
        output_formats = ["HTML", "PDF", "Excel"]

        for format_type in output_formats:
            wizard = frappe.get_doc({
                "doctype": "Project Report Wizard",
                "report_name": f"Test {format_type}",
                "report_type": "Team Performance",
                "output_format": format_type
            })
            wizard.insert()

            self.assertEqual(wizard.output_format, format_type)

            # Clean up
            wizard.delete()

    def test_wizard_with_filters(self):
        """Test wizard with various filters."""
        wizard = frappe.get_doc({
            "doctype": "Project Report Wizard",
            "report_name": "Filtered Report",
            "report_type": "NCR Summary",
            "project": self.test_project.name,
            "typology_filter": "Electromechanical",
            "from_date": add_days(today(), -30),
            "to_date": today(),
            "include_wbs": 1,
            "include_ncrs": 1,
            "output_format": "HTML"
        })
        wizard.insert()

        # Verify filter values are set
        self.assertEqual(wizard.typology_filter, "Electromechanical")
        self.assertEqual(wizard.include_wbs, 1)
        self.assertEqual(wizard.include_ncrs, 1)

        # Clean up
        wizard.delete()


if __name__ == "__main__":
    unittest.main()