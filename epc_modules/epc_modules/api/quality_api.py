"""
Quality Management API Module

REST API endpoints for quality management operations.
"""

import frappe
from frappe import _
from frappe.utils import today, now_datetime, add_days
from epc_modules.utils import get_epc_logger
from epc_modules.utils.quality_gate import (
    QualityTemplateCloner,
    NCRManager,
    ITPManager
)

logger = get_epc_logger(__name__)


@frappe.whitelist()
def get_inspection_templates(typology=None, category=None, is_active=1):
    """
    Get inspection templates with optional filters.

    Args:
        typology (str, optional): Filter by typology
        category (str, optional): Filter by category
        is_active (int): Active status filter

    Returns:
        list: Inspection templates
    """
    filters = {"is_active": is_active}

    if typology:
        filters["applicable_typologies"] = ["like", f"%{typology}%"]

    if category:
        filters["inspection_category"] = category

    templates = frappe.get_all(
        "Master Inspection Template",
        filters=filters,
        fields=["name", "template_name", "applicable_typologies", "inspection_category", "description"],
        order_by="template_name"
    )

    return templates


@frappe.whitelist()
def get_template_details(template_name):
    """
    Get detailed template with hold points.

    Args:
        template_name (str): Template name

    Returns:
        dict: Template details with hold points
    """
    if not frappe.db.exists("Master Inspection Template", template_name):
        frappe.throw(_("Template {0} does not exist").format(template_name))

    doc = frappe.get_doc("Master Inspection Template", template_name)

    return {
        "name": doc.name,
        "template_name": doc.template_name,
        "applicable_typologies": doc.applicable_typologies,
        "inspection_category": doc.inspection_category,
        "description": doc.description,
        "is_active": doc.is_active,
        "hold_points": [
            {
                "name": hp.name,
                "sequence": hp.sequence,
                "hold_point_name": hp.hold_point_name,
                "description": hp.description,
                "inspection_type": hp.inspection_type,
                "acceptance_criteria": hp.acceptance_criteria,
                "tolerance_min": hp.tolerance_min,
                "tolerance_max": hp.tolerance_max,
                "required_evidence": hp.required_evidence,
                "is_mandatory": hp.is_mandatory
            }
            for hp in doc.hold_points
        ]
    }


@frappe.whitelist()
def clone_templates_to_project(project):
    """
    Clone applicable templates to project as ITPs.

    Args:
        project (str): Project name

    Returns:
        dict: Cloning result
    """
    if not frappe.db.exists("Project", project):
        frappe.throw(_("Project {0} does not exist").format(project))

    count = QualityTemplateCloner.clone_templates_for_project(project)

    return {
        "project": project,
        "itps_created": count
    }


@frappe.whitelist()
def get_project_itps(project, status=None):
    """
    Get ITPs for a project.

    Args:
        project (str): Project name
        status (str, optional): Filter by status

    Returns:
        list: ITPs
    """
    if not frappe.db.exists("Project", project):
        frappe.throw(_("Project {0} does not exist").format(project))

    filters = {"project": project}
    if status:
        filters["status"] = status

    itps = frappe.get_all(
        "Project Inspection Plan",
        filters=filters,
        fields=["name", "itp_code", "source_template", "status", "total_hold_points", "progress_percentage"],
        order_by="creation desc"
    )

    return itps


@frappe.whitelist()
def get_itp_details(itp_name):
    """
    Get detailed ITP with inspection records.

    Args:
        itp_name (str): ITP name

    Returns:
        dict: ITP details
    """
    if not frappe.db.exists("Project Inspection Plan", itp_name):
        frappe.throw(_("ITP {0} does not exist").format(itp_name))

    doc = frappe.get_doc("Project Inspection Plan", itp_name)

    return {
        "name": doc.name,
        "project": doc.project,
        "itp_code": doc.itp_code,
        "source_template": doc.source_template,
        "wbs_item": doc.wbs_item,
        "status": doc.status,
        "planned_start": doc.planned_start,
        "planned_end": doc.planned_end,
        "responsible_qa": doc.responsible_qa,
        "total_hold_points": doc.total_hold_points,
        "completed_hold_points": doc.completed_hold_points,
        "pending_hold_points": doc.pending_hold_points,
        "passed_hold_points": doc.passed_hold_points,
        "failed_hold_points": doc.failed_hold_points,
        "progress_percentage": doc.progress_percentage,
        "inspection_records": [
            {
                "name": r.name,
                "hold_point": r.hold_point,
                "hold_point_name": r.hold_point_name,
                "sequence": r.sequence,
                "scheduled_date": r.scheduled_date,
                "actual_date": r.actual_date,
                "inspector": r.inspector,
                "status": r.status,
                "actual_reading": r.actual_reading,
                "is_within_tolerance": r.is_within_tolerance,
                "non_conformance": r.non_conformance,
                "remarks": r.remarks
            }
            for r in doc.inspection_records
        ]
    }


@frappe.whitelist()
def record_inspection(itp_name, record_name, status, actual_reading=None, remarks=None):
    """
    Record inspection result.

    Args:
        itp_name (str): ITP name
        record_name (str): Inspection record name
        status (str): Pass, Fail, or Waived
        actual_reading (float, optional): Actual reading
        remarks (str, optional): Inspector remarks

    Returns:
        dict: Recording result
    """
    if not frappe.db.exists("Project Inspection Plan", itp_name):
        frappe.throw(_("ITP {0} does not exist").format(itp_name))

    record = ITPManager.update_inspection_status(
        record_name=record_name,
        status=status,
        actual_reading=actual_reading,
        inspector=frappe.session.user,
        remarks=remarks
    )

    return {
        "record_name": record.name,
        "status": record.status,
        "is_within_tolerance": record.is_within_tolerance
    }


@frappe.whitelist()
def create_ncr(data):
    """
    Create Non-Conformance Report.

    Args:
        data (dict): NCR data

    Returns:
        dict: Created NCR info
    """
    frappe.has_permission("Non-Conformance Report", "create", throw=True)

    required_fields = ["project", "wbs_item", "description", "severity"]
    for field in required_fields:
        if not data.get(field):
            frappe.throw(_("{0} is required").format(field))

    if not frappe.db.exists("Project", data["project"]):
        frappe.throw(_("Project {0} does not exist").format(data["project"]))

    if not frappe.db.exists("WBS Item", data["wbs_item"]):
        frappe.throw(_("WBS Item {0} does not exist").format(data["wbs_item"]))

    ncr = NCRManager.create_ncr_from_inspection(
        project=data["project"],
        wbs_item=data["wbs_item"],
        inspection_record=data.get("inspection_record"),
        description=data["description"],
        severity=data["severity"],
        target_close_date=data.get("target_close_date")
    )

    return {
        "name": ncr.name,
        "ncr_number": ncr.ncr_number,
        "status": ncr.status
    }


@frappe.whitelist()
def get_project_ncrs(project, status=None):
    """
    Get NCRs for a project.

    Args:
        project (str): Project name
        status (str, optional): Filter by status

    Returns:
        list: NCRs
    """
    if not frappe.db.exists("Project", project):
        frappe.throw(_("Project {0} does not exist").format(project))

    filters = {"project": project}
    if status:
        filters["status"] = status

    ncrs = frappe.get_all(
        "Non-Conformance Report",
        filters=filters,
        fields=["name", "ncr_number", "description", "severity", "status", "target_close_date", "actual_close_date"],
        order_by="creation desc"
    )

    return ncrs


@frappe.whitelist()
def get_ncr_details(ncr_name):
    """
    Get detailed NCR.

    Args:
        ncr_name (str): NCR name

    Returns:
        dict: NCR details
    """
    if not frappe.db.exists("Non-Conformance Report", ncr_name):
        frappe.throw(_("NCR {0} does not exist").format(ncr_name))

    doc = frappe.get_doc("Non-Conformance Report", ncr_name)

    return {
        "name": doc.name,
        "ncr_number": doc.ncr_number,
        "project": doc.project,
        "wbs_item": doc.wbs_item,
        "inspection_record": doc.inspection_record,
        "description": doc.description,
        "severity": doc.severity,
        "identified_date": doc.identified_date,
        "identified_by": doc.identified_by,
        "root_cause": doc.root_cause,
        "corrective_action": doc.corrective_action,
        "preventive_action": doc.preventive_action,
        "target_close_date": doc.target_close_date,
        "actual_close_date": doc.actual_close_date,
        "closed_by": doc.closed_by,
        "status": doc.status,
        "closure_remarks": doc.closure_remarks,
        "verification_date": doc.verification_date,
        "verified_by": doc.verified_by,
        "verification_remarks": doc.verification_remarks
    }


@frappe.whitelist()
def update_ncr_status(ncr_name, status, remarks=None):
    """
    Update NCR status.

    Args:
        ncr_name (str): NCR name
        status (str): New status
        remarks (str, optional): Status change remarks

    Returns:
        dict: Update result
    """
    if not frappe.db.exists("Non-Conformance Report", ncr_name):
        frappe.throw(_("NCR {0} does not exist").format(ncr_name))

    doc = frappe.get_doc("Non-Conformance Report", ncr_name)
    doc.status = status

    if status == "Closed":
        doc.actual_close_date = today()
        doc.closed_by = frappe.session.user
        if remarks:
            doc.closure_remarks = remarks

    doc.save(ignore_permissions=True)

    return {
        "name": doc.name,
        "status": doc.status
    }


@frappe.whitelist()
def close_ncr(ncr_name, closure_remarks=None):
    """
    Close an NCR.

    Args:
        ncr_name (str): NCR name
        closure_remarks (str, optional): Closure remarks

    Returns:
        dict: Closure result
    """
    ncr = NCRManager.close_ncr(ncr_name, closure_remarks)

    return {
        "name": ncr.name,
        "ncr_number": ncr.ncr_number,
        "status": ncr.status,
        "actual_close_date": ncr.actual_close_date
    }


@frappe.whitelist()
def verify_ncr(ncr_name, verification_remarks=None):
    """
    Verify a closed NCR.

    Args:
        ncr_name (str): NCR name
        verification_remarks (str, optional): Verification remarks

    Returns:
        dict: Verification result
    """
    if not frappe.db.exists("Non-Conformance Report", ncr_name):
        frappe.throw(_("NCR {0} does not exist").format(ncr_name))

    doc = frappe.get_doc("Non-Conformance Report", ncr_name)

    if doc.status != "Closed":
        frappe.throw(_("NCR must be Closed before verification"))

    doc.status = "Verified"
    doc.verification_date = today()
    doc.verified_by = frappe.session.user
    if verification_remarks:
        doc.verification_remarks = verification_remarks

    doc.save(ignore_permissions=True)

    logger.info(f"NCR {doc.ncr_number} verified")

    return {
        "name": doc.name,
        "status": doc.status,
        "verification_date": doc.verification_date
    }


@frappe.whitelist()
def get_quality_summary(project):
    """
    Get quality summary for a project.

    Args:
        project (str): Project name

    Returns:
        dict: Quality summary with ITP and NCR stats
    """
    itp_summary = ITPManager.get_project_itp_summary(project)
    ncr_summary = NCRManager.get_project_ncr_summary(project)
    blocking_status = NCRManager.check_project_ncr_blocking(project)

    return {
        "project": project,
        "itp": itp_summary,
        "ncr": ncr_summary,
        "billing_blocked": blocking_status["is_blocked"]
    }


@frappe.whitelist()
def check_billing_eligibility(project):
    """
    Check if project is eligible for billing based on NCR status.

    Args:
        project (str): Project name

    Returns:
        dict: Billing eligibility
    """
    blocking = NCRManager.check_project_ncr_blocking(project)

    return {
        "project": project,
        "can_bill": blocking["can_bill"],
        "reason": "Open Critical NCRs" if blocking["is_blocked"] else None,
        "open_critical": blocking["open_critical"],
        "open_major": blocking["open_major"]
    }