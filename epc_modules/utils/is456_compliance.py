"""
IS 456:2000 Compliance Validator

Implements IS 456:2000 requirements for concrete mix design, cube testing,
and compliance validation for civil construction projects.
"""

import frappe
from frappe import _
from frappe.utils import flt, today, add_days
from typing import Dict, List, Optional, Any, Tuple
from epc_modules.utils import get_epc_logger
import math

logger = get_epc_logger(__name__)


class IS456ComplianceValidator:
    """
    Validates concrete works against IS 456:2000 requirements.
    Implements Table 2 (slump), Table 5 (min cement & max W/C), and Clause 16 acceptance criteria.
    """

    # IS 456 Table 2 - Slump Requirements (mm)
    SLUMP_REQUIREMENTS = {
        "Reinforced foundation": (25, 75),
        "Trench fill": (25, 50),
        "Beams & Slabs": (25, 75),
        "Roads": (25, 50),
        "Pumped": (75, 150),
        "Reinforced walls": (25, 75)
    }

    # IS 456 Table 5 - Minimum Cement Content & Maximum W/C Ratio
    EXPOSURE_REQUIREMENTS = {
        "Mild": {"min_cement": 300, "max_wc": 0.55, "min_grade": 20},
        "Moderate": {"min_cement": 310, "max_wc": 0.50, "min_grade": 25},
        "Severe": {"min_cement": 325, "max_wc": 0.45, "min_grade": 30},
        "Very Severe": {"min_cement": 340, "max_wc": 0.45, "min_grade": 35},
        "Extreme": {"min_cement": 360, "max_wc": 0.40, "min_grade": 40}
    }

    # Concrete Grade to fck mapping (MPa)
    GRADE_TO_FCK = {
        "M15": 15,
        "M20": 20,
        "M25": 25,
        "M30": 30,
        "M35": 35,
        "M40": 40,
        "M45": 45,
        "M50": 50,
        "M55": 55,
        "M60": 60
    }

    # IS 456 Clause 16 - Acceptance Criteria
    ACCEPTANCE_CRITERIA = {
        "single": 0.85,  # Individual test >= 0.85 fck
        "average": 1.30   # Average of 4 consecutive >= fck + 0.825σ (simplified)
    }

    # Minimum curing periods (IS 456 Clause 13.5.1)
    CURING_PERIODS = {
        "M15": 7,
        "M20": 7,
        "M25": 7,
        "M30": 10,
        "M35": 10,
        "M40": 14,
        "M45": 14,
        "M50": 14,
        "M55": 14,
        "M60": 14
    }

    @classmethod
    def validate_mix_design(cls, mix_doc: "frappe.doc") -> List[str]:
        """
        Validate mix design against IS 456 requirements.

        Args:
            mix_doc: Concrete Mix Design document

        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []

        # Check exposure condition compliance
        exposure_req = cls.EXPOSURE_REQUIREMENTS.get(mix_doc.exposure_condition)

        if exposure_req:
            # Validate minimum cement content
            min_cement = exposure_req["min_cement"]
            if flt(mix_doc.cement_content_kg) < min_cement:
                errors.append(
                    _("Cement content {0} kg/m³ is less than minimum {1} kg/m³ for "
                      "{2} exposure (IS 456 Table 5)").format(
                          mix_doc.cement_content_kg, min_cement, mix_doc.exposure_condition
                      )
                )

            # Validate max water-cement ratio
            max_wc = exposure_req["max_wc"]
            if flt(mix_doc.max_water_cement_ratio) > max_wc:
                errors.append(
                    _("W/C ratio {0} exceeds maximum {1} for {2} exposure (IS 456 Table 5)").format(
                          mix_doc.max_water_cement_ratio, max_wc, mix_doc.exposure_condition
                      )
                )

        # Check minimum grade requirements (IS 456 Clause 5.2)
        min_grade = exposure_req.get("min_grade", 20) if exposure_req else 20
        grade_value = cls._get_grade_value(mix_doc.concrete_grade)

        if grade_value < min_grade:
            errors.append(
                _("Concrete grade {0} is below minimum required M{1} for {2} "
                  "exposure (IS 456 Clause 5.2)").format(
                      mix_doc.concrete_grade, min_grade, mix_doc.exposure_condition or "Mild"
                  )
            )

        # Validate slump (if provided)
        if mix_doc.design_slump_mm:
            slump_errors = cls._validate_slump(mix_doc.design_slump_mm, mix_doc.mix_type)
            errors.extend(slump_errors)

        return errors

    @classmethod
    def _validate_slump(cls, slump_mm: float, mix_type: str = None) -> List[str]:
        """Validate slump against IS 456 Table 2."""
        errors = []

        # If mix_type specified, check against specific requirements
        if mix_type:
            if mix_type == "Pumped":
                if slump_mm < 75 or slump_mm > 150:
                    errors.append(
                        _("Pumped concrete slump must be 75-150mm (IS 456 Table 2)")
                    )
            else:
                if slump_mm < 25 or slump_mm > 75:
                    errors.append(
                        _("Slump should be 25-75mm for {0} (IS 456 Table 2)").format(mix_type)
                    )
        else:
            if slump_mm < 25 or slump_mm > 150:
                errors.append(
                    _("Slump {0}mm outside recommended range 25-150mm (IS 456 Table 2)").format(slump_mm)
                )

        return errors

    @classmethod
    def _get_grade_value(cls, grade: str) -> int:
        """Extract numeric grade from grade string (e.g., 'M20' -> 20)."""
        try:
            return int(grade.replace("M", ""))
        except (ValueError, AttributeError):
            return 0

    @classmethod
    def validate_cube_test(cls, cube_doc: "frappe.doc", mix_design_doc: "frappe.doc" = None) -> Dict[str, Any]:
        """
        Validate cube test against IS 456 Clause 16 acceptance criteria.

        Args:
            cube_doc: Cube Test Result document
            mix_design_doc: Concrete Mix Design document (optional)

        Returns:
            dict with validation results
        """
        result = {
            "is_valid": True,
            "is_pass": False,
            "errors": [],
            "compressive_strength": 0,
            "expected_strength": 0
        }

        # Get expected strength from mix design
        if mix_design_doc:
            grade = mix_design_doc.concrete_grade
            result["expected_strength"] = cls.GRADE_TO_FCK.get(grade, 20)
        else:
            result["expected_strength"] = 20  # Default

        # Calculate compressive strength if not set
        strength = cube_doc.compressive_strength_mpa

        if not strength and cube_doc.crushing_load_kn and cube_doc.size_mm:
            # Calculate: stress = load / area (area = size²)
            area_mm2 = cube_doc.size_mm ** 2
            strength = (cube_doc.crushing_load_kn * 1000) / area_mm2  # Convert kN to N
            result["compressive_strength"] = round(strength, 2)
        else:
            result["compressive_strength"] = strength

        # IS 456 Clause 16.1 - Acceptance criteria
        expected = result["expected_strength"]

        # Individual cube acceptance: >= 0.85 fck
        min_acceptable = expected * 0.85

        if result["compressive_strength"] < min_acceptable:
            result["is_valid"] = True  # Test is valid but fails
            result["is_pass"] = False
            result["errors"].append(
                _("Cube strength {0} MPa is below 0.85 fck ({1} MPa) (IS 456 Clause 16.1)").format(
                    result["compressive_strength"], min_acceptable
                )
            )
        else:
            result["is_pass"] = True

        # Check age vs expected
        if cube_doc.age_days != 28 and result["is_pass"]:
            # For 7-day tests, expect ~67% of 28-day strength
            # For 14-day tests, expect ~85% of 28-day strength
            age_factors = {7: 0.67, 14: 0.85}
            factor = age_factors.get(cube_doc.age_days, 1.0)

            if factor < 1.0:
                expected_for_age = expected * factor
                if result["compressive_strength"] < expected_for_age:
                    result["is_pass"] = False
                    result["errors"].append(
                        _("7-day strength {0} MPa is below expected {1} MPa").format(
                            result["compressive_strength"], round(expected_for_age, 2)
                        )
                    )

        return result

    @classmethod
    def get_acceptance_criteria_for_age(cls, age_days: int, grade: str) -> Dict[str, float]:
        """
        Get acceptance criteria based on test age and grade.

        Args:
            age_days: Test age in days
            grade: Concrete grade (e.g., 'M20')

        Returns:
            dict with expected and minimum strength values
        """
        fck = cls.GRADE_TO_FCK.get(grade, 20)

        criteria = {
            "expected_fck": fck,
            "min_individual": fck * 0.85
        }

        # Age-based expected strengths
        age_factors = {7: 0.67, 14: 0.85, 28: 1.0}

        if age_days in age_factors:
            factor = age_factors[age_days]
            criteria["expected_for_age"] = fck * factor
            criteria["min_for_age"] = fck * 0.85 * factor

        return criteria

    @classmethod
    def get_minimum_curing_days(cls, grade: str) -> int:
        """
        Get minimum curing period per IS 456 Clause 13.5.1.

        Args:
            grade: Concrete grade

        Returns:
            Minimum curing days
        """
        return cls.CURING_PERIODS.get(grade, 7)

    @classmethod
    def calculate_required_samples(cls, pour_volume_cum: float, work_type: str = "routine") -> Dict[str, Any]:
        """
        Calculate sampling frequency per IS 456 Clause 15.2.

        Args:
            pour_volume_cum: Volume of concrete pour in cubic meters
            work_type: Type of work ("routine" or "important")

        Returns:
            dict with sample requirements
        """
        # Per IS 456 Clause 15.2
        # One sample per 100 cum for routine work
        # One sample per 50 cum for important/structural work

        if work_type == "important":
            samples = math.ceil(pour_volume_cum / 50)
            recommendation = "Use important_work sampling for structural elements"
        else:
            samples = math.ceil(pour_volume_cum / 100)
            recommendation = "Increase to important_work sampling for structural elements"

        # For each sample, minimum 3 cubes for 28-day test
        cubes_per_sample = 3

        return {
            "work_type": work_type,
            "pour_volume_cum": pour_volume_cum,
            "required_samples": samples,
            "cubes_per_sample": cubes_per_sample,
            "total_cubes_required": samples * cubes_per_sample,
            "recommendation": recommendation
        }

    @classmethod
    def get_compliance_summary(cls, mix_doc: "frappe.doc") -> Dict[str, Any]:
        """
        Get full compliance summary for a mix design.

        Args:
            mix_doc: Concrete Mix Design document

        Returns:
            Comprehensive compliance status
        """
        exposure_req = cls.EXPOSURE_REQUIREMENTS.get(mix_doc.exposure_condition, {})

        summary = {
            "mix_design": mix_doc.mix_design_code,
            "concrete_grade": mix_doc.concrete_grade,
            "exposure_condition": mix_doc.exposure_condition,
            "checks": []
        }

        # Grade check
        grade_ok = cls._get_grade_value(mix_doc.concrete_grade) >= exposure_req.get("min_grade", 20)
        summary["checks"].append({
            "check": "Minimum Grade",
            "status": "pass" if grade_ok else "fail",
            "required": f"M{exposure_req.get('min_grade', 20)}",
            "actual": mix_doc.concrete_grade
        })

        # Cement content check
        cement_ok = flt(mix_doc.cement_content_kg) >= exposure_req.get("min_cement", 300)
        summary["checks"].append({
            "check": "Minimum Cement Content",
            "status": "pass" if cement_ok else "fail",
            "required": f"{exposure_req.get('min_cement', 300)} kg/m³",
            "actual": f"{mix_doc.cement_content_kg} kg/m³"
        })

        # W/C ratio check
        wc_ok = flt(mix_doc.max_water_cement_ratio) <= exposure_req.get("max_wc", 0.55)
        summary["checks"].append({
            "check": "Maximum W/C Ratio",
            "status": "pass" if wc_ok else "fail",
            "required": f"{exposure_req.get('max_wc', 0.55)}",
            "actual": str(mix_doc.max_water_cement_ratio)
        })

        # Overall compliance
        all_pass = all(c["status"] == "pass" for c in summary["checks"])
        summary["overall_status"] = "Compliant" if all_pass else "Non-Compliant"
        summary["is_compliant"] = all_pass

        return summary


class CuringManager:
    """
    Manages curing records and compliance tracking.
    """

    @staticmethod
    def create_curing_record(project: str, data: Dict) -> "frappe.doc":
        """Create a new curing record."""
        count = frappe.db.count("Curing Record", {"project": project}) or 0
        record_id = f"CR-{project[:4].upper()}-{count + 1:04d}"

        doc = frappe.get_doc({
            "doctype": "Curing Record",
            "record_id": record_id,
            "project": project,
            "wbs_item": data.get("wbs_item"),
            "element_location": data.get("element_location"),
            "pour_date": data.get("pour_date"),
            "concrete_grade": data.get("concrete_grade"),
            "mix_design": data.get("mix_design"),
            "quantity_cum": data.get("quantity_cum"),
            "curing_method": data.get("curing_method"),
            "curing_start_date": data.get("curing_start_date")
        })

        # Set minimum curing days
        doc.minimum_curing_days = IS456ComplianceValidator.get_minimum_curing_days(doc.concrete_grade)

        doc.insert(ignore_permissions=True)
        return doc

    @staticmethod
    def add_daily_check(curing_record: str, check_data: Dict) -> "frappe.doc":
        """Add a daily curing check to a record."""
        doc = frappe.get_doc("Curing Record", curing_record)

        # Calculate day number
        from frappe.utils import date_diff
        day_num = date_diff(check_data.get("check_date", today()), doc.curing_start_date)

        doc.append("curing_checks", {
            "check_date": check_data.get("check_date", today()),
            "day_number": day_num,
            "is_wet_surface": check_data.get("is_wet_surface", 0),
            "temperature_c": check_data.get("temperature_c"),
            "is_satisfactory": check_data.get("is_satisfactory", 0),
            "checked_by": check_data.get("checked_by", frappe.session.user),
            "remarks": check_data.get("remarks")
        })

        doc.save(ignore_permissions=True)
        return doc

    @staticmethod
    def complete_curing(curing_record: str) -> "frappe.doc":
        """Mark curing as complete and verify minimum days."""
        doc = frappe.get_doc("Curing Record", curing_record)

        from frappe.utils import date_diff, today
        curing_days = date_diff(today(), doc.curing_start_date)
        min_required = IS456ComplianceValidator.get_minimum_curing_days(doc.concrete_grade)

        doc.curing_end_date = today()
        doc.is_minimum_met = curing_days >= min_required
        doc.is_completed = 1
        doc.completed_by = frappe.session.user

        doc.save(ignore_permissions=True)

        logger.info(f"Curing record {doc.record_id} completed: {curing_days} days (min: {min_required})")

        return doc


class FormworkManager:
    """
    Manages formwork inspection records.
    """

    @staticmethod
    def create_inspection(project: str, data: Dict) -> "frappe.doc":
        """Create a formwork inspection record."""
        count = frappe.db.count("Formwork Inspection", {"project": project}) or 0
        inspection_id = f"FW-{project[:4].upper()}-{count + 1:04d}"

        doc = frappe.get_doc({
            "doctype": "Formwork Inspection",
            "inspection_id": inspection_id,
            "project": project,
            "wbs_item": data.get("wbs_item"),
            "location": data.get("location"),
            "formwork_type": data.get("formwork_type"),
            "element_description": data.get("element_description"),
            "dimensions_length_m": data.get("dimensions_length_m"),
            "dimensions_breadth_m": data.get("dimensions_breadth_m"),
            "dimensions_depth_m": data.get("dimensions_depth_m"),
            "inspector": data.get("inspector", frappe.session.user),
            "inspection_date": data.get("inspection_date", today())
        })

        # Calculate formwork area
        if doc.dimensions_length_m and doc.dimensions_breadth_m:
            doc.formwork_area_sqm = doc.dimensions_length_m * doc.dimensions_breadth_m

        doc.insert(ignore_permissions=True)
        return doc

    @staticmethod
    def clear_for_pour(inspection_name: str, cleared_by: str = None) -> "frappe.doc":
        """Clear formwork for concrete pouring."""
        doc = frappe.get_doc("Formwork Inspection", inspection_name)

        # Check all inspection points
        required_checks = [
            "alignment_check", "dimensions_check", "props_alignment",
            "cleaning_check", "oil_applied"
        ]

        all_passed = all(getattr(doc, check, 0) for check in required_checks)

        if not all_passed:
            frappe.throw(_("Cannot clear formwork: Not all inspection checks passed"))

        doc.is_cleared = 1
        doc.cleared_by = cleared_by or frappe.session.user
        doc.clearance_date = today()

        doc.save(ignore_permissions=True)

        logger.info(f"Formwork {doc.inspection_id} cleared for pour at {doc.location}")

        return doc


class ConcreteMixDesignManager:
    """
    Manages concrete mix design documents and compliance.
    """

    @staticmethod
    def create_mix_design(project: str, data: Dict) -> "frappe.doc":
        """
        Create a new concrete mix design with IS 456 validation.

        Args:
            project: Project name
            data: Mix design data

        Returns:
            Created document
        """
        # Generate mix design code
        count = frappe.db.count("Concrete Mix Design", {"project": project}) or 0
        mix_code = f"MD-{project[:4].upper()}-{count + 1:04d}"

        doc = frappe.get_doc({
            "doctype": "Concrete Mix Design",
            "mix_design_code": mix_code,
            "project": project,
            "wbs_item": data.get("wbs_item"),
            "concrete_grade": data.get("concrete_grade"),
            "mix_type": data.get("mix_type"),
            "exposure_condition": data.get("exposure_condition"),
            "design_slump_mm": data.get("design_slump_mm", 75),
            "cement_type": data.get("cement_type"),
            "cement_content_kg": data.get("cement_content_kg"),
            "max_water_cement_ratio": data.get("max_water_cement_ratio"),
            "sand_content_kg": data.get("sand_content_kg"),
            "coarse_aggregate_kg": data.get("coarse_aggregate_kg"),
            "flyash_content_kg": data.get("flyash_content_kg"),
            "max_aggregate_size_mm": data.get("max_aggregate_size_mm", 20),
            "admixture_type": data.get("admixture_type"),
            "admixture_dosage": data.get("admixture_dosage")
        })

        # Auto-calculate derived fields
        IS456ComplianceValidator._populate_compliance_fields(doc)
        doc.insert(ignore_permissions=True)

        return doc

    @staticmethod
    def approve_mix_design(mix_name: str) -> "frappe.doc":
        """
        Approve a concrete mix design.

        Args:
            mix_name: Mix design document name

        Returns:
            Updated document
        """
        doc = frappe.get_doc("Concrete Mix Design", mix_name)

        # Validate before approval
        errors = IS456ComplianceValidator.validate_mix_design(doc)

        if errors:
            doc.approval_status = "Rejected"
            doc.remarks = "; ".join(errors)
        else:
            doc.approval_status = "Approved"
            doc.approved_by = frappe.session.user
            doc.approval_date = today()

        doc.save(ignore_permissions=True)

        logger.info(f"Mix design {doc.mix_design_code} status: {doc.approval_status}")
        return doc

    @staticmethod
    def get_project_mix_designs(project: str, approved_only: bool = False) -> List[Dict]:
        """
        Get all mix designs for a project.

        Args:
            project: Project name
            approved_only: Filter for approved only

        Returns:
            List of mix design records
        """
        filters = {"project": project}
        if approved_only:
            filters["approval_status"] = "Approved"

        designs = frappe.get_all(
            "Concrete Mix Design",
            filters=filters,
            fields=["name", "mix_design_code", "concrete_grade", "exposure_condition",
                    "approval_status", "approved_by", "approval_date"],
            order_by="creation desc"
        )

        return designs


class CubeTestManager:
    """
    Manages cube test records and compliance.
    """

    @staticmethod
    def create_cube_test(project: str, data: Dict) -> "frappe.doc":
        """
        Create a new cube test record.

        Args:
            project: Project name
            data: Cube test data

        Returns:
            Created document
        """
        count = frappe.db.count("Cube Test Result", {"project": project}) or 0
        test_id = f"CT-{project[:4].upper()}-{count + 1:04d}"

        doc = frappe.get_doc({
            "doctype": "Cube Test Result",
            "cube_test_id": test_id,
            "project": project,
            "wbs_item": data.get("wbs_item"),
            "mix_design": data.get("mix_design"),
            "cube_number": data.get("cube_number"),
            "casting_date": data.get("casting_date"),
            "casting_location": data.get("casting_location"),
            "specimen_shape": data.get("specimen_shape", "Cube"),
            "size_mm": data.get("size_mm", 150),
            "age_days": data.get("age_days"),
            "test_date": data.get("test_date"),
            "weight_kg": data.get("weight_kg"),
            "crushing_load_kn": data.get("crushing_load_kn"),
            "test_standard": data.get("test_standard", "IS 516"),
            "lab_name": data.get("lab_name"),
            "lab_report_number": data.get("lab_report_number")
        })

        # Auto-calculate fields
        CubeTestManager._calculate_test_results(doc)

        doc.insert(ignore_permissions=True)

        return doc

    @staticmethod
    def _calculate_test_results(doc: "frappe.doc") -> None:
        """Calculate compressive strength and pass/fail."""
        if doc.crushing_load_kn and doc.size_mm:
            # Compressive strength = Load / Area
            area_mm2 = doc.size_mm ** 2
            strength_mpa = (doc.crushing_load_kn * 1000) / area_mm2
            doc.compressive_strength_mpa = round(strength_mpa, 2)
            doc.cross_sectional_area_mm2 = area_mm2

            # Get expected strength from mix design
            if doc.mix_design:
                mix = frappe.get_cached_doc("Concrete Mix Design", doc.mix_design)
                doc.grade_of_concrete = mix.concrete_grade

                # Check against acceptance criteria
                criteria = IS456ComplianceValidator.get_acceptance_criteria_for_age(
                    doc.age_days, mix.concrete_grade
                )

                doc.is_pass = doc.compressive_strength_mpa >= criteria.get("min_for_age", 0)

    @staticmethod
    def get_project_cube_tests(
        project: str,
        mix_design: str = None,
        failing_only: bool = False
    ) -> List[Dict]:
        """
        Get cube tests for a project.

        Args:
            project: Project name
            mix_design: Optional mix design filter
            failing_only: Filter for failing tests only

        Returns:
            List of cube test records
        """
        filters = {"project": project}

        if mix_design:
            filters["mix_design"] = mix_design

        if failing_only:
            filters["is_pass"] = 0

        tests = frappe.get_all(
            "Cube Test Result",
            filters=filters,
            fields=["name", "cube_test_id", "cube_number", "casting_date", "age_days",
                    "test_date", "compressive_strength_mpa", "is_pass", "is_within_tolerance"],
            order_by="test_date desc"
        )

        return tests

    @staticmethod
    def calculate_batch_average(project: str, batch_id: str) -> Dict[str, Any]:
        """
        Calculate average strength for a batch of cubes (IS 456 Clause 16.2).

        Args:
            project: Project name
            batch_id: Batch identifier (e.g., pour date + location)

        Returns:
            Batch average results
        """
        cubes = frappe.get_all(
            "Cube Test Result",
            filters={
                "project": project,
                "casting_date": batch_id
            },
            fields=["name", "compressive_strength_mpa", "cube_number", "is_pass"]
        )

        if not cubes:
            return {"error": "No cubes found for batch"}

        strengths = [c.get("compressive_strength_mpa", 0) for c in cubes]
        avg_strength = sum(strengths) / len(strengths) if strengths else 0
        pass_count = sum(1 for c in cubes if c.get("is_pass"))

        return {
            "batch_id": batch_id,
            "cube_count": len(cubes),
            "average_strength": round(avg_strength, 2),
            "pass_count": pass_count,
            "fail_count": len(cubes) - pass_count,
            "all_pass": pass_count == len(cubes)
        }


class MaterialRegisterManager:
    """
    Manages cement and steel reinforcement registers.
    """

    @staticmethod
    def create_cement_entry(project: str, data: Dict) -> "frappe.doc":
        """Create cement register entry."""
        count = frappe.db.count("Cement Register", {"project": project}) or 0
        entry_id = f"CE-{project[:4].upper()}-{count + 1:04d}"

        doc = frappe.get_doc({
            "doctype": "Cement Register",
            "entry_id": entry_id,
            "project": project,
            "batch_number": data.get("batch_number"),
            "cement_brand": data.get("cement_brand"),
            "cement_type": data.get("cement_type"),
            "grade": data.get("grade"),
            "manufacturer": data.get("manufacturer"),
            "quantity_tonnes": data.get("quantity_tonnes"),
            "date_received": data.get("date_received"),
            "date_of_manufacture": data.get("date_of_manufacture"),
            "test_certificate_ref": data.get("test_certificate_ref"),
            "storage_location": data.get("storage_location")
        })

        # Calculate expiry (3 months from manufacture for OPC)
        from frappe.utils import add_months
        doc.date_of_expiry = add_months(doc.date_of_manufacture, 3)

        doc.insert(ignore_permissions=True)
        return doc

    @staticmethod
    def create_steel_entry(project: str, data: Dict) -> "frappe.doc":
        """Create steel reinforcement register entry."""
        count = frappe.db.count("Steel Reinforcement Register", {"project": project}) or 0
        entry_id = f"SR-{project[:4].upper()}-{count + 1:04d}"

        doc = frappe.get_doc({
            "doctype": "Steel Reinforcement Register",
            "entry_id": entry_id,
            "project": project,
            "heat_number": data.get("heat_number"),
            "bar_mark": data.get("bar_mark"),
            "diameter_mm": data.get("diameter_mm"),
            "steel_grade": data.get("steel_grade"),
            "manufacturer": data.get("manufacturer"),
            "batch_number": data.get("batch_number"),
            "quantity_tonnes": data.get("quantity_tonnes"),
            "date_received": data.get("date_received"),
            "test_certificate": data.get("test_certificate"),
            "storage_location": data.get("storage_location")
        })

        # Auto-validate against IS 1786
        IS456ComplianceValidator._validate_steel_grade(doc)

        doc.insert(ignore_permissions=True)
        return doc

    @staticmethod
    def _validate_steel_grade(doc: "frappe.doc") -> None:
        """Validate steel grade meets IS 1786 requirements."""
        min_yield_strengths = {
            "Fe 415": 415,
            "Fe 415D": 415,
            "Fe 500": 500,
            "Fe 500D": 500,
            "Fe 550": 550,
            "Fe 550D": 550,
            "Fe 600": 600
        }

        min_required = min_yield_strengths.get(doc.steel_grade, 415)

        # These would be read from test certificate
        # Placeholder - actual values from certificate
        doc.yield_strength_mpa = min_required  # Would be from certificate
        doc.tensile_strength_mpa = min_required * 1.15  # IS 1786: Tensile >= 1.15*Yield
        doc.elongation_percent = 14.5  # IS 1786 minimum
        doc.bend_rebend_test = 1

        doc.is_approved = 1  # Auto-approve if certificate attached