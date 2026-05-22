"""
HSE (Health, Safety & Environment) API Module

REST API endpoints for HSE incident tracking, safety inspections,
toolbox talks, and compliance reporting.
"""

import frappe
from frappe import _
from frappe.utils import today, add_days, flt
from epc_modules.utils import get_epc_logger

logger = get_epc_logger(__name__)


@frappe.whitelist(methods=["POST"])
def create_hse_incident(project, data):
    """
    Create HSE incident report.

    Args:
        project (str): Project name
        data (dict): Incident data

    Returns:
        dict: Created incident info
    """
    frappe.has_permission("HSE Incident", "create", throw=True)

    if not isinstance(data, dict):
        frappe.throw(_("data must be a dictionary"))

    if not frappe.db.exists("Project", project):
        frappe.throw(_("Project {0} does not exist").format(project))

    # Required field validation
    if not data.get("incident_date"):
        frappe.throw(_("incident_date is required"))
    if not data.get("incident_type"):
        frappe.throw(_("incident_type is required"))
    if not data.get("severity"):
        frappe.throw(_("severity is required"))

    # Use naming series to avoid race conditions
    naming_series = frappe.get_meta("HSE Incident").get_auto_login_name()
    if naming_series:
        doc = frappe.get_doc({
            "doctype": "HSE Incident",
            "naming_series": naming_series,
            "project": project,
            "incident_date": data.get("incident_date"),
            "incident_time": data.get("incident_time"),
            "location": data.get("location"),
            "incident_type": data.get("incident_type"),
            "severity": data.get("severity"),
            "description": data.get("description"),
            "immediate_action": data.get("immediate_action"),
            "root_cause": data.get("root_cause"),
            "corrective_action": data.get("corrective_action"),
            "preventive_action": data.get("preventive_action"),
            "reported_by": data.get("reported_by", frappe.session.user),
            "is_confidential": data.get("is_confidential", 0),
            "media_involvement": data.get("media_involvement", 0),
            "regulatory_reporting_required": data.get("regulatory_reporting_required", 0),
            "status": "Reported"
        })
        doc.insert()
        incident_number = doc.name
    else:
        incident_number = f"INC-{project[:4].upper()}-{frappe.generate_hash(length=8).upper()}"
        doc = frappe.get_doc({
            "doctype": "HSE Incident",
            "incident_number": incident_number,
            "project": project,
            "incident_date": data.get("incident_date"),
            "incident_time": data.get("incident_time"),
            "location": data.get("location"),
            "incident_type": data.get("incident_type"),
            "severity": data.get("severity"),
            "description": data.get("description"),
            "immediate_action": data.get("immediate_action"),
            "root_cause": data.get("root_cause"),
            "corrective_action": data.get("corrective_action"),
            "preventive_action": data.get("preventive_action"),
            "reported_by": data.get("reported_by", frappe.session.user),
            "is_confidential": data.get("is_confidential", 0),
            "media_involvement": data.get("media_involvement", 0),
            "regulatory_reporting_required": data.get("regulatory_reporting_required", 0),
            "status": "Reported"
        })
        doc.insert()

    logger.warning(f"HSE Incident reported: {incident_number} at {project}")

    return {
        "name": doc.name,
        "incident_number": doc.incident_number if hasattr(doc, "incident_number") else doc.name,
        "status": doc.status
    }


@frappe.whitelist()
def get_project_incidents(project, status=None, limit=20, offset=0):
    """
    Get HSE incidents for a project.

    Args:
        project (str): Project name
        status (str, optional): Filter by status
        limit (int, optional): Results per page (default 20, max 100)
        offset (int, optional): Starting offset

    Returns:
        list: Incidents
    """
    frappe.has_permission("HSE Incident", "read", throw=True)
    limit = min(int(limit or 20), 100)
    filters = {"project": project}
    if status:
        filters["status"] = status

    return frappe.get_list(
        "HSE Incident",
        filters=filters,
        fields=["name", "incident_number", "incident_date", "incident_type",
                "severity", "status", "location"],
        order_by="incident_date desc",
        limit_page_length=limit,
        limit_start=offset
    )


@frappe.whitelist(methods=["POST"])
def update_incident_status(incident_name, status, investigation_data=None):
    """
    Update incident status and add investigation details.

    Args:
        incident_name (str): Incident name
        status (str): New status
        investigation_data (dict, optional): Investigation details

    Returns:
        dict: Update result
    """
    frappe.has_permission("HSE Incident", "write", throw=True)
    doc = frappe.get_doc("HSE Incident", incident_name)

    doc.status = status

    if investigation_data and isinstance(investigation_data, dict):
        doc.investigated_by = investigation_data.get("investigated_by")
        doc.investigation_date = investigation_data.get("investigation_date", today())
        doc.root_cause = investigation_data.get("root_cause")
        doc.corrective_action = investigation_data.get("corrective_action")
        doc.preventive_action = investigation_data.get("preventive_action")

    if status == "Closed":
        doc.closure_date = today()

    try:
        doc.save()
    except Exception as e:
        frappe.log_error("HSE Incident update failed: {0}".format(str(e)), "HSE API Error")
        frappe.throw(_("Failed to update incident: {0}").format(str(e)))

    logger.info(f"HSE Incident {doc.incident_number} status updated to {status}")

    return {
        "name": doc.name,
        "status": doc.status
    }


@frappe.whitelist(methods=["POST"])
def create_safety_inspection(project, data):
    """
    Create safety inspection record.

    Args:
        project (str): Project name
        data (dict): Inspection data

    Returns:
        dict: Created inspection info
    """
    frappe.has_permission("Safety Inspection", "create", throw=True)

    if not isinstance(data, dict):
        frappe.throw(_("data must be a dictionary"))

    # Use naming series to avoid race conditions
    naming_series = frappe.get_meta("Safety Inspection").get_auto_login_name()
    if naming_series:
        doc = frappe.get_doc({
            "doctype": "Safety Inspection",
            "naming_series": naming_series,
            "project": project,
            "inspection_date": data.get("inspection_date", today()),
            "inspector": data.get("inspector", frappe.session.user),
            "inspection_type": data.get("inspection_type", "Daily"),
            "location_area": data.get("location_area"),
            "wbs_item": data.get("wbs_item"),
            "weather_conditions": data.get("weather_conditions"),
            "temperature": data.get("temperature"),
            "total_workers_present": data.get("total_workers_present"),
            "overall_status": data.get("overall_status", "Satisfactory"),
            "remarks": data.get("remarks")
        })
        # Add checklist items if provided
        if data.get("checklist_items"):
            for item in data["checklist_items"]:
                doc.append("checklist_items", item)
        doc.insert()
        inspection_number = doc.name
    else:
        inspection_number = f"SFT-{project[:4].upper()}-{frappe.generate_hash(length=8).upper()}"
        doc = frappe.get_doc({
            "doctype": "Safety Inspection",
            "inspection_number": inspection_number,
            "project": project,
            "inspection_date": data.get("inspection_date", today()),
            "inspector": data.get("inspector", frappe.session.user),
            "inspection_type": data.get("inspection_type", "Daily"),
            "location_area": data.get("location_area"),
            "wbs_item": data.get("wbs_item"),
            "weather_conditions": data.get("weather_conditions"),
            "temperature": data.get("temperature"),
            "total_workers_present": data.get("total_workers_present"),
            "overall_status": data.get("overall_status", "Satisfactory"),
            "remarks": data.get("remarks")
        })
        # Add checklist items if provided
        if data.get("checklist_items"):
            for item in data["checklist_items"]:
                doc.append("checklist_items", item)
        doc.insert()

    logger.info(f"Safety inspection completed: {inspection_number}")

    return {
        "name": doc.name,
        "inspection_number": doc.inspection_number if hasattr(doc, "inspection_number") else doc.name,
        "overall_status": doc.overall_status
    }


@frappe.whitelist()
def get_project_safety_inspections(project, inspection_type=None, limit=20, offset=0):
    """
    Get safety inspections for a project.

    Args:
        project (str): Project name
        inspection_type (str, optional): Filter by type
        limit (int, optional): Results per page (default 20, max 100)
        offset (int, optional): Starting offset

    Returns:
        list: Inspections
    """
    frappe.has_permission("Safety Inspection", "read", throw=True)
    limit = min(int(limit or 20), 100)
    filters = {"project": project}
    if inspection_type:
        filters["inspection_type"] = inspection_type

    return frappe.get_list(
        "Safety Inspection",
        filters=filters,
        fields=["name", "inspection_number", "inspection_date", "inspection_type",
                "inspector", "overall_status", "non_conformances"],
        order_by="inspection_date desc",
        limit_page_length=limit,
        limit_start=offset
    )


@frappe.whitelist(methods=["POST"])
def create_toolbox_talk(project, data):
    """
    Create toolbox talk record.

    Args:
        project (str): Project name
        data (dict): Toolbox talk data

    Returns:
        dict: Created record info
    """
    frappe.has_permission("Toolbox Talk Record", "create", throw=True)

    if not isinstance(data, dict):
        frappe.throw(_("data must be a dictionary"))

    # Use naming series to avoid race conditions
    naming_series = frappe.get_meta("Toolbox Talk Record").get_auto_login_name()
    if naming_series:
        doc = frappe.get_doc({
            "doctype": "Toolbox Talk Record",
            "naming_series": naming_series,
            "project": project,
            "talk_date": data.get("talk_date", today()),
            "talk_topic": data.get("talk_topic"),
            "talk_presenter": data.get("talk_presenter", frappe.session.user),
            "location": data.get("location"),
            "duration_minutes": data.get("duration_minutes"),
            "key_points": data.get("key_points"),
            "questions_raised": data.get("questions_raised"),
            "attendee_feedback": data.get("attendee_feedback"),
            "action_items": data.get("action_items")
        })
        # Add attendees
        if data.get("attendees"):
            for attendee in data["attendees"]:
                doc.append("attendees", attendee)
        doc.insert()
        talk_id = doc.name
    else:
        talk_id = f"TT-{project[:4].upper()}-{frappe.generate_hash(length=8).upper()}"
        doc = frappe.get_doc({
            "doctype": "Toolbox Talk Record",
            "talk_id": talk_id,
            "project": project,
            "talk_date": data.get("talk_date", today()),
            "talk_topic": data.get("talk_topic"),
            "talk_presenter": data.get("talk_presenter", frappe.session.user),
            "location": data.get("location"),
            "duration_minutes": data.get("duration_minutes"),
            "key_points": data.get("key_points"),
            "questions_raised": data.get("questions_raised"),
            "attendee_feedback": data.get("attendee_feedback"),
            "action_items": data.get("action_items")
        })
        # Add attendees
        if data.get("attendees"):
            for attendee in data["attendees"]:
                doc.append("attendees", attendee)
        doc.insert()

    return {
        "name": doc.name,
        "talk_id": doc.talk_id if hasattr(doc, "talk_id") else doc.name,
        "total_attendees": doc.total_attendees
    }


@frappe.whitelist()
def get_toolbox_talks(project, days=30, limit=20, offset=0):
    """
    Get toolbox talks for a project.

    Args:
        project (str): Project name
        days (int): Lookback period
        limit (int, optional): Results per page (default 20, max 100)
        offset (int, optional): Starting offset

    Returns:
        list: Toolbox talks
    """
    frappe.has_permission("Toolbox Talk Record", "read", throw=True)
    from frappe.utils import add_days as add_days_util

    limit = min(int(limit or 20), 100)
    cutoff = add_days_util(today(), -int(days))

    return frappe.get_list(
        "Toolbox Talk Record",
        filters={"project": project, "talk_date": [">=", cutoff]},
        fields=["name", "talk_id", "talk_date", "talk_topic", "talk_presenter",
                "total_attendees", "location"],
        order_by="talk_date desc",
        limit_page_length=limit,
        limit_start=offset
    )


# =============================================
# HSE Analytics & Reporting
# =============================================

@frappe.whitelist()
def get_hse_metrics(project, days=90):
    """
    Get HSE metrics for a project.

    Args:
        project (str): Project name
        days (int): Lookback period

    Returns:
        dict: HSE metrics
    """
    frappe.has_permission("HSE Incident", "read", throw=True)
    from frappe.utils import add_days as add_days_util

    days = int(days)
    cutoff = add_days_util(today(), -days)

    # Incident statistics
    incidents = frappe.get_list(
        "HSE Incident",
        filters={"project": project, "incident_date": [">=", cutoff]},
        fields=["name", "incident_type", "severity", "days_lost", "cost_impact"]
    )

    incident_stats = {
        "total": len(incidents),
        "by_type": {},
        "by_severity": {},
        "total_days_lost": 0,
        "total_cost_impact": 0
    }

    for inc in incidents:
        inc_type = inc.incident_type or "Unknown"
        severity = inc.severity or "Unknown"

        incident_stats["by_type"][inc_type] = incident_stats["by_type"].get(inc_type, 0) + 1
        incident_stats["by_severity"][severity] = incident_stats["by_severity"].get(severity, 0) + 1
        incident_stats["total_days_lost"] += inc.days_lost or 0
        incident_stats["total_cost_impact"] += flt(inc.cost_impact or 0)

    # Safety inspection statistics
    inspections = frappe.get_list(
        "Safety Inspection",
        filters={"project": project, "inspection_date": [">=", cutoff]},
        fields=["name", "inspection_type", "overall_status", "non_conformances"]
    )

    inspection_stats = {
        "total": len(inspections),
        "satisfactory": sum(1 for i in inspections if i.overall_status == "Satisfactory"),
        "needs_improvement": sum(1 for i in inspections if i.overall_status == "Needs Improvement"),
        "unsatisfactory": sum(1 for i in inspections if i.overall_status == "Unsatisfactory"),
        "total_nc": sum(i.non_conformances or 0 for i in inspections)
    }

    # Toolbox talks
    talks = frappe.get_list(
        "Toolbox Talk Record",
        filters={"project": project, "talk_date": [">=", cutoff]},
        fields=["name", "total_attendees"]
    )

    # Calculate rates
    total_workers = sum(t.total_attendees or 0 for t in talks)
    avg_attendance = total_workers / len(talks) if talks else 0

    # TRIR (Total Recordable Incident Rate) - per 200,000 hours
    # Assuming 50 working weeks * 40 hours * some worker count
    # Simplified calculation
    trir = (len(incidents) / (days / 30)) * 12 if days > 0 else 0  # Normalized to annual

    return {
        "project": project,
        "period_days": days,
        "incidents": incident_stats,
        "inspections": inspection_stats,
        "toolbox_talks": {
            "total": len(talks),
            "total_attendees": total_workers,
            "avg_attendance": round(avg_attendance, 1)
        },
        "trir": round(trir, 2),
        "safety_score": calculate_safety_score(incident_stats, inspection_stats)
    }


def calculate_safety_score(incident_stats, inspection_stats):
    """
    Calculate overall safety score (0-100).

    Args:
        incident_stats (dict): Incident statistics
        inspection_stats (dict): Inspection statistics

    Returns:
        int: Safety score
    """
    score = 100

    # Deductions for incidents
    total_incidents = incident_stats.get("total", 0)
    critical_incidents = incident_stats.get("by_severity", {}).get("Fatal", 0)
    major_incidents = incident_stats.get("by_severity", {}).get("Major", 0)

    if critical_incidents > 0:
        score -= 50 * critical_incidents
    if major_incidents > 0:
        score -= 10 * major_incidents
    score -= min(total_incidents * 2, 20)  # Max 20 points for other incidents

    # Deductions for inspection results
    total_insp = inspection_stats.get("total", 0)
    if total_insp > 0:
        unsatisfactory_rate = inspection_stats.get("unsatisfactory", 0) / total_insp
        score -= unsatisfactory_rate * 20

    return max(0, min(100, score))


@frappe.whitelist()
def get_incident_trend(project, months=6):
    """
    Get incident trend over time.

    Args:
        project (str): Project name
        months (int): Number of months

    Returns:
        dict: Trend data
    """
    frappe.has_permission("HSE Incident", "read", throw=True)
    from frappe.utils import add_months

    months = int(months)
    cutoff = add_months(today(), -months)

    incidents = frappe.get_list(
        "HSE Incident",
        filters={"project": project, "incident_date": [">=", cutoff]},
        fields=["name", "incident_date", "incident_type", "severity"],
        order_by="incident_date asc"
    )

    # Group by month
    by_month = {}
    for inc in incidents:
        month_key = inc.incident_date[:7]  # YYYY-MM
        if month_key not in by_month:
            by_month[month_key] = {"total": 0, "types": {}, "severities": {}}

        by_month[month_key]["total"] += 1
        by_month[month_key]["types"][inc.incident_type or "Unknown"] = \
            by_month[month_key]["types"].get(inc.incident_type or "Unknown", 0) + 1
        by_month[month_key]["severities"][inc.severity or "Unknown"] = \
            by_month[month_key]["severities"].get(inc.severity or "Unknown", 0) + 1

    return {
        "project": project,
        "period_months": months,
        "trend": by_month
    }


@frappe.whitelist()
def get_near_miss_ratio(project, days=90):
    """
    Calculate near-miss to incident ratio.
    Higher ratio indicates better safety reporting culture.

    Args:
        project (str): Project name
        days (int): Lookback period

    Returns:
        dict: Near miss ratio
    """
    frappe.has_permission("HSE Incident", "read", throw=True)
    from frappe.utils import add_days as add_days_util

    days = int(days)
    cutoff = add_days_util(today(), -days)

    incidents = frappe.get_list(
        "HSE Incident",
        filters={"project": project, "incident_date": [">=", cutoff]},
        fields=["name", "incident_type"]
    )

    near_misses = [i for i in incidents if i.incident_type == "Near Miss"]
    actual_incidents = [i for i in incidents if i.incident_type != "Near Miss"]

    ratio = len(near_misses) / len(actual_incidents) if actual_incidents else 0

    return {
        "project": project,
        "period_days": days,
        "near_miss_count": len(near_misses),
        "actual_incident_count": len(actual_incidents),
        "ratio": round(ratio, 2),
        "interpretation": interpret_near_miss_ratio(ratio)
    }


def interpret_near_miss_ratio(ratio):
    """Interpret near-miss ratio."""
    if ratio >= 10:
        return "Excellent - Strong safety reporting culture"
    elif ratio >= 5:
        return "Good - Active near-miss reporting"
    elif ratio >= 1:
        return "Moderate - Room for improvement"
    else:
        return "Needs Attention - Encourage near-miss reporting"


@frappe.whitelist(methods=["POST"])
def create_safety_observation(project, data):
    """Create Safety Observation."""
    frappe.has_permission("Safety Observation", "create", throw=True)

    if not isinstance(data, dict):
        frappe.throw(_("data must be a dictionary"))

    naming_series = frappe.get_meta("Safety Observation").get_auto_login_name()
    if naming_series:
        doc = frappe.get_doc({
            "doctype": "Safety Observation",
            "naming_series": naming_series,
            "project": project,
            "observation_date": data.get("observation_date", frappe.utils.today()),
            "observed_by": data.get("observed_by", frappe.session.user),
            "location": data.get("location"),
            "wbs_item": data.get("wbs_item"),
            "observation_title": data.get("observation_title"),
            "severity": data.get("severity", "Medium"),
            "category": data.get("category"),
            "description": data.get("description"),
            "corrective_action": data.get("corrective_action"),
            "target_date": data.get("target_date"),
            "status": "Open"
        })
        doc.insert()
        obs_number = doc.name
    else:
        project_code = project[:4].upper()
        obs_number = f"SO-{project_code}-{frappe.generate_hash(length=8).upper()}"
        doc = frappe.get_doc({
            "doctype": "Safety Observation",
            "observation_number": obs_number,
            "project": project,
            "observation_date": data.get("observation_date", frappe.utils.today()),
            "observed_by": data.get("observed_by", frappe.session.user),
            "location": data.get("location"),
            "wbs_item": data.get("wbs_item"),
            "observation_title": data.get("observation_title"),
            "severity": data.get("severity", "Medium"),
            "category": data.get("category"),
            "description": data.get("description"),
            "corrective_action": data.get("corrective_action"),
            "target_date": data.get("target_date"),
            "status": "Open"
        })
        doc.insert()
    return {"name": doc.name, "observation_number": obs_number}


@frappe.whitelist(methods=["POST"])
def create_method_statement(project, data):
    """Create Method Statement."""
    frappe.has_permission("Method Statement", "create", throw=True)

    if not isinstance(data, dict):
        frappe.throw(_("data must be a dictionary"))

    naming_series = frappe.get_meta("Method Statement").get_auto_login_name()
    if naming_series:
        doc = frappe.get_doc({
            "doctype": "Method Statement",
            "naming_series": naming_series,
            "project": project,
            "ms_title": data.get("ms_title"),
            "wbs_item": data.get("wbs_item"),
            "activity_description": data.get("activity_description"),
            "sequence_of_work": data.get("sequence_of_work"),
            "materials_equipment": data.get("materials_equipment"),
            "manpower_requirements": data.get("manpower_requirements"),
            "hazards_identified": data.get("hazards_identified"),
            "risk_controls": data.get("risk_controls"),
            "ppe_required": data.get("ppe_required"),
            "emergency_procedures": data.get("emergency_procedures"),
            "prepared_by": data.get("prepared_by", frappe.session.user),
            "prepared_date": frappe.utils.today(),
            "status": "Draft"
        })
        doc.insert()
        ms_number = doc.name
    else:
        project_code = project[:4].upper()
        ms_number = f"MS-{project_code}-{frappe.generate_hash(length=8).upper()}"
        doc = frappe.get_doc({
            "doctype": "Method Statement",
            "ms_number": ms_number,
            "project": project,
            "ms_title": data.get("ms_title"),
            "wbs_item": data.get("wbs_item"),
            "activity_description": data.get("activity_description"),
            "sequence_of_work": data.get("sequence_of_work"),
            "materials_equipment": data.get("materials_equipment"),
            "manpower_requirements": data.get("manpower_requirements"),
            "hazards_identified": data.get("hazards_identified"),
            "risk_controls": data.get("risk_controls"),
            "ppe_required": data.get("ppe_required"),
            "emergency_procedures": data.get("emergency_procedures"),
            "prepared_by": data.get("prepared_by", frappe.session.user),
            "prepared_date": frappe.utils.today(),
            "status": "Draft"
        })
        doc.insert()
    return {"name": doc.name, "ms_number": ms_number}


@frappe.whitelist(methods=["POST"])
def create_visitor_log(project, data):
    """Create Visitor Log entry."""
    frappe.has_permission("Visitor Log", "create", throw=True)

    if not isinstance(data, dict):
        frappe.throw(_("data must be a dictionary"))

    naming_series = frappe.get_meta("Visitor Log").get_auto_login_name()
    badge_number = f"B-{frappe.utils.now().strftime('%Y%m%d%H%M%S')}"

    if naming_series:
        doc = frappe.get_doc({
            "doctype": "Visitor Log",
            "naming_series": naming_series,
            "project": project,
            "pre_registered": data.get("pre_registered", 0),
            "visitor_name": data.get("visitor_name"),
            "company": data.get("company"),
            "email": data.get("email"),
            "phone": data.get("phone"),
            "purpose": data.get("purpose"),
            "entry_date": frappe.utils.now(),
            "area_visited": data.get("area_visited"),
            "badge_number": badge_number,
            "security_induction": data.get("security_induction", 0),
            "host_name": data.get("host_name"),
            "status": "In Site"
        })
        doc.insert()
        visitor_id = doc.name
    else:
        project_code = project[:4].upper()
        visitor_id = f"VIS-{project_code}-{frappe.generate_hash(length=8).upper()}"
        doc = frappe.get_doc({
            "doctype": "Visitor Log",
            "visitor_id": visitor_id,
            "project": project,
            "pre_registered": data.get("pre_registered", 0),
            "visitor_name": data.get("visitor_name"),
            "company": data.get("company"),
            "email": data.get("email"),
            "phone": data.get("phone"),
            "purpose": data.get("purpose"),
            "entry_date": frappe.utils.now(),
            "area_visited": data.get("area_visited"),
            "badge_number": badge_number,
            "security_induction": data.get("security_induction", 0),
            "host_name": data.get("host_name"),
            "status": "In Site"
        })
        doc.insert()
    return {"name": doc.name, "visitor_id": visitor_id, "badge_number": badge_number}


# =============================================
# HSE Report Endpoints
# =============================================

@frappe.whitelist()
def get_attendance_summary(project, from_date=None, to_date=None):
    """
    Get attendance summary report with labor utilization.

    Args:
        project (str): Project name
        from_date (str, optional): Start date
        to_date (str, optional): End date

    Returns:
        dict: Attendance summary with daily records and totals
    """
    frappe.has_permission("Site Attendance", "read", throw=True)
    if not from_date:
        from_date = add_days(today(), -30)
    if not to_date:
        to_date = today()

    records = frappe.get_list(
        "Site Attendance",
        filters={"project": project, "attendance_date": ["between", [from_date, to_date]]},
        fields=["name", "attendance_id", "attendance_date", "total_labor_count", "regular_hours_total",
                "overtime_hours_total", "status"]
    )

    total_hours = sum(r.regular_hours_total or 0 for r in records)
    total_ot = sum(r.overtime_hours_total or 0 for r in records)

    return {
        "project": project,
        "from_date": from_date,
        "to_date": to_date,
        "daily_records": records,
        "total_hours": total_hours,
        "total_overtime": total_ot,
        "avg_daily_labor": sum(r.total_labor_count or 0 for r in records) / len(records) if records else 0
    }


@frappe.whitelist()
def get_visitor_log_report(project, from_date=None, to_date=None, limit=20, offset=0):
    """
    Get visitor log report.

    Args:
        project (str): Project name
        from_date (str, optional): Start date
        to_date (str, optional): End date
        limit (int, optional): Results per page (default 20, max 100)
        offset (int, optional): Starting offset

    Returns:
        dict: Visitor log with visitor records and count
    """
    frappe.has_permission("Visitor Log", "read", throw=True)
    from frappe.utils import get_datetime

    limit = min(int(limit or 20), 100)
    filters = {"project": project}
    if from_date and to_date:
        filters["entry_date"] = ["between", [get_datetime(from_date), get_datetime(to_date)]]

    visitors = frappe.get_list(
        "Visitor Log",
        filters=filters,
        fields=["name", "visitor_id", "visitor_name", "company", "purpose",
                "entry_date", "exit_date", "area_visited", "status"],
        order_by="entry_date desc",
        limit_page_length=limit,
        limit_start=offset
    )

    return {"project": project, "visitors": visitors, "total_visits": len(visitors)}


@frappe.whitelist()
def get_safety_statistics(project):
    """
    Get safety statistics: observations, permits, incidents.

    Args:
        project (str): Project name

    Returns:
        dict: Safety statistics including open/closed observations and active permits
    """
    frappe.has_permission("Safety Observation", "read", throw=True)
    open_observations = frappe.db.count(
        "Safety Observation",
        {"project": project, "status": ["in", ["Open", "Action Taken"]]}
    )
    closed_observations = frappe.db.count(
        "Safety Observation",
        {"project": project, "status": "Closed"}
    )

    active_permits = frappe.db.count(
        "Work Permit",
        {"project": project, "status": ["in", ["Approved", "In Progress"]]}
    )

    total_obs = open_observations + closed_observations
    closure_rate = (closed_observations / total_obs * 100) if total_obs > 0 else 0

    return {
        "project": project,
        "open_observations": open_observations,
        "closed_observations": closed_observations,
        "active_permits": active_permits,
        "closure_rate": round(closure_rate, 2)
    }


# =============================================
# Site Attendance API
# =============================================

@frappe.whitelist(methods=["POST"])
def create_site_attendance(project, data):
    """Create Site Attendance record."""
    frappe.has_permission("Site Attendance", "create", throw=True)

    if not isinstance(data, dict):
        frappe.throw(_("data must be a dictionary"))

    naming_series = frappe.get_meta("Site Attendance").get_auto_login_name()
    if naming_series:
        doc = frappe.get_doc({
            "doctype": "Site Attendance",
            "naming_series": naming_series,
            "project": project,
            "attendance_date": data.get("attendance_date", frappe.utils.today()),
            "entries": data.get("entries", []),
            "recorded_by": frappe.session.user,
            "status": "Draft"
        })
        doc.insert()
        att_id = doc.name
    else:
        project_code = project[:4].upper()
        att_id = f"SA-{project_code}-{frappe.generate_hash(length=8).upper()}"
        doc = frappe.get_doc({
            "doctype": "Site Attendance",
            "attendance_id": att_id,
            "project": project,
            "attendance_date": data.get("attendance_date", frappe.utils.today()),
            "entries": data.get("entries", []),
            "recorded_by": frappe.session.user,
            "status": "Draft"
        })
        doc.insert()
    return {"name": doc.name, "attendance_id": att_id}


# =============================================
# PPE Type Configuration
# =============================================

@frappe.whitelist(methods=["POST"])
def create_ppe_type(data):
    """Create PPE Type configuration."""
    frappe.has_permission("PPE Type", "create", throw=True)

    if not isinstance(data, dict):
        frappe.throw(_("data must be a dictionary"))

    doc = frappe.get_doc({
        "doctype": "PPE Type",
        "ppe_type_name": data.get("ppe_type_name"),
        "category": data.get("category"),
        "description": data.get("description"),
        "standard": data.get("standard"),
        "inspection_frequency_days": data.get("inspection_frequency_days", 30),
        "replacement_interval_days": data.get("replacement_interval_days"),
        "storage_requirements": data.get("storage_requirements"),
        "is_active": 1
    })
    try:
        doc.insert()
    except Exception as e:
        frappe.log_error("PPE Type insert failed: {0}".format(str(e)), "HSE API Error")
        frappe.throw(_("Failed to create PPE type: {0}").format(str(e)))
    return {"name": doc.name}


@frappe.whitelist()
def get_ppe_types(category=None, limit=20, offset=0):
    """Get PPE types, optionally filtered by category."""
    frappe.has_permission("PPE Type", "read", throw=True)
    limit = min(int(limit or 20), 100)
    filters = {"is_active": 1}
    if category:
        filters["category"] = category
    return frappe.get_list("PPE Type", filters=filters,
        fields=["name", "ppe_type_name", "category", "standard"],
        limit_page_length=limit, limit_start=offset)


# =============================================
# Work Permit API
# =============================================

@frappe.whitelist(methods=["POST"])
def create_work_permit(project, data):
    """Create Work Permit."""
    frappe.has_permission("Work Permit", "create", throw=True)

    if not isinstance(data, dict):
        frappe.throw(_("data must be a dictionary"))

    naming_series = frappe.get_meta("Work Permit").get_auto_login_name()
    if naming_series:
        doc = frappe.get_doc({
            "doctype": "Work Permit",
            "naming_series": naming_series,
            "project": project,
            "permit_type": data.get("permit_type"),
            "work_description": data.get("work_description"),
            "location": data.get("location"),
            "wbs_item": data.get("wbs_item"),
            "start_date": data.get("start_date"),
            "end_date": data.get("end_date"),
            "issued_by": frappe.session.user,
            "status": "Draft"
        })
        doc.insert()
        permit_number = doc.name
    else:
        project_code = project[:4].upper()
        permit_number = f"WP-{project_code}-{frappe.generate_hash(length=8).upper()}"
        doc = frappe.get_doc({
            "doctype": "Work Permit",
            "permit_number": permit_number,
            "project": project,
            "permit_type": data.get("permit_type"),
            "work_description": data.get("work_description"),
            "location": data.get("location"),
            "wbs_item": data.get("wbs_item"),
            "start_date": data.get("start_date"),
            "end_date": data.get("end_date"),
            "issued_by": frappe.session.user,
            "status": "Draft"
        })
        doc.insert()
    return {"name": doc.name, "permit_number": permit_number}


@frappe.whitelist()
def get_work_permit_list(project=None, status=None, limit=20, offset=0):
    """Get work permits filtered by project and status."""
    frappe.has_permission("Work Permit", "read", throw=True)
    limit = min(int(limit or 20), 100)
    filters = {}
    if project:
        filters["project"] = project
    if status:
        filters["status"] = status
    return frappe.get_list(
        "Work Permit",
        filters=filters,
        fields=["name", "permit_number", "project", "permit_type", "location",
                "start_date", "end_date", "status"],
        order_by="creation desc",
        limit_page_length=limit,
        limit_start=offset
    )
