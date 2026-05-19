"""
Financial Report Wizard Controller

Guided wizard for generating EPC project financial reports.
"""

import frappe
from frappe import _
from frappe.utils import now_datetime, today, get_datetime, date_diff
from frappe.model.document import Document
from epc_modules.utils import get_epc_logger

logger = get_epc_logger(__name__)


class FinancialReportWizard(Document):
    """Controller for Financial Report Wizard."""

    def autoname(self):
        """Generate wizard_id like FRW-YYYYMMDD-001."""
        if not self.wizard_id:
            date_str = today().replace("-", "")
            # Get the last wizard ID for today
            last_wizard = frappe.db.sql("""
                SELECT name FROM `tabFinancial Report Wizard`
                WHERE wizard_id LIKE %s
                ORDER BY name DESC LIMIT 1
            """, (f"FRW-{date_str}-%",))

            if last_wizard:
                # Extract the sequence number and increment
                last_id = last_wizard[0][0]
                last_seq = frappe.db.get_value(
                    "Financial Report Wizard", last_id, "wizard_id"
                )
                if last_seq:
                    seq = int(last_seq.split("-")[-1]) + 1
                else:
                    seq = 1
            else:
                seq = 1

            self.wizard_id = f"FRW-{date_str}-{seq:03d}"

    def validate(self):
        """Validate report wizard settings."""
        # Ensure from_date is before to_date if both are set
        if self.from_date and self.to_date:
            if get_datetime(self.from_date) > get_datetime(self.to_date):
                frappe.throw(_("From Date must be before or equal to To Date"))

        # Report type specific validation
        if self.report_type == "Cash Flow":
            if not self.from_date or not self.to_date:
                frappe.throw(_("Cash Flow report requires a date range"))

        # Set default group_by if not set
        if not self.group_by:
            self.group_by = "WBS"

    def generate_report(self):
        """
        Generate the financial report based on report_type.
        Delegates to reports_api functions.
        """
        from epc_modules.api.reports_api import generate_financial_report

        try:
            self.db_set("status", "Generating")
            self.reload()

            # Prepare data for report generation
            data = {
                "wizard_name": self.name,
                "report_type": self.report_type,
                "project": self.project,
                "wbs_item": self.wbs_item,
                "from_date": self.from_date,
                "to_date": self.to_date,
                "include_archived": self.include_archived,
                "group_by": self.group_by,
                "output_format": self.output_format
            }

            # Call the appropriate report generator
            result = generate_financial_report(data)

            # Update wizard with results
            self.db_set("status", "Generated")
            self.db_set("generated_on", now_datetime())
            self.db_set("report_data", frappe.as_json(result))
            self.reload()

            return result

        except Exception as e:
            logger.error(f"Error generating financial report: {str(e)}")
            self.db_set("status", "Failed")
            self.db_set("remarks", f"Error: {str(e)}")
            self.reload()
            frappe.throw(_(f"Failed to generate report: {str(e)}"))

    def before_save(self):
        """Set default values before saving."""
        if not self.status:
            self.status = "Draft"
        if not self.output_format:
            self.output_format = "HTML"