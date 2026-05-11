"""
EPC Module Tests

Main test runner for all EPC module tests.
"""

import frappe
import unittest

# Import all test modules
from epc_modules.tests import (
    test_boq_calculator,
    test_billing_calculator,
    test_typology_engine,
    test_wbs_generator,
    test_is456_compliance
)


class TestEPCHooks(unittest.TestCase):
    def setUp(self):
        frappe.set_user("Administrator")

    def test_project_created_hook(self):
        """Test on_project_created hook initialization."""
        # This would test the hook functionality
        # Requires actual Frappe environment
        pass

    def test_typology_validation(self):
        """Test validate_project_typology prevents invalid saves."""
        # This would test the validation logic
        pass


class TestEPCUtils(unittest.TestCase):
    def setUp(self):
        frappe.set_user("Administrator")

    def test_is_epc_project(self):
        """Test is_epc_project utility function."""
        # This would test the utility function
        # Requires actual Frappe environment
        pass

    def test_get_project_billing_track(self):
        """Test billing track determination."""
        # This would test the billing track logic
        pass

    def test_create_site_warehouse(self):
        """Test warehouse creation for civil projects."""
        # This would test warehouse creation
        pass


class TestEPCConstants(unittest.TestCase):
    def test_typology_choices(self):
        """Test typology constants are defined."""
        from epc_modules.utils.constants import (
            TYPOLOGY_ELECTROMECHANICAL,
            TYPOLOGY_CIVIL,
            TYPOLOGY_STANDARD_SERVICE
        )
        self.assertEqual(TYPOLOGY_ELECTROMECHANICAL, "Electromechanical")
        self.assertEqual(TYPOLOGY_CIVIL, "Civil")
        self.assertEqual(TYPOLOGY_STANDARD_SERVICE, "Standard/Service")

    def test_billing_tracks(self):
        """Test billing tracks mapping."""
        from epc_modules.utils.constants import BILLING_TRACKS
        self.assertEqual(BILLING_TRACKS["Civil"], "RA-Billing")
        self.assertEqual(BILLING_TRACKS["Standard/Service"], "Milestone-Billing")

    def test_concrete_grades(self):
        """Test concrete grades are defined."""
        from epc_modules.utils.constants import CONCRETE_GRADES
        self.assertIn("M20", CONCRETE_GRADES)
        self.assertIn("M30", CONCRETE_GRADES)
        self.assertIn("M60", CONCRETE_GRADES)


def create_test_suite():
    """Create a complete test suite for the EPC module."""
    suite = unittest.TestSuite()

    # Add all test modules
    loader = unittest.TestLoader()
    suite.addTests(loader.loadTestsFromModule(test_boq_calculator))
    suite.addTests(loader.loadTestsFromModule(test_billing_calculator))
    suite.addTests(loader.loadTestsFromModule(test_typology_engine))
    suite.addTests(loader.loadTestsFromModule(test_wbs_generator))
    suite.addTests(loader.loadTestsFromModule(test_is456_compliance))

    # Add local tests
    suite.addTests(loader.loadTestsFromTestCase(TestEPCHooks))
    suite.addTests(loader.loadTestsFromTestCase(TestEPCUtils))
    suite.addTests(loader.loadTestsFromTestCase(TestEPCConstants))

    return suite


if __name__ == "__main__":
    # Run all tests
    suite = create_test_suite()
    runner = unittest.TextTestRunner(verbosity=2)
    runner.run(suite)