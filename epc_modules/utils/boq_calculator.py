"""
BOQ Calculator Module

Provides polymorphic calculation of project progress based on measurement methods.
"""

import frappe
from frappe import _
from epc_modules.utils import get_epc_logger

logger = get_epc_logger(__name__)


class BOQCalculator:
    """Calculator for BOQ-based project progress."""

    @staticmethod
    def calculate_item_completion(boq_item, dpr_entries):
        """
        Calculate completion based on measurement method.

        Args:
            boq_item: Custom BOQ document
            dpr_entries: List of DPR Line Item documents

        Returns:
            dict: Completion data including cumulative_quantity, percent_complete, financial_value
        """
        method = boq_item.get("measurement_method", "Unit-Based")

        if method == "Unit-Based":
            return BOQCalculator._calculate_unit_based(boq_item, dpr_entries)
        elif method == "Percentage-Based":
            return BOQCalculator._calculate_percentage_based(boq_item, dpr_entries)
        elif method == "Milestone-Based":
            return BOQCalculator._calculate_milestone_based(boq_item, dpr_entries)
        else:
            # Default to unit-based
            return BOQCalculator._calculate_unit_based(boq_item, dpr_entries)

    @staticmethod
    def _calculate_unit_based(boq_item, dpr_entries):
        """
        Unit-based: aggregate cumulative quantities.
        Used for Civil projects with continuous measurement (concrete, earthworks, etc.)
        """
        total_executed = sum(
            entry.get("quantity_executed", 0)
            for entry in dpr_entries
            if entry.get("boq_item") == boq_item.name
        )

        boq_qty = boq_item.get("boq_quantity", 0)
        unit_rate = boq_item.get("unit_rate", 0)

        # Prevent over-billing
        if total_executed > boq_qty:
            frappe.throw(
                _("BOQ item {0} exceeded. BOQ: {1}, Executed: {2}").format(
                    boq_item.item_code, boq_qty, total_executed
                )
            )

        percentage = (total_executed / boq_qty * 100) if boq_qty > 0 else 0
        financial_value = total_executed * unit_rate

        return {
            "cumulative_quantity": total_executed,
            "percent_complete": min(percentage, 100),
            "financial_value": financial_value
        }

    @staticmethod
    def _calculate_percentage_based(boq_item, dpr_entries):
        """
        Percentage-based: weighted progress tracking.
        Used for electromechanical projects with discrete steps.
        """
        latest_entry = dpr_entries[-1] if dpr_entries else None
        if not latest_entry:
            return {"percent_complete": 0, "financial_value": 0}

        percentage = latest_entry.get("percent_complete", 0)
        total_value = boq_item.get("total_value", 0)

        return {
            "percent_complete": min(percentage, 100),
            "financial_value": (percentage / 100) * total_value
        }

    @staticmethod
    def _calculate_milestone_based(boq_item, dpr_entries):
        """
        Milestone-based: discrete state transitions.
        Used for service/consulting projects with binary milestones.
        """
        achieved_milestones = [
            entry for entry in dpr_entries
            if entry.get("boq_item") == boq_item.name
            and entry.get("is_milestone_achieved")
        ]

        if not achieved_milestones:
            return {"percent_complete": 0, "financial_value": 0, "current_milestone": 0}

        # Count discrete milestones (0%, 50%, 100%)
        milestone_count = len(achieved_milestones)
        total_value = boq_item.get("total_value", 0)

        # Calculate percentage based on milestone progression
        if milestone_count == 1:
            percentage = 33.33  # 0% -> 33%
        elif milestone_count == 2:
            percentage = 66.67  # 33% -> 67%
        else:
            percentage = 100

        return {
            "percent_complete": percentage,
            "financial_value": (percentage / 100) * total_value,
            "current_milestone": milestone_count
        }

    @staticmethod
    def aggregate_project_progress(project_name):
        """
        Aggregate all BOQ items into unified project progress.

        Args:
            project_name: Name of the project

        Returns:
            float: Overall project progress percentage
        """
        logger.info(f"Aggregating progress for project: {project_name}")

        project = frappe.get_doc("Project", project_name)
        typology = None

        if project.project_typology:
            typology = frappe.get_doc("Project Typology", project.project_typology)

        boq_items = frappe.get_all(
            "Custom BOQ",
            filters={"parent": project_name},
            fields=["name", "item_code", "total_value", "boq_quantity", "measurement_method"]
        )

        # Batch query: fetch all DPR entries for all BOQ items at once
        boq_names = [item.name for item in boq_items]
        all_dpr_entries = {}
        if boq_names:
            all_dpr = frappe.get_all(
                "DPR Line Item",
                filters={"boq_item": ["in", boq_names]},
                fields=["boq_item", "name", "quantity_executed", "percent_complete", "is_milestone_achieved"],
                order_by="creation asc"
            )
            for entry in all_dpr:
                all_dpr_entries.setdefault(entry.boq_item, []).append(entry)

        total_planned_value = 0
        total_earned_value = 0
        updated_items = []
        wbs_updates = {}  # Collect WBS updates for batch

        for item in boq_items:
            dpr_entries = all_dpr_entries.get(item.name, [])

            completion = BOQCalculator.calculate_item_completion(item, dpr_entries)
            total_planned_value += item.get("total_value", 0)
            total_earned_value += completion.get("financial_value", 0)

            # Collect WBS item updates instead of updating inside loop
            if item.get("wbs_item"):
                wbs_updates[item.wbs_item] = {
                    "earned_value": completion.get("financial_value", 0),
                    "physical_progress": completion.get("percent_complete", 0)
                }

            updated_items.append({
                "item": item.name,
                "progress": completion.get("percent_complete", 0)
            })

        # Batch update all WBS items outside the loop
        for wbs_name, values in wbs_updates.items():
            frappe.db.set_value("WBS Item", wbs_name, values)

        # Calculate overall progress
        if total_planned_value > 0:
            overall_progress = (total_earned_value / total_planned_value) * 100
        else:
            overall_progress = 0

        # Update project (already outside loop)
        frappe.db.set_value("Project", project_name, {
            "percent_complete": overall_progress,
            "earned_value": total_earned_value
        })

        logger.info(
            f"Project {project_name}: Progress = {overall_progress:.2f}%, "
            f"Earned Value = {total_earned_value}"
        )

        return overall_progress

    @staticmethod
    def get_boq_summary(project_name):
        """
        Get summary of BOQ items for a project.

        Args:
            project_name: Name of the project

        Returns:
            dict: Summary data
        """
        boq_items = frappe.get_all(
            "Custom BOQ",
            filters={"parent": project_name},
            fields=["name", "item_code", "description", "boq_quantity", "unit_rate", "total_value"]
        )

        total_value = sum(item.get("total_value", 0) for item in boq_items)

        return {
            "total_items": len(boq_items),
            "total_value": total_value,
            "items": boq_items
        }