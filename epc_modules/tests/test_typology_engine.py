"""
Typology Engine Tests

Tests for the polymorphic ProjectTypology engine.
"""

import unittest
import frappe
from frappe.utils import flt
from epc_modules.utils.typology_engine import (
    ProjectTypology,
    ElectromechanicalTypology,
    CivilTypology,
    StandardTypology,
    TypologyFactory
)


class TestProjectTypology(unittest.TestCase):
    """Test base Typology class."""

    def setUp(self):
        """Set up test environment."""
        frappe.set_user("Administrator")

    def test_typology_initialization(self):
        """Test typology initializes with project data."""
        project_data = {
            "name": "Test Project",
            "project_name": "Test Project",
            "typology": "Electromechanical",
            "total_contract_value": 10000000,
            "is_advance_interest_free": 0,
            "advance_rap_percentage": 20,
            "defect_liability_period": 12
        }

        typology = ProjectTypology(project_data)

        self.assertEqual(typology.typology, "Electromechanical")
        self.assertEqual(typology.total_contract_value, 10000000)
        self.assertEqual(typology.advance_rap_percentage, 20)

    def test_get_billing_method(self):
        """Test billing method retrieval."""
        project_data = {
            "name": "Test Project",
            "typology": "Civil"
        }

        typology = CivilTypology(project_data)
        method = typology.get_billing_method()

        self.assertEqual(method, "RA-Billing")


class TestElectromechanicalTypology(unittest.TestCase):
    """Test Electromechanical typology."""

    def setUp(self):
        """Set up test environment."""
        frappe.set_user("Administrator")

    def test_is_electromechanical(self):
        """Test Electromechanical type detection."""
        project_data = {
            "name": "Test Project",
            "typology": "Electromechanical"
        }

        typology = ElectromechanicalTypology(project_data)

        self.assertTrue(typology.is_electromechanical())

    def test_retainage_rate(self):
        """Test retainage rate for electromechanical."""
        project_data = {
            "name": "Test Project",
            "typology": "Electromechanical"
        }

        typology = ElectromechanicalTypology(project_data)

        self.assertEqual(typology.get_retainage_rate(), 10)

    def test_advance_limit_percentage(self):
        """Test advance limit for electromechanical."""
        project_data = {
            "name": "Test Project",
            "typology": "Electromechanical"
        }

        typology = ElectromechanicalTypology(project_data)

        # Default 20% for electromechanical
        self.assertEqual(typology.get_advance_limit_percentage(), 20)

    def test_wbs_structure_type(self):
        """Test WBS structure type."""
        project_data = {
            "name": "Test Project",
            "typology": "Electromechanical"
        }

        typology = ElectromechanicalTypology(project_data)
        wbs_type = typology.get_wbs_structure_type()

        self.assertEqual(wbs_type, "hierarchical")

    def test_required_documents(self):
        """Test required documents for electromechanical."""
        project_data = {
            "name": "Test Project",
            "typology": "Electromechanical"
        }

        typology = ElectromechanicalTypology(project_data)
        docs = typology.get_required_documents()

        self.assertIn("Material Submittals", docs)
        self.assertIn("Equipment Data Sheets", docs)
        self.assertIn("Testing Certificates", docs)


class TestCivilTypology(unittest.TestCase):
    """Test Civil typology."""

    def setUp(self):
        """Set up test environment."""
        frappe.set_user("Administrator")

    def test_is_civil(self):
        """Test Civil type detection."""
        project_data = {
            "name": "Test Project",
            "typology": "Civil"
        }

        typology = CivilTypology(project_data)

        self.assertTrue(typology.is_civil())

    def test_billing_method_is_ra(self):
        """Test Civil uses RA-Billing."""
        project_data = {
            "name": "Test Project",
            "typology": "Civil"
        }

        typology = CivilTypology(project_data)

        self.assertEqual(typology.get_billing_method(), "RA-Billing")

    def test_defect_liability_period(self):
        """Test defect liability period for civil works."""
        project_data = {
            "name": "Test Project",
            "typology": "Civil",
            "defect_liability_period": 24
        }

        typology = CivilTypology(project_data)

        self.assertEqual(typology.get_defect_liability_period(), 24)

    def test_concrete_compliance_required(self):
        """Test concrete compliance is required for civil."""
        project_data = {
            "name": "Test Project",
            "typology": "Civil"
        }

        typology = CivilTypology(project_data)

        self.assertTrue(typology.is_concrete_compliance_required())

    def test_retainage_rate(self):
        """Test retainage rate for civil works."""
        project_data = {
            "name": "Test Project",
            "typology": "Civil"
        }

        typology = CivilTypology(project_data)

        self.assertEqual(typology.get_retainage_rate(), 10)

    def test_wbs_structure_type(self):
        """Test WBS structure type for civil."""
        project_data = {
            "name": "Test Project",
            "typology": "Civil"
        }

        typology = CivilTypology(project_data)
        wbs_type = typology.get_wbs_structure_type()

        self.assertEqual(wbs_type, "cost_breakdown")


class TestStandardTypology(unittest.TestCase):
    """Test Standard/Service typology."""

    def setUp(self):
        """Set up test environment."""
        frappe.set_user("Administrator")

    def test_is_standard(self):
        """Test Standard type detection."""
        project_data = {
            "name": "Test Project",
            "typology": "Standard/Service"
        }

        typology = StandardTypology(project_data)

        self.assertTrue(typology.is_standard())

    def test_billing_method_is_milestone(self):
        """Test Standard uses Milestone-Billing."""
        project_data = {
            "name": "Test Project",
            "typology": "Standard/Service"
        }

        typology = StandardTypology(project_data)

        self.assertEqual(typology.get_billing_method(), "Milestone-Billing")

    def test_advance_not_applicable(self):
        """Test advance limit is 0 for standard service."""
        project_data = {
            "name": "Test Project",
            "typology": "Standard/Service"
        }

        typology = StandardTypology(project_data)

        self.assertEqual(typology.get_advance_limit_percentage(), 0)

    def test_measurement_methods(self):
        """Test measurement methods for standard."""
        project_data = {
            "name": "Test Project",
            "typology": "Standard/Service"
        }

        typology = StandardTypology(project_data)
        methods = typology.get_measurement_methods()

        self.assertIn("Milestone-Based", methods)
        self.assertIn("Percentage-Based", methods)

    def test_no_concrete_compliance(self):
        """Test concrete compliance not required for standard."""
        project_data = {
            "name": "Test Project",
            "typology": "Standard/Service"
        }

        typology = StandardTypology(project_data)

        self.assertFalse(typology.is_concrete_compliance_required())


class TestTypologyFactory(unittest.TestCase):
    """Test Typology factory."""

    def setUp(self):
        """Set up test environment."""
        frappe.set_user("Administrator")

    def test_create_electromechanical(self):
        """Test creating Electromechanical typology."""
        project_data = {
            "name": "Test Project",
            "typology": "Electromechanical"
        }

        typology = TypologyFactory.create(project_data)

        self.assertIsInstance(typology, ElectromechanicalTypology)

    def test_create_civil(self):
        """Test creating Civil typology."""
        project_data = {
            "name": "Test Project",
            "typology": "Civil"
        }

        typology = TypologyFactory.create(project_data)

        self.assertIsInstance(typology, CivilTypology)

    def test_create_standard(self):
        """Test creating Standard typology."""
        project_data = {
            "name": "Test Project",
            "typology": "Standard/Service"
        }

        typology = TypologyFactory.create(project_data)

        self.assertIsInstance(typology, StandardTypology)

    def test_create_invalid_raises(self):
        """Test creating invalid typology raises error."""
        project_data = {
            "name": "Test Project",
            "typology": "Invalid"
        }

        with self.assertRaises(ValueError):
            TypologyFactory.create(project_data)

    def test_get_all_typologies(self):
        """Test getting all available typologies."""
        typologies = TypologyFactory.get_all_typologies()

        self.assertIn("Electromechanical", typologies)
        self.assertIn("Civil", typologies)
        self.assertIn("Standard/Service", typologies)


class TestTypologyCalculations(unittest.TestCase):
    """Test typology-based calculations."""

    def setUp(self):
        """Set up test environment."""
        frappe.set_user("Administrator")

    def test_calculate_max_advance_electromechanical(self):
        """Test max advance calculation for electromechanical."""
        project_data = {
            "name": "Test Project",
            "typology": "Electromechanical",
            "total_contract_value": 50000000,
            "advance_rap_percentage": 20
        }

        typology = ElectromechanicalTypology(project_data)
        max_advance = typology.calculate_max_advance()

        # 20% of 50,000,000 = 10,000,000
        self.assertEqual(max_advance, 10000000)

    def test_calculate_max_advance_civil(self):
        """Test max advance calculation for civil."""
        project_data = {
            "name": "Test Project",
            "typology": "Civil",
            "total_contract_value": 25000000,
            "advance_rap_percentage": 20
        }

        typology = CivilTypology(project_data)
        max_advance = typology.calculate_max_advance()

        # 20% of 25,000,000 = 5,000,000
        self.assertEqual(max_advance, 5000000)

    def test_calculate_max_advance_standard(self):
        """Test max advance calculation for standard (0%)."""
        project_data = {
            "name": "Test Project",
            "typology": "Standard/Service",
            "total_contract_value": 10000000,
            "advance_rap_percentage": 0
        }

        typology = StandardTypology(project_data)
        max_advance = typology.calculate_max_advance()

        # 0% for standard service
        self.assertEqual(max_advance, 0)

    def test_calculate_final_recovery_civil(self):
        """Test final recovery calculation for civil."""
        project_data = {
            "name": "Test Project",
            "typology": "Civil",
            "total_contract_value": 10000000,
            "defect_liability_period": 12
        }

        typology = CivilTypology(project_data)

        # During defect liability: 100% recovery
        recovery_pct = typology.get_final_recovery_percentage()
        self.assertEqual(recovery_pct, 100)

    def test_get_boq_measurement_method_civil(self):
        """Test BOQ measurement methods for civil."""
        project_data = {
            "name": "Test Project",
            "typology": "Civil"
        }

        typology = CivilTypology(project_data)
        methods = typology.get_boq_measurement_methods()

        self.assertIn("Unit-Based", methods)
        self.assertIn("Percentage-Based", methods)

    def test_get_boq_measurement_method_electromechanical(self):
        """Test BOQ measurement methods for electromechanical."""
        project_data = {
            "name": "Test Project",
            "typology": "Electromechanical"
        }

        typology = ElectromechanicalTypology(project_data)
        methods = typology.get_boq_measurement_methods()

        self.assertIn("Unit-Based", methods)
        self.assertIn("Milestone-Based", methods)


if __name__ == "__main__":
    unittest.main()