"""
Project Report Wizard Controller

Guided wizard for generating EPC project operational reports.
"""

import frappe
from frappe import _
from frappe.utils import now_datetime, today, get_datetime
from frappe.model.document import Document
from epc_modules.utils import get_epc_logger

logger = get_epc_logger(__name__)


class ProjectReportWizard(Document):
    """Controller for Project Report Wizard."""

    def autoname(self):
        """Generate wizard_id like PRW-YYYYMMDD-001."""
        if not self.wizard_id:
            date_str = today().replace("-", "")
            # Get the last wizard ID for today
            last_wizard = frappe.db.sql("""
                SELECT name FROM `tabProject Report Wizard`
                WHERE wizard_id LIKE %s
                ORDER BY name DESC LIMIT 1
            """, (f"PRW-{date_str}-%",))

            if last_wizard:
                # Extract the sequence number and increment
                last_id = last_wizard[0][0]
                last_seq = frappe.db.get_value(
                    "Project Report Wizard", last_id, "wizard_id"
                )
                if last_seq:
                    seq = int(last_seq.split("-")[-1]) + 1
                else:
                    seq = 1
            else:
                seq = 1

            self.wizard_id = f"PRW-{date_str}-{seq:03d}"

    def validate(self):
        """Validate report wizard settings."""
        # Ensure from_date is before to_date if both are set
        if self.from_date and self.to_date:
            if get_datetime(self.from_date) > get_datetime(self.to_date):
                frappe.throw(_("From Date must be before or equal to To Date"))

        # Set defaults
        if not self.output_format:
            self.output_format = "HTML"

    def generate_report(self):
        """
        Generate the project report based on report_type.
        Delegates to reports_api functions.
        """
        from epc_modules.api.reports_api import generate_project_report

        try:
            self.db_set("status", "Generating")
            self.reload()

            # Prepare data for report generation
            data = {
                "wizard_name": self.name,
                "report_name": self.report_name,
                "report_type": self.report_type,
                "project": self.project,
                "typology_filter": self.typology_filter,
                "from_date": self.from_date,
                "to_date": self.to_date,
                "include_wbs": self.include_wbs,
                "include_ncrs": self.include_ncrs,
                "output_format": self.output_format
            }

            # Call the appropriate report generator
            result = generate_project_report(data)

            # Update wizard with results
            self.db_set("status", "Generated")
            self.db_set("generated_on", now_datetime())
            self.db_set("report_data", frappe.as_json(result))
            self.reload()

            return result

        except Exception as e:
            logger.error("Error generating project report: %s", frappe.get_traceback())
            self.db_set("status", "Failed")
            self.reload()
            frappe.throw(_("Failed to generate report. Please contact support."))

    def before_save(self):
        """Set default values before saving."""
        if not self.status:
            self.status = "Draft"