"""
Billing Calculator Module

Dual-track billing engine implementing RA-Billing and Milestone-Billing
per Ethiopian regulatory requirements (PPA 2011, VAT 1341/2024).
"""

import frappe
from frappe import _
from frappe.utils import flt, today, add_days, get_datetime
from typing import Dict, List, Optional, Any
from epc_modules.utils import get_epc_logger

logger = get_epc_logger(__name__)


class RABillingCalculator:
    """
    RA (Running Account) Billing Calculator implementing Ethiopian PPA 2011.

    Key features:
    - Mobilization advance recovery with threshold-based calculation
    - Retention with defect liability period
    - Ethiopian VAT 15% calculation
    - Cumulative value tracking
    """

    # Default thresholds per PPA 2011
    DEFAULT_LOWER_THRESHOLD = 0.20  # 20% completion before recovery starts
    DEFAULT_UPPER_THRESHOLD = 0.80  # 80% completion before recovery must complete

    @staticmethod
    def calculate_advance_recovery(
        original_advance: float,
        current_certified_value: float,
        total_contract_value: float,
        cumulative_certified_value: float,
        lower_threshold: float = None,
        upper_threshold: float = None
    ) -> Dict[str, float]:
        """
        Calculate mobilization advance recovery per PPA 2011.

        Recovery begins after lower_threshold (default 20%) completion
        and must be complete by upper_threshold (default 80%) completion.

        Args:
            original_advance: Original advance amount
            current_certified_value: Certified value this period
            total_contract_value: Total contract value
            cumulative_certified_value: Total cumulative certified value
            lower_threshold: Threshold to start recovery (default 20%)
            upper_threshold: Threshold to complete recovery (default 80%)

        Returns:
            dict with advance_recovery, remaining_advance, status
        """
        if lower_threshold is None:
            lower_threshold = RABillingCalculator.DEFAULT_LOWER_THRESHOLD
        if upper_threshold is None:
            upper_threshold = RABillingCalculator.DEFAULT_UPPER_THRESHOLD

        lt_value = total_contract_value * lower_threshold
        ut_value = total_contract_value * upper_threshold
        certifiable_range = ut_value - lt_value

        result = {
            "advance_recovery": 0.0,
            "remaining_advance": original_advance,
            "status": "below_threshold",
            "cumulative_certified_pct": (cumulative_certified_value / total_contract_value * 100) if total_contract_value > 0 else 0
        }

        if current_certified_value <= 0 or original_advance <= 0:
            return result

        # Already fully recovered
        if cumulative_certified_value >= original_advance:
            result["status"] = "fully_recovered"
            result["advance_recovery"] = 0
            return result

        if cumulative_certified_value < lt_value:
            result["status"] = "below_threshold"
            return result

        # Calculate recovery based on certifiable range
        if certifiable_range > 0:
            recovery_factor = original_advance / certifiable_range
            advance_recovery = current_certified_value * recovery_factor
        else:
            advance_recovery = current_certified_value

        # Cap at remaining advance
        remaining = original_advance - cumulative_certified_value
        advance_recovery = min(advance_recovery, remaining)

        # Cap at current certified value
        advance_recovery = min(advance_recovery, current_certified_value)

        result["advance_recovery"] = max(0, flt(advance_recovery, 2))
        result["remaining_advance"] = remaining - result["advance_recovery"]

        if result["remaining_advance"] <= 0:
            result["status"] = "fully_recovered"
        elif cumulative_certified_value >= ut_value:
            result["status"] = "final_recovery_phase"
        else:
            result["status"] = "recovery_active"

        return result

    @staticmethod
    def calculate_retention(
        net_certified_value: float,
        retention_percentage: float = 10,
        project_completion: float = 0,
        defect_liability_months: int = 12
    ) -> Dict[str, float]:
        """
        Calculate retention amount with defect liability release.

        Per standard construction contracts:
        - 50% retention released after substantial completion (90%+)
        - Remaining 50% released after defect liability period

        Args:
            net_certified_value: Net certified value
            retention_percentage: Retention % (default 10)
            project_completion: Project completion %
            defect_liability_months: Defect liability period

        Returns:
            dict with retention_amount, released_amount, held_amount
        """
        gross_retention = net_certified_value * (retention_percentage / 100)

        result = {
            "retention_amount": flt(gross_retention, 2),
            "released_amount": 0,
            "held_amount": flt(gross_retention, 2),
            "defect_liability_months": defect_liability_months
        }

        # 50% release at substantial completion (90%+)
        if project_completion >= 90:
            result["released_amount"] = flt(gross_retention * 0.5, 2)
            result["held_amount"] = flt(gross_retention * 0.5, 2)

        # Full release after defect liability (simplified - assume if completion = 100%)
        if project_completion >= 100:
            result["released_amount"] = flt(gross_retention, 2)
            result["held_amount"] = 0

        return result

    @staticmethod
    def calculate_vat(
        net_payable: float,
        vat_rate: float = 15,
        is_exempt: bool = False
    ) -> Dict[str, float]:
        """
        Calculate Ethiopian VAT per Proclamation 1341/2024.

        Standard VAT rate is 15% on net taxable amount.

        Args:
            net_payable: Net payable amount
            vat_rate: VAT rate % (default 15 for Ethiopia)
            is_exempt: Whether transaction is VAT exempt

        Returns:
            dict with vat_amount, total_invoice_value, is_exempt
        """
        if is_exempt:
            return {
                "vat_rate": 0,
                "vat_amount": 0,
                "total_invoice_value": net_payable,
                "is_exempt": True
            }

        vat_amount = net_payable * (vat_rate / 100)

        return {
            "vat_rate": vat_rate,
            "vat_amount": flt(vat_amount, 2),
            "total_invoice_value": flt(net_payable + vat_amount, 2),
            "is_exempt": False
        }

    @staticmethod
    def calculate_ra_bill_totals(
        project: str,
        measurement_book_values: List[Dict],
        billing_period_end: str = None
    ) -> Dict[str, Any]:
        """
        Calculate complete RA bill totals for a billing period.

        Args:
            project: Project name
            measurement_book_values: List of MB refs with certified values
            billing_period_end: Period end date

        Returns:
            Complete billing calculation
        """
        project_doc = frappe.get_cached_doc("Project", project)

        # Get project financial settings
        original_advance = flt(getattr(project_doc, 'mobilization_advance_amount', 0))
        total_contract_value = flt(project_doc.contract_value or project_doc.total_contract_value)
        retention_percentage = flt(project_doc.retention_percentage or 10)
        vat_rate = 15  # Ethiopian standard

        # Calculate gross certified from MBs
        gross_certified = sum(
            flt(mb.get('certified_value', 0))
            for mb in measurement_book_values
            if mb.get('is_certified')
        )

        # Get cumulative certified from previous RA bills
        cumulative_certified = frappe.db.sql("""
            SELECT SUM(gross_certified_value)
            FROM `tabRA Bill`
            WHERE project = %s AND docstatus = 1
        """, project)[0][0] or 0

        current_certified = gross_certified
        new_cumulative = cumulative_certified + current_certified

        # Calculate advance recovery
        advance_calc = RABillingCalculator.calculate_advance_recovery(
            original_advance=original_advance,
            current_certified_value=current_certified,
            total_contract_value=total_contract_value,
            cumulative_certified_value=cumulative_certified
        )

        # Net certified after advance recovery
        net_certified = current_certified - advance_calc["advance_recovery"]

        # Calculate retention
        retention_calc = RABillingCalculator.calculate_retention(
            net_certified=net_certified,
            retention_percentage=retention_percentage,
            project_completion=flt(project_doc.percent_complete or 0)
        )

        # Net payable after retention
        net_payable = net_certified - retention_calc["held_amount"]

        # Calculate VAT
        vat_calc = RABillingCalculator.calculate_vat(net_payable, vat_rate)

        # Calculate project completion %
        project_completion = (new_cumulative / total_contract_value * 100) if total_contract_value > 0 else 0

        return {
            # Inputs
            "project": project,
            "total_contract_value": total_contract_value,
            "original_advance": original_advance,
            "measurement_books_count": len(measurement_book_values),

            # Gross calculations
            "gross_certified_value": flt(gross_certified, 2),
            "cumulative_certified_value": flt(new_cumulative, 2),
            "project_completion_pct": flt(project_completion, 2),

            # Advance recovery
            "advance_recovered": advance_calc["advance_recovery"],
            "cumulative_advance_recovered": flt(cumulative_certified + advance_calc["advance_recovery"], 2),
            "remaining_advance": advance_calc["remaining_advance"],
            "advance_status": advance_calc["status"],

            # Net calculations
            "net_certified_value": flt(net_certified, 2),

            # Retention
            "retention_percentage": retention_percentage,
            "retention_amount": retention_calc["retention_amount"],
            "retention_released": retention_calc["released_amount"],
            "retention_held": retention_calc["held_amount"],

            # Net payable
            "net_payable": flt(net_payable, 2),

            # VAT
            "vat_rate": vat_rate,
            "vat_amount": vat_calc["vat_amount"],

            # Invoice total
            "total_invoice_value": vat_calc["total_invoice_value"]
        }


class MilestoneBillingCalculator:
    """
    Milestone Billing Calculator for service/consulting projects.

    Triggers invoices when milestones are achieved.
    """

    @staticmethod
    def get_project_milestones(project: str) -> List[Dict]:
        """
        Get all milestones for a project.

        Args:
            project: Project name

        Returns:
            List of milestone configs
        """
        project_doc = frappe.get_cached_doc("Project", project)

        if not hasattr(project_doc, 'milestones'):
            return []

        return [
            {
                "name": m.name,
                "milestone_name": m.milestone_name,
                "sequence": m.sequence,
                "planned_date": m.planned_date,
                "actual_date": m.actual_date,
                "trigger_percentage": m.trigger_percentage,
                "invoice_amount": m.invoice_amount,
                "is_invoiced": m.is_invoiced,
                "status": m.status
            }
            for m in project_doc.milestones
        ]

    @staticmethod
    def check_milestone_triggers(project: str) -> List[Dict]:
        """
        Check which milestones should be triggered based on progress.

        Args:
            project: Project name

        Returns:
            List of milestones to trigger
        """
        project_doc = frappe.get_cached_doc("Project", project)
        current_progress = flt(project_doc.percent_complete or 0)

        triggers = []

        if hasattr(project_doc, 'milestones'):
            for m in project_doc.milestones:
                if not m.is_invoiced and m.trigger_percentage:
                    if current_progress >= flt(m.trigger_percentage):
                        triggers.append({
                            "name": m.name,
                            "milestone_name": m.milestone_name,
                            "trigger_percentage": m.trigger_percentage,
                            "invoice_amount": m.invoice_amount
                        })

        return triggers

    @staticmethod
    def generate_milestone_invoice(
        project: str,
        milestone_name: str
    ) -> Dict[str, Any]:
        """
        Generate Sales Invoice for a milestone.

        Args:
            project: Project name
            milestone_name: Milestone doc name

        Returns:
            Invoice creation result
        """
        if not frappe.db.exists("Project Milestone", milestone_name):
            frappe.throw(_("Milestone {0} does not exist").format(milestone_name))

        milestone = frappe.get_doc("Project Milestone", milestone_name)

        if milestone.is_invoiced:
            frappe.throw(_("Milestone {0} already invoiced").format(milestone_name))

        project_doc = frappe.get_doc("Project", project)

        # Create sales invoice
        si = frappe.get_doc({
            "doctype": "Sales Invoice",
            "project": project,
            "customer": project_doc.customer,
            "due_date": add_days(today(), 30),
            "is_pos": 0,
            "items": [{
                "item_code": "Milestone Invoice",
                "description": f"Milestone: {milestone.milestone_name}",
                "qty": 1,
                "rate": milestone.invoice_amount,
                "amount": milestone.invoice_amount,
                "project": project
            }],
            "taxes": [{
                "doctype": "Sales Taxes and Charges",
                "charge_type": "On Net Total",
                "account_head": frappe.db.get_value("Account", {"account_name": ["like", "%VAT%"]}, "name") or "VAT - E",
                "description": "VAT 15% (Proclamation 1341/2024)",
                "rate": 15,
                "cost_center": "Main - E"
            }]
        })

        si.insert(ignore_permissions=True)
        si.submit()

        # Update milestone
        frappe.db.set_value("Project Milestone", milestone_name, {
            "is_invoiced": 1,
            "actual_date": today(),
            "sales_invoice": si.name,
            "status": "Invoiced",
            "invoice_date": today()
        })

        logger.info(f"Generated milestone invoice {si.name} for project {project}")

        return {
            "success": True,
            "sales_invoice": si.name,
            "milestone": milestone_name,
            "invoice_amount": milestone.invoice_amount,
            "invoice_date": today()
        }


class BillingEngine:
    """
    Unified billing engine that delegates to appropriate calculator
    based on project's billing track.
    """

    @staticmethod
    def get_calculator_for_project(project: str) -> Any:
        """
        Get appropriate billing calculator for project.

        Args:
            project: Project name

        Returns:
            RA or Milestone billing calculator
        """
        project_doc = frappe.get_cached_doc("Project", project)

        if not project_doc.project_typology:
            raise EPCException("Project must have a typology assigned")

        typology = frappe.get_cached_doc("Project Typology", project_doc.project_typology)

        if typology.billing_track == "Milestone-Billing":
            return MilestoneBillingCalculator
        else:
            # Default to RA Billing for construction projects
            return RABillingCalculator

    @staticmethod
    def calculate_billing(project: str, **kwargs) -> Dict[str, Any]:
        """
        Calculate billing for a project based on its typology.

        Args:
            project: Project name
            **kwargs: Additional parameters for specific calculator

        Returns:
            Billing calculation result
        """
        calculator = BillingEngine.get_calculator_for_project(project)

        if calculator == RABillingCalculator:
            return RABillingCalculator.calculate_ra_bill_totals(
                project,
                kwargs.get('measurement_book_values', [])
            )
        else:
            return {
                "project": project,
                "billing_type": "Milestone-Billing",
                "pending_milestones": MilestoneBillingCalculator.check_milestone_triggers(project)
            }

    @staticmethod
    def get_billing_summary(project: str) -> Dict[str, Any]:
        """
        Get complete billing summary for a project.

        Args:
            project: Project name

        Returns:
            Summary with RA and milestone billing status
        """
        project_doc = frappe.get_cached_doc("Project", project)

        summary = {
            "project": project,
            "contract_value": flt(project_doc.contract_value),
            "total_billed": 0,
            "pending_billing": 0,
            "billing_track": None
        }

        if project_doc.project_typology:
            typology = frappe.get_cached_doc("Project Typology", project_doc.project_typology)
            summary["billing_track"] = typology.billing_track

            if typology.billing_track == "RA-Billing":
                # Get RA bill totals
                ra_total = frappe.db.sql("""
                    SELECT SUM(total_invoice_value) as total, SUM(net_payable) as payable
                    FROM `tabRA Bill`
                    WHERE project = %s AND docstatus = 1
                """, project)[0]

                summary["total_billed"] = flt(ra_total.total) if ra_total else 0
                summary["pending_billing"] = flt(project_doc.contract_value) - summary["total_billed"]

            elif typology.billing_track == "Milestone-Billing":
                # Get milestone totals
                milestones = frappe.get_all(
                    "Project Milestone",
                    filters={"parent": project, "is_invoiced": 1},
                    fields=["SUM(invoice_amount) as total"]
                )

                summary["total_billed"] = flt(milestones[0].total) if milestones and milestones[0].total else 0
                summary["pending_milestones"] = MilestoneBillingCalculator.get_project_milestones(project)

        summary["billing_percentage"] = (summary["total_billed"] / summary["contract_value"] * 100) if summary["contract_value"] > 0 else 0

        return summary


# Import for custom exception
from epc_modules.utils import EPCException