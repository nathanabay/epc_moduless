"""
IS 456 Concrete Compliance API

REST API endpoints for IS 456:2000 concrete compliance operations.
"""

import frappe
from frappe import _
from frappe.utils import today, add_days, add_months, date_diff
from epc_modules.utils import get_epc_logger
from epc_modules.utils.is456_compliance import (
    IS456ComplianceValidator,
    ConcreteMixDesignManager,
    CubeTestManager,
    MaterialRegisterManager,
    CuringManager,
    FormworkManager
)

logger = get_epc_logger(__name__)


@frappe.whitelist()
def create_concrete_mix_design(project, data):
    """
    Create a new concrete mix design.

    Args:
        project (str): Project name
        data (dict): Mix design data

    Returns:
        dict: Created mix design info
    """
    frappe.has_permission("Concrete Mix Design", "create", throw=True)

    if not frappe.db.exists("Project", project):
        frappe.throw(_("Project {0} does not exist").format(project))

    mix = ConcreteMixDesignManager.create_mix_design(project, data)

    return {
        "name": mix.name,
        "mix_design_code": mix.mix_design_code,
        "concrete_grade": mix.concrete_grade,
        "approval_status": mix.approval_status
    }


@frappe.whitelist()
def get_project_mix_designs(project, approved_only=0):
    """
    Get all mix designs for a project.

    Args:
        project (str): Project name
        approved_only (int): Filter approved only

    Returns:
        list: Mix designs
    """
    if not project:
        frappe.throw(_("Project is required"))

    if not frappe.db.exists("Project", project):
        frappe.throw(_("Project {0} does not exist").format(project))

    frappe.has_permission("Project", "read", project, throw=True)

    return ConcreteMixDesignManager.get_project_mix_designs(project, bool(approved_only))


@frappe.whitelist()
def get_mix_design_details(mix_name):
    """
    Get detailed mix design.

    Args:
        mix_name (str): Mix design name

    Returns:
        dict: Mix design details
    """
    if not mix_name:
        frappe.throw(_("Mix design name is required"))

    if not frappe.db.exists("Concrete Mix Design", mix_name):
        frappe.throw(_("Mix Design {0} does not exist").format(mix_name))

    frappe.has_permission("Concrete Mix Design", "read", mix_name, throw=True)

    doc = frappe.get_doc("Concrete Mix Design", mix_name)

    return {
        "name": doc.name,
        "mix_design_code": doc.mix_design_code,
        "project": doc.project,
        "wbs_item": doc.wbs_item,
        "concrete_grade": doc.concrete_grade,
        "mix_type": doc.mix_type,
        "exposure_condition": doc.exposure_condition,
        "design_slump_mm": doc.design_slump_mm,
        "cement_type": doc.cement_type,
        "cement_content_kg": doc.cement_content_kg,
        "max_water_cement_ratio": doc.max_water_cement_ratio,
        "flyash_content_kg": doc.flyash_content_kg,
        "sand_content_kg": doc.sand_content_kg,
        "coarse_aggregate_kg": doc.coarse_aggregate_kg,
        "max_aggregate_size_mm": doc.max_aggregate_size_mm,
        "admixture_type": doc.admixture_type,
        "admixture_dosage": doc.admixture_dosage,
        "min_cement_content_kg": doc.min_cement_content_kg,
        "design_compressive_strength_mpa": doc.design_compressive_strength_mpa,
        "approval_status": doc.approval_status,
        "approved_by": doc.approved_by,
        "approval_date": doc.approval_date,
        "validity_period_months": doc.validity_period_months
    }


@frappe.whitelist()
def validate_mix_design(mix_name):
    """
    Validate a mix design against IS 456 requirements.

    Args:
        mix_name (str): Mix design name

    Returns:
        dict: Validation result
    """
    if not mix_name:
        frappe.throw(_("Mix design name is required"))

    if not frappe.db.exists("Concrete Mix Design", mix_name):
        frappe.throw(_("Mix Design {0} does not exist").format(mix_name))

    frappe.has_permission("Concrete Mix Design", "read", mix_name, throw=True)

    doc = frappe.get_doc("Concrete Mix Design", mix_name)
    errors = IS456ComplianceValidator.validate_mix_design(doc)

    return {
        "mix_design": mix_name,
        "is_valid": len(errors) == 0,
        "errors": errors,
        "grade": doc.concrete_grade,
        "exposure": doc.exposure_condition
    }


@frappe.whitelist()
def approve_mix_design(mix_name):
    """
    Approve a mix design.

    Args:
        mix_name (str): Mix design name

    Returns:
        dict: Approval result
    """
    if not mix_name:
        frappe.throw(_("Mix design name is required"))

    if not frappe.db.exists("Concrete Mix Design", mix_name):
        frappe.throw(_("Mix Design {0} does not exist").format(mix_name))

    frappe.has_permission("Concrete Mix Design", "write", mix_name, throw=True)

    doc = ConcreteMixDesignManager.approve_mix_design(mix_name)

    return {
        "name": doc.name,
        "approval_status": doc.approval_status,
        "approved_by": doc.approved_by,
        "approval_date": doc.approval_date
    }


@frappe.whitelist()
def create_cube_test(project, data):
    """
    Create a new cube test record.

    Args:
        project (str): Project name
        data (dict): Cube test data

    Returns:
        dict: Created test info
    """
    frappe.has_permission("Cube Test Result", "create", throw=True)

    if not frappe.db.exists("Project", project):
        frappe.throw(_("Project {0} does not exist").format(project))

    test = CubeTestManager.create_cube_test(project, data)

    return {
        "name": test.name,
        "cube_test_id": test.cube_test_id,
        "compressive_strength_mpa": test.compressive_strength_mpa,
        "is_pass": test.is_pass
    }


@frappe.whitelist()
def get_project_cube_tests(project, mix_design=None, failing_only=0):
    """
    Get cube tests for a project.

    Args:
        project (str): Project name
        mix_design (str, optional): Filter by mix design
        failing_only (int): Filter failing only

    Returns:
        list: Cube tests
    """
    if not project:
        frappe.throw(_("Project is required"))

    if not frappe.db.exists("Project", project):
        frappe.throw(_("Project {0} does not exist").format(project))

    frappe.has_permission("Project", "read", project, throw=True)

    return CubeTestManager.get_project_cube_tests(project, mix_design, bool(failing_only))


@frappe.whitelist()
def get_cube_test_details(test_name):
    """
    Get detailed cube test result.

    Args:
        test_name (str): Cube test name

    Returns:
        dict: Test details
    """
    if not test_name:
        frappe.throw(_("Test name is required"))

    if not frappe.db.exists("Cube Test Result", test_name):
        frappe.throw(_("Cube Test {0} does not exist").format(test_name))

    frappe.has_permission("Cube Test Result", "read", test_name, throw=True)

    doc = frappe.get_doc("Cube Test Result", test_name)

    return {
        "name": doc.name,
        "cube_test_id": doc.cube_test_id,
        "project": doc.project,
        "wbs_item": doc.wbs_item,
        "mix_design": doc.mix_design,
        "cube_number": doc.cube_number,
        "casting_date": doc.casting_date,
        "casting_location": doc.casting_location,
        "grade_of_concrete": doc.grade_of_concrete,
        "specimen_shape": doc.specimen_shape,
        "size_mm": doc.size_mm,
        "age_days": doc.age_days,
        "test_date": doc.test_date,
        "weight_kg": doc.weight_kg,
        "cross_sectional_area_mm2": doc.cross_sectional_area_mm2,
        "crushing_load_kn": doc.crushing_load_kn,
        "compressive_strength_mpa": doc.compressive_strength_mpa,
        "is_pass": doc.is_pass,
        "is_within_tolerance": doc.is_within_tolerance,
        "test_standard": doc.test_standard,
        "lab_name": doc.lab_name,
        "lab_report_number": doc.lab_report_number
    }


@frappe.whitelist()
def validate_cube_test(test_name):
    """
    Validate a cube test against IS 456 acceptance criteria.

    Args:
        test_name (str): Cube test name

    Returns:
        dict: Validation result
    """
    if not frappe.db.exists("Cube Test Result", test_name):
        frappe.throw(_("Cube Test {0} does not exist").format(test_name))

    frappe.has_permission("Cube Test Result", "read", test_name, throw=True)
    doc = frappe.get_doc("Cube Test Result", test_name)

    mix_doc = None
    if doc.mix_design:
        mix_doc = frappe.get_cached_doc("Concrete Mix Design", doc.mix_design)

    result = IS456ComplianceValidator.validate_cube_test(doc, mix_doc)

    return result


@frappe.whitelist()
def get_batch_average_strength(project, casting_date):
    """
    Calculate batch average strength.

    Args:
        project (str): Project name
        casting_date (str): Casting date (batch identifier)

    Returns:
        dict: Batch average results
    """
    frappe.has_permission("Cube Test Result", "read", throw=True)
    return CubeTestManager.calculate_batch_average(project, casting_date)


@frappe.whitelist()
def create_cement_entry(project, data):
    """
    Create cement register entry.

    Args:
        project (str): Project name
        data (dict): Cement entry data

    Returns:
        dict: Created entry info
    """
    frappe.has_permission("Cement Register", "create", throw=True)

    if not frappe.db.exists("Project", project):
        frappe.throw(_("Project {0} does not exist").format(project))

    entry = MaterialRegisterManager.create_cement_entry(project, data)

    return {
        "name": entry.name,
        "entry_id": entry.entry_id,
        "cement_brand": entry.cement_brand,
        "is_approved": entry.is_approved
    }


@frappe.whitelist()
def create_steel_entry(project, data):
    """
    Create steel reinforcement register entry.

    Args:
        project (str): Project name
        data (dict): Steel entry data

    Returns:
        dict: Created entry info
    """
    frappe.has_permission("Steel Reinforcement Register", "create", throw=True)

    if not frappe.db.exists("Project", project):
        frappe.throw(_("Project {0} does not exist").format(project))

    entry = MaterialRegisterManager.create_steel_entry(project, data)

    return {
        "name": entry.name,
        "entry_id": entry.entry_id,
        "steel_grade": entry.steel_grade,
        "is_approved": entry.is_approved
    }


@frappe.whitelist()
def get_project_material_registers(project, material_type=None):
    """
    Get material registers for a project.

    Args:
        project (str): Project name
        material_type (str): 'cement' or 'steel'

    Returns:
        list: Material entries
    """
    frappe.has_permission("Project", "read", project, throw=True)
    if material_type == "cement":
        doctype = "Cement Register"
    elif material_type == "steel":
        doctype = "Steel Reinforcement Register"
    else:
        return {"cement": get_cement_register(project), "steel": get_steel_register(project)}

    entries = frappe.get_list(
        doctype,
        filters={"project": project},
        fields=["name", "entry_id", "batch_number", "quantity_tonnes", "date_received", "is_approved", "is_used"]
    )

    return entries


@frappe.whitelist()
def get_cement_register(project):
    """Get cement register entries."""
    frappe.has_permission("Cement Register", "read", throw=True)
    return frappe.get_list(
        "Cement Register",
        filters={"project": project},
        fields=["name", "entry_id", "cement_brand", "cement_type", "quantity_tonnes", "date_received", "is_approved", "is_used"],
        order_by="date_received desc"
    )


@frappe.whitelist()
def get_steel_register(project):
    """Get steel reinforcement register entries."""
    frappe.has_permission("Steel Reinforcement Register", "read", throw=True)
    return frappe.get_list(
        "Steel Reinforcement Register",
        filters={"project": project},
        fields=["name", "entry_id", "heat_number", "bar_mark", "diameter_mm", "steel_grade", "quantity_tonnes", "date_received", "is_approved", "is_used"],
        order_by="date_received desc"
    )


@frappe.whitelist()
def get_minimum_curing_days(grade):
    """
    Get minimum curing period for a grade.

    Args:
        grade (str): Concrete grade (e.g., 'M20')

    Returns:
        dict: Minimum curing days
    """
    frappe.has_permission("Project", "read", throw=True)
    days = IS456ComplianceValidator.get_minimum_curing_days(grade)
    return {"grade": grade, "minimum_curing_days": days}


@frappe.whitelist()
def get_exposure_requirements(exposure):
    """
    Get IS 456 requirements for an exposure condition.

    Args:
        exposure (str): Exposure condition

    Returns:
        dict: Requirements
    """
    frappe.has_permission("Project", "read", throw=True)
    requirements = IS456ComplianceValidator.EXPOSURE_REQUIREMENTS.get(exposure, {})
    return {
        "exposure": exposure,
        "min_cement_kg": requirements.get("min_cement"),
        "max_wc_ratio": requirements.get("max_wc"),
        "min_grade": f"M{requirements.get('min_grade', 20)}" if requirements else None
    }


@frappe.whitelist()
def create_formwork_inspection(project, data):
    """
    Create formwork inspection record.

    Args:
        project (str): Project name
        data (dict): Inspection data

    Returns:
        dict: Created inspection info
    """
    frappe.has_permission("Formwork Inspection", "create", throw=True)

    if not frappe.db.exists("Project", project):
        frappe.throw(_("Project {0} does not exist").format(project))

    # Use naming series to avoid race conditions
    inspection_id = frappe.get_value("Namingseries", "FW-.#####", "current") or f"FW-{project[:4].upper()}-{frappe.generate_hash(length=8).upper()}"

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
        "alignment_check": data.get("alignment_check", 0),
        "dimensions_check": data.get("dimensions_check", 0),
        "props_alignment": data.get("props_alignment", 0),
        "cleaning_check": data.get("cleaning_check", 0),
        "oil_applied": data.get("oil_applied", 0),
        "reinforcement_check": data.get("reinforcement_check", 0),
        "cover_blocks_placed": data.get("cover_blocks_placed", 0),
        "inspector": data.get("inspector", frappe.session.user),
        "inspection_date": data.get("inspection_date", today()),
        "remarks": data.get("remarks")
    })

    # Auto-calculate formwork area
    if doc.dimensions_length_m and doc.dimensions_breadth_m:
        # Assuming simple rectangular area
        doc.formwork_area_sqm = doc.dimensions_length_m * doc.dimensions_breadth_m

    try:
        doc.insert()
    except Exception as e:
        frappe.log_error(
            title=_("Formwork Inspection Insert Failed"),
            message=f"Failed to insert Formwork Inspection for project {project}: {str(e)}"
        )
        frappe.throw(_("Failed to create Formwork Inspection. Please contact administrator."))

    return {
        "name": doc.name,
        "inspection_id": doc.inspection_id,
        "is_cleared": doc.is_cleared
    }


@frappe.whitelist()
def create_curing_record(project, data):
    """
    Create curing record.

    Args:
        project (str): Project name
        data (dict): Curing record data

    Returns:
        dict: Created record info
    """
    frappe.has_permission("Curing Record", "create", throw=True)

    if not frappe.db.exists("Project", project):
        frappe.throw(_("Project {0} does not exist").format(project))

    # Use naming series to avoid race conditions
    record_id = frappe.get_value("Namingseries", "CR-.#####", "current") or f"CR-{project[:4].upper()}-{frappe.generate_hash(length=8).upper()}"

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
        "curing_start_date": data.get("curing_start_date"),
        "daily_check_required": data.get("daily_check_required", 1)
    })

    # Auto-set minimum curing days per IS 456
    doc.minimum_curing_days = IS456ComplianceValidator.get_minimum_curing_days(doc.concrete_grade)

    # Calculate curing end date
    doc.curing_end_date = add_days(doc.curing_start_date, doc.minimum_curing_days)

    try:
        doc.insert()
    except Exception as e:
        frappe.log_error(
            title=_("Curing Record Insert Failed"),
            message=f"Failed to insert Curing Record for project {project}: {str(e)}"
        )
        frappe.throw(_("Failed to create Curing Record. Please contact administrator."))

    return {
        "name": doc.name,
        "record_id": doc.record_id,
        "minimum_curing_days": doc.minimum_curing_days,
        "curing_end_date": doc.curing_end_date
    }


@frappe.whitelist()
def add_curing_check(record_name, check_data):
    """
    Add a daily curing check.

    Args:
        record_name (str): Curing record name
        check_data (dict): Check data

    Returns:
        dict: Updated record info
    """
    frappe.has_permission("Curing Record", "write", record_name, throw=True)

    if not frappe.db.exists("Curing Record", record_name):
        frappe.throw(_("Curing Record {0} does not exist").format(record_name))

    doc = frappe.get_doc("Curing Record", record_name)

    # Calculate day number
    from frappe.utils import date_diff
    day_num = date_diff(check_data.get("check_date", today()), doc.curing_start_date) + 1

    doc.append("curing_checks", {
        "check_date": check_data.get("check_date", today()),
        "day_number": day_num,
        "is_wet_surface": check_data.get("is_wet_surface", 0),
        "temperature_c": check_data.get("temperature_c"),
        "is_satisfactory": check_data.get("is_satisfactory", 0),
        "checked_by": check_data.get("checked_by", frappe.session.user),
        "remarks": check_data.get("remarks")
    })

    # Check if minimum curing days met (before saving so it persists)
    passed_checks = [c for c in doc.curing_checks if c.is_satisfactory]
    if len(passed_checks) >= doc.minimum_curing_days:
        doc.is_minimum_met = 1

    try:
        doc.save()
    except Exception as e:
        frappe.log_error(
            title=_("Curing Check Save Failed"),
            message=f"Failed to save curing check for record {record_name}: {str(e)}"
        )
        frappe.throw(_("Failed to save curing check. Please contact administrator."))

    return {
        "name": doc.name,
        "day_number": day_num,
        "is_satisfactory": check_data.get("is_satisfactory", 0)
    }


@frappe.whitelist()
def get_concrete_compliance_summary(project):
    """
    Get comprehensive concrete compliance summary.

    Args:
        project (str): Project name

    Returns:
        dict: Summary
    """
    if not project:
        frappe.throw(_("Project is required"))

    if not frappe.db.exists("Project", project):
        frappe.throw(_("Project {0} does not exist").format(project))

    frappe.has_permission("Project", "read", project, throw=True)

    # Get mix designs
    mix_designs = frappe.get_list(
        "Concrete Mix Design",
        filters={"project": project},
        fields=["name", "concrete_grade", "approval_status"]
    )

    approved_mixes = [m for m in mix_designs if m.approval_status == "Approved"]
    pending_mixes = [m for m in mix_designs if m.approval_status == "Draft"]

    # Get cube tests
    cube_tests = frappe.get_list(
        "Cube Test Result",
        filters={"project": project},
        fields=["name", "is_pass", "compressive_strength_mpa", "age_days"]
    )

    passing_tests = [c for c in cube_tests if c.is_pass]
    failing_tests = [c for c in cube_tests if not c.is_pass]

    # Get material registers
    cement_entries = frappe.get_count("Cement Register", {"project": project})
    steel_entries = frappe.get_count("Steel Reinforcement Register", {"project": project})

    # Get formwork inspections
    formwork_cleared = frappe.get_count(
        "Formwork Inspection",
        {"project": project, "is_cleared": 1}
    )

    # Get curing records
    curing_records = frappe.get_list(
        "Curing Record",
        filters={"project": project},
        fields=["name", "is_minimum_met"]
    )

    completed_curing = [c for c in curing_records if c.is_minimum_met]

    return {
        "project": project,
        "mix_designs": {
            "total": len(mix_designs),
            "approved": len(approved_mixes),
            "pending": len(pending_mixes)
        },
        "cube_tests": {
            "total": len(cube_tests),
            "passing": len(passing_tests),
            "failing": len(failing_tests)
        },
        "materials": {
            "cement_entries": cement_entries,
            "steel_entries": steel_entries
        },
        "formwork": {
            "total_cleared": formwork_cleared
        },
        "curing": {
            "total_records": len(curing_records),
            "completed": len(completed_curing)
        },
        "compliance_status": "Compliant" if len(failing_tests) == 0 and len(approved_mixes) > 0 else "Pending Review"
    }


@frappe.whitelist()
def complete_curing(record_name):
    """
    Mark curing as complete and verify minimum days met.

    Args:
        record_name (str): Curing record name

    Returns:
        dict: Completion result
    """
    if not record_name:
        frappe.throw(_("Record name is required"))

    if not frappe.db.exists("Curing Record", record_name):
        frappe.throw(_("Curing Record {0} does not exist").format(record_name))

    frappe.has_permission("Curing Record", "write", record_name, throw=True)

    doc = CuringManager.complete_curing(record_name)

    return {
        "name": doc.name,
        "record_id": doc.record_id,
        "is_minimum_met": doc.is_minimum_met,
        "is_completed": doc.is_completed
    }


@frappe.whitelist()
def clear_formwork_for_pour(inspection_name, cleared_by=None):
    """
    Clear formwork for concrete pouring.

    Args:
        inspection_name (str): Formwork inspection name
        cleared_by (str, optional): User who cleared

    Returns:
        dict: Clearance result
    """
    if not inspection_name:
        frappe.throw(_("Inspection name is required"))

    if not frappe.db.exists("Formwork Inspection", inspection_name):
        frappe.throw(_("Formwork Inspection {0} does not exist").format(inspection_name))

    frappe.has_permission("Formwork Inspection", "write", inspection_name, throw=True)

    doc = FormworkManager.clear_for_pour(inspection_name, cleared_by)

    return {
        "name": doc.name,
        "inspection_id": doc.inspection_id,
        "is_cleared": doc.is_cleared,
        "clearance_date": doc.clearance_date
    }


@frappe.whitelist()
def get_sampling_requirements(pour_volume, work_type="routine"):
    """
    Get sampling requirements per IS 456 Clause 15.2.

    Args:
        pour_volume (float): Volume in cubic meters
        work_type (str): 'routine' or 'important'

    Returns:
        dict: Sampling requirements
    """
    return IS456ComplianceValidator.calculate_required_samples(pour_volume, work_type)


@frappe.whitelist()
def get_mix_design_compliance(mix_name):
    """
    Get full compliance summary for a mix design.

    Args:
        mix_name (str): Mix design name

    Returns:
        dict: Compliance summary
    """
    if not mix_name:
        frappe.throw(_("Mix design name is required"))

    if not frappe.db.exists("Concrete Mix Design", mix_name):
        frappe.throw(_("Mix Design {0} does not exist").format(mix_name))

    frappe.has_permission("Concrete Mix Design", "read", mix_name, throw=True)

    doc = frappe.get_doc("Concrete Mix Design", mix_name)
    return IS456ComplianceValidator.get_compliance_summary(doc)


@frappe.whitelist()
def get_mix_designs_for_grade(project, concrete_grade):
    """
    Get approved mix designs for a specific grade.

    Args:
        project (str): Project name
        concrete_grade (str): Concrete grade (e.g., 'M30')

    Returns:
        list: Approved mix designs
    """
    frappe.has_permission("Concrete Mix Design", "read", throw=True)
    return frappe.get_list(
        "Concrete Mix Design",
        filters={
            "project": project,
            "concrete_grade": concrete_grade,
            "approval_status": "Approved"
        },
        fields=["name", "mix_design_code", "exposure_condition", "approval_date"]
    )


@frappe.whitelist()
def get_concrete_strength_trend(project, days=90, limit=500):
    """
    Get concrete strength trend over time.

    Args:
        project (str): Project name
        days (int): Number of days to look back
        limit (int): Maximum records to return

    Returns:
        dict: Strength trend data
    """
    frappe.has_permission("Cube Test Result", "read", throw=True)

    if not frappe.db.exists("Project", project):
        frappe.throw(_("Project {0} does not exist").format(project))

    from frappe.utils import add_days as add_days_util

    cutoff_date = add_days_util(today(), -days)

    tests = frappe.get_list(
        "Cube Test Result",
        filters={
            "project": project,
            "test_date": [">=", cutoff_date]
        },
        fields=["name", "test_date", "compressive_strength_mpa", "is_pass", "grade_of_concrete", "mix_design"],
        order_by="test_date asc",
        limit_page_length=min(int(limit or 500), 500)
    )

    # Calculate moving averages
    trend_data = []
    cumulative = []
    count = 0

    for test in tests:
        count += 1
        cumulative.append(test.compressive_strength_mpa or 0)
        avg = sum(cumulative) / count

        trend_data.append({
            "date": test.test_date,
            "strength": test.compressive_strength_mpa,
            "grade": test.grade_of_concrete,
            "is_pass": test.is_pass,
            "moving_average": round(avg, 2)
        })

    return {
        "project": project,
        "period_days": days,
        "test_count": len(tests),
        "trend": trend_data
    }


@frappe.whitelist()
def get_formwork_inspections(project, status=None):
    """
    Get formwork inspections for a project.

    Args:
        project (str): Project name
        status (str, optional): Filter by status (cleared/pending)

    Returns:
        list: Formwork inspections
    """
    frappe.has_permission("Formwork Inspection", "read", throw=True)

    if not frappe.db.exists("Project", project):
        frappe.throw(_("Project {0} does not exist").format(project))

    filters = {"project": project}

    if status == "cleared":
        filters["is_cleared"] = 1
    elif status == "pending":
        filters["is_cleared"] = 0

    return frappe.get_list(
        "Formwork Inspection",
        filters=filters,
        fields=["name", "inspection_id", "location", "formwork_type",
                "inspector", "inspection_date", "is_cleared"],
        order_by="inspection_date desc"
    )


@frappe.whitelist()
def get_curing_records(project, include_checks=True):
    """
    Get curing records for a project.

    Args:
        project (str): Project name
        include_checks (bool): Include daily check details

    Returns:
        list: Curing records
    """
    frappe.has_permission("Curing Record", "read", throw=True)

    if not frappe.db.exists("Project", project):
        frappe.throw(_("Project {0} does not exist").format(project))

    records = frappe.get_list(
        "Curing Record",
        filters={"project": project},
        fields=["name", "record_id", "element_location", "concrete_grade",
                "curing_method", "pour_date", "curing_start_date",
                "curing_end_date", "is_minimum_met", "is_completed"],
        order_by="pour_date desc"
    )

    if include_checks and records:
        # Batch query all checks for all records to avoid N+1
        record_names = [r["name"] for r in records]
        all_checks = frappe.get_list(
            "Curing Check Entry",
            filters={"parent": ["in", record_names]},
            fields=["name", "parent", "check_date", "day_number", "is_satisfactory", "checked_by"],
            order_by="day_number asc"
        )
        # Map checks to records
        checks_map = {}
        for check in all_checks:
            checks_map.setdefault(check["parent"], []).append(check)
        for record in records:
            record["checks"] = checks_map.get(record["name"], [])

    return records