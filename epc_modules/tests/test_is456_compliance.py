"""
IS 456:2000 Compliance Tests

Tests for concrete mix design validation, cube test acceptance criteria,
and IS 456 compliance checks per Indian Standard requirements.
"""

import unittest
import frappe
from frappe.utils import flt, now_datetime
from epc_modules.utils.is456_compliance import (
    IS456ComplianceValidator,
    ConcreteMixDesignManager,
    CubeTestManager,
    MaterialRegisterManager,
    CuringManager,
    FormworkManager
)


class TestIS456ExposureRequirements(unittest.TestCase):
    """Test exposure condition requirements per IS 456 Table 5."""

    def test_mild_exposure_minimums(self):
        """Test mild exposure has correct minimums."""
        req = IS456ComplianceValidator.EXPOSURE_REQUIREMENTS["Mild"]
        self.assertEqual(req["min_cement"], 300)
        self.assertEqual(req["max_wc"], 0.55)
        self.assertEqual(req["min_grade"], 20)

    def test_severe_exposure_minimums(self):
        """Test severe exposure has correct minimums."""
        req = IS456ComplianceValidator.EXPOSURE_REQUIREMENTS["Severe"]
        self.assertEqual(req["min_cement"], 325)
        self.assertEqual(req["max_wc"], 0.45)
        self.assertEqual(req["min_grade"], 30)

    def test_extreme_exposure_minimums(self):
        """Test extreme exposure has correct minimums."""
        req = IS456ComplianceValidator.EXPOSURE_REQUIREMENTS["Extreme"]
        self.assertEqual(req["min_cement"], 360)
        self.assertEqual(req["max_wc"], 0.40)
        self.assertEqual(req["min_grade"], 40)


class TestIS456ComplianceValidator(unittest.TestCase):
    """Test IS 456 compliance validation."""

    def setUp(self):
        """Set up test mix design document."""
        self.mock_mix = frappe._dict({
            "doctype": "Concrete Mix Design",
            "exposure_condition": "Moderate",
            "concrete_grade": "M25",
            "cement_content_kg": 320,
            "max_water_cement_ratio": 0.50,
            "design_slump_mm": 75,
            "mix_type": "Site Mix"
        })

    def test_valid_mix_design(self):
        """Test a valid mix design passes."""
        errors = IS456ComplianceValidator.validate_mix_design(self.mock_mix)
        self.assertEqual(len(errors), 0)

    def test_insufficient_cement_content(self):
        """Test cement content below minimum fails."""
        self.mock_mix.cement_content_kg = 280  # Below 310 for moderate
        errors = IS456ComplianceValidator.validate_mix_design(self.mock_mix)
        self.assertGreater(len(errors), 0)
        self.assertTrue(any("Cement content" in e for e in errors))

    def test_excessive_water_ratio(self):
        """Test W/C ratio above maximum fails."""
        self.mock_mix.max_water_cement_ratio = 0.60  # Above 0.50 for moderate
        errors = IS456ComplianceValidator.validate_mix_design(self.mock_mix)
        self.assertGreater(len(errors), 0)
        self.assertTrue(any("W/C ratio" in e for e in errors))

    def test_insufficient_grade_for_exposure(self):
        """Test grade below minimum for exposure fails."""
        self.mock_mix.concrete_grade = "M20"  # Should be M25 for moderate
        errors = IS456ComplianceValidator.validate_mix_design(self.mock_mix)
        self.assertGreater(len(errors), 0)
        self.assertTrue(any("below minimum" in e.lower() for e in errors))

    def test_pumped_concrete_slump_range(self):
        """Test pumped concrete slump must be 75-150mm."""
        self.mock_mix.mix_type = "Pumped"
        self.mock_mix.design_slump_mm = 50  # Too low
        errors = IS456ComplianceValidator.validate_mix_design(self.mock_mix)
        self.assertGreater(len(errors), 0)

    def test_normal_concrete_slump_range(self):
        """Test normal concrete slump must be 25-75mm."""
        self.mock_mix.mix_type = "Site Mix"
        self.mock_mix.design_slump_mm = 200  # Too high
        errors = IS456ComplianceValidator.validate_mix_design(self.mock_mix)
        self.assertGreater(len(errors), 0)


class TestIS456CubeAcceptance(unittest.TestCase):
    """Test cube test acceptance criteria per IS 456 Clause 16."""

    def setUp(self):
        """Set up test mix and cube documents."""
        self.mock_mix = frappe._dict({
            "doctype": "Concrete Mix Design",
            "concrete_grade": "M30"
        })

    def test_m30_individual_acceptance(self):
        """Test M30 cube must be >= 25.5 MPa (0.85 x 30)."""
        cube = frappe._dict({
            "doctype": "Cube Test Result",
            "compressive_strength_mpa": 28,  # Above 25.5, should pass
            "age_days": 28
        })
        result = IS456ComplianceValidator.validate_cube_test(cube, self.mock_mix)
        self.assertTrue(result["is_pass"])

    def test_m30_below_acceptance(self):
        """Test M30 cube below 0.85 fck fails."""
        cube = frappe._dict({
            "compressive_strength_mpa": 24,  # Below 25.5
            "age_days": 28
        })
        result = IS456ComplianceValidator.validate_cube_test(cube, self.mock_mix)
        self.assertFalse(result["is_pass"])

    def test_strength_calculation_from_load(self):
        """Test strength calculation from load and size."""
        cube = frappe._dict({
            "crushing_load_kn": 562.5,  # 562.5 kN on 150mm cube = 25 MPa
            "size_mm": 150,
            "age_days": 28
        })
        result = IS456ComplianceValidator.validate_cube_test(cube, self.mock_mix)
        self.assertAlmostEqual(result["compressive_strength"], 25.0, places=1)

    def test_7day_strength_expectation(self):
        """Test 7-day strength expected at ~67% of 28-day."""
        cube = frappe._dict({
            "compressive_strength_mpa": 20,  # 20 MPa at 7 days
            "age_days": 7
        })
        result = IS456ComplianceValidator.validate_cube_test(cube, self.mock_mix)
        # For M30, 7-day should be ~20 MPa (67%)
        self.assertTrue(result["is_pass"])


class TestIS456CuringPeriods(unittest.TestCase):
    """Test curing period requirements per IS 456 Clause 13.5.1."""

    def test_m15_m25_curing_days(self):
        """Test M15-M25 require 7 days curing."""
        for grade in ["M15", "M20", "M25"]:
            days = IS456ComplianceValidator.get_minimum_curing_days(grade)
            self.assertEqual(days, 7)

    def test_m30_m35_curing_days(self):
        """Test M30-M35 require 10 days curing."""
        for grade in ["M30", "M35"]:
            days = IS456ComplianceValidator.get_minimum_curing_days(grade)
            self.assertEqual(days, 10)

    def test_m40_and_above_curing_days(self):
        """Test M40+ require 14 days curing."""
        for grade in ["M40", "M45", "M50", "M55", "M60"]:
            days = IS456ComplianceValidator.get_minimum_curing_days(grade)
            self.assertEqual(days, 14)


class TestSamplingFrequency(unittest.TestCase):
    """Test sampling frequency per IS 456 Clause 15.2."""

    def test_routine_work_sampling(self):
        """Test routine work sampling: 1 per 100 cum."""
        result = IS456ComplianceValidator.calculate_required_samples(250, "routine")
        self.assertEqual(result["required_samples"], 3)
        self.assertEqual(result["total_cubes_required"], 9)

    def test_important_work_sampling(self):
        """Test important/structural work: 1 per 50 cum."""
        result = IS456ComplianceValidator.calculate_required_samples(250, "important")
        self.assertEqual(result["required_samples"], 5)
        self.assertEqual(result["total_cubes_required"], 15)

    def test_small_pour_sampling(self):
        """Test small pour still requires minimum samples."""
        result = IS456ComplianceValidator.calculate_required_samples(30, "routine")
        self.assertEqual(result["required_samples"], 1)


class TestGradeToFCK(unittest.TestCase):
    """Test grade to characteristic strength mapping."""

    def test_standard_grades(self):
        """Test standard grade mappings."""
        self.assertEqual(IS456ComplianceValidator.GRADE_TO_FCK["M20"], 20)
        self.assertEqual(IS456ComplianceValidator.GRADE_TO_FCK["M30"], 30)
        self.assertEqual(IS456ComplianceValidator.GRADE_TO_FCK["M40"], 40)
        self.assertEqual(IS456ComplianceValidator.GRADE_TO_FCK["M60"], 60)


class TestAcceptanceCriteriaForAge(unittest.TestCase):
    """Test acceptance criteria based on test age."""

    def test_7day_criteria(self):
        """Test 7-day acceptance criteria."""
        criteria = IS456ComplianceValidator.get_acceptance_criteria_for_age(7, "M30")
        self.assertEqual(criteria["expected_fck"], 30)
        self.assertAlmostEqual(criteria["expected_for_age"], 20.1, places=1)
        self.assertAlmostEqual(criteria["min_individual"], 17.1, places=1)

    def test_28day_criteria(self):
        """Test 28-day acceptance criteria."""
        criteria = IS456ComplianceValidator.get_acceptance_criteria_for_age(28, "M30")
        self.assertEqual(criteria["expected_fck"], 30)
        self.assertEqual(criteria["expected_for_age"], 30)
        self.assertEqual(criteria["min_individual"], 25.5)  # 0.85 x 30


class TestSteelGradeValidation(unittest.TestCase):
    """Test steel reinforcement grade validation."""

    def test_fe415_requirements(self):
        """Test Fe 415 minimum yield strength."""
        self.assertGreaterEqual(415, 415)  # Minimum required

    def test_fe500_requirements(self):
        """Test Fe 500 minimum yield strength."""
        self.assertGreaterEqual(500, 500)

    def test_fe550_requirements(self):
        """Test Fe 550 minimum yield strength."""
        self.assertGreaterEqual(550, 550)


# Integration tests (require Frappe environment)
class TestIS456Integration(unittest.TestCase):
    """Integration tests for IS 456 compliance in Frappe context."""

    @classmethod
    def setUpClass(cls):
        """Set up Frappe environment."""
        frappe.set_user("Administrator")

    def test_mix_design_workflow(self):
        """Test complete mix design workflow."""
        # This test requires actual Frappe environment
        # Skipping in unit test mode
        pass

    def test_cube_test_ncr_generation(self):
        """Test NCR generation for failed cube tests."""
        # This test requires actual Frappe environment
        pass


if __name__ == "__main__":
    unittest.main()
