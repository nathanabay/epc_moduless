"""
BOQ Calculator Tests

Tests for the polymorphic BOQ calculator.
"""

import unittest
import frappe
from frappe.utils import flt
from epc_modules.utils.boq_calculator import BOQCalculator


class TestBOQCalculator(unittest.TestCase):
    """Test BOQ calculation methods."""

    def setUp(self):
        """Set up test environment."""
        frappe.set_user("Administrator")
        self.maxDiff = None

    def test_unit_based_calculation(self):
        """Test unit-based progress calculation."""
        boq_item = {
            "item_code": "Concrete",
            "measurement_method": "Unit-Based",
            "boq_quantity": 100,
            "unit": "CUM",
            "unit_rate": 5000,
            "total_value": 500000
        }

        entries = [
            {"quantity_executed": 25, "is_milestone_achieved": 0},
            {"quantity_executed": 30, "is_milestone_achieved": 0},
            {"quantity_executed": 20, "is_milestone_achieved": 0}
        ]

        result = BOQCalculator.calculate_item_completion(boq_item, entries)

        self.assertEqual(result["cumulative_quantity"], 75)
        self.assertEqual(result["percent_complete"], 75)
        self.assertEqual(result["financial_value"], 375000)

    def test_percentage_based_calculation(self):
        """Test percentage-based progress calculation."""
        boq_item = {
            "item_code": "Site Preparation",
            "measurement_method": "Percentage-Based",
            "total_value": 1000000
        }

        entries = [
            {"percent_executed": 30},
            {"percent_executed": 25}
        ]

        result = BOQCalculator.calculate_item_completion(boq_item, entries)

        self.assertEqual(result["percent_complete"], 55)
        self.assertEqual(result["financial_value"], 550000)

    def test_milestone_based_calculation(self):
        """Test milestone-based progress (0%, 50%, 100%)."""
        boq_item = {
            "item_code": "Design Phase",
            "measurement_method": "Milestone-Based",
            "total_value": 1000000,
            "milestones": [
                {"name": "initiation", "value_percentage": 10},
                {"name": "completion", "value_percentage": 90}
            ]
        }

        entries = [
            {"milestone_name": "initiation", "is_milestone_achieved": 1},
            {"milestone_name": "completion", "is_milestone_achieved": 0}
        ]

        result = BOQCalculator.calculate_item_completion(boq_item, entries)

        self.assertEqual(result["percent_complete"], 10)
        self.assertEqual(result["financial_value"], 100000)
        self.assertEqual(result["achieved_milestones"], ["initiation"])

    def test_over_billing_prevention_unit(self):
        """Test that over-billing is prevented for unit-based."""
        boq_item = {
            "item_code": "Steel",
            "measurement_method": "Unit-Based",
            "boq_quantity": 50,
            "unit": "TON",
            "unit_rate": 100000,
            "total_value": 5000000
        }

        # Cumulative exceeds BOQ quantity
        entries = [
            {"quantity_executed": 30, "is_milestone_achieved": 0},
            {"quantity_executed": 30, "is_milestone_achieved": 0}  # Would exceed 50
        ]

        result = BOQCalculator.calculate_item_completion(boq_item, entries)

        # Should cap at 100%
        self.assertEqual(result["percent_complete"], 100)
        self.assertEqual(result["cumulative_quantity"], 50)

    def test_under_billing_allowed(self):
        """Test that under-billing is allowed and tracked."""
        boq_item = {
            "item_code": "Foundation",
            "measurement_method": "Unit-Based",
            "boq_quantity": 100,
            "unit": "CUM",
            "unit_rate": 5000,
            "total_value": 500000
        }

        entries = [
            {"quantity_executed": 50, "is_milestone_achieved": 0}
        ]

        result = BOQCalculator.calculate_item_completion(boq_item, entries)

        self.assertEqual(result["percent_complete"], 50)
        self.assertEqual(result["cumulative_quantity"], 50)
        self.assertEqual(result["pending_quantity"], 50)

    def test_financial_value_calculation(self):
        """Test financial value calculation is correct."""
        boq_item = {
            "item_code": "Concrete",
            "measurement_method": "Unit-Based",
            "boq_quantity": 200,
            "unit": "CUM",
            "unit_rate": 4500,
            "total_value": 900000
        }

        entries = [
            {"quantity_executed": 80, "is_milestone_achieved": 0}
        ]

        result = BOQCalculator.calculate_item_completion(boq_item, entries)

        # 80/200 = 40%, 40% of 900000 = 360000
        self.assertEqual(result["percent_complete"], 40)
        self.assertEqual(result["financial_value"], 360000)

    def test_empty_entries(self):
        """Test calculation with no entries."""
        boq_item = {
            "item_code": "Concrete",
            "measurement_method": "Unit-Based",
            "boq_quantity": 100,
            "unit": "CUM",
            "unit_rate": 5000,
            "total_value": 500000
        }

        entries = []

        result = BOQCalculator.calculate_item_completion(boq_item, entries)

        self.assertEqual(result["percent_complete"], 0)
        self.assertEqual(result["cumulative_quantity"], 0)
        self.assertEqual(result["financial_value"], 0)


class TestBOQCalculatorAggregations(unittest.TestCase):
    """Test BOQ project-level aggregations."""

    def setUp(self):
        frappe.set_user("Administrator")

    def test_project_total_calculation(self):
        """Test project total BOQ value calculation."""
        boq_items = [
            {"item_code": "Item1", "total_value": 100000},
            {"item_code": "Item2", "total_value": 200000},
            {"item_code": "Item3", "total_value": 300000}
        ]

        total = BOQCalculator.calculate_project_total(boq_items)
        self.assertEqual(total, 600000)

    def test_weighted_progress(self):
        """Test weighted progress calculation."""
        boq_items = [
            {"item_code": "Item1", "total_value": 100000, "percent_complete": 50},
            {"item_code": "Item2", "total_value": 400000, "percent_complete": 25}
        ]

        weighted_progress = BOQCalculator.calculate_weighted_progress(boq_items)

        # (100000*50 + 400000*25) / 500000 = (50000 + 100000) / 500000 = 30%
        self.assertEqual(weighted_progress, 30)


class TestBOQMeasurementMethods(unittest.TestCase):
    """Test different measurement method behaviors."""

    def setUp(self):
        frappe.set_user("Administrator")

    def test_unit_method_requires_quantity(self):
        """Test unit-based method requires quantity_executed."""
        boq_item = {
            "measurement_method": "Unit-Based",
            "boq_quantity": 100,
            "unit_rate": 100
        }

        entries = [{"percent_executed": 50}]  # Wrong field

        result = BOQCalculator.calculate_item_completion(boq_item, entries)

        # Should handle gracefully - returns 0 since no valid entries
        self.assertEqual(result["cumulative_quantity"], 0)

    def test_percentage_method_requires_percent(self):
        """Test percentage-based method requires percent_executed."""
        boq_item = {
            "measurement_method": "Percentage-Based",
            "total_value": 100000
        }

        entries = [{"quantity_executed": 50}]  # Wrong field

        result = BOQCalculator.calculate_item_completion(boq_item, entries)

        self.assertEqual(result["percent_complete"], 0)


if __name__ == "__main__":
    unittest.main()
