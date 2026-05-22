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


@frappe.whitelist()
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

    if not frappe.db.exists("Project", project):
        frappe.throw(_("Project {0} does not exist").format(project))

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
        "incident_number": doc.incident_number,
        "status": doc.status
    }


@frappe.whitelist()
def get_project_incidents(project, status=None):
    """
    Get HSE incidents for a project.

    Args:
        project (str): Project name
        status (str, optional): Filter by status

    Returns:
        list: Incidents
    """
    filters = {"project": project}
    if status:
        filters["status"] = status

    return frappe.get_all(
        "HSE Incident",
        filters=filters,
        fields=["name", "incident_number", "incident_date", "incident_type",
                "severity", "status", "location"],
        order_by="incident_date desc"
    )


@frappe.whitelist()
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

    if investigation_data:
        doc.investigated_by = investigation_data.get("investigated_by")
        doc.investigation_date = investigation_data.get("investigation_date", today())
        doc.root_cause = investigation_data.get("root_cause")
        doc.corrective_action = investigation_data.get("corrective_action")
        doc.preventive_action = investigation_data.get("preventive_action")

    if status == "Closed":
        doc.closure_date = today()

    doc.save()

    logger.info(f"HSE Incident {doc.incident_number} status updated to {status}")

    return {
        "name": doc.name,
        "status": doc.status
    }


@frappe.whitelist()
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
        "inspection_number": doc.inspection_number,
        "overall_status": doc.overall_status
    }


@frappe.whitelist()
def get_project_safety_inspections(project, inspection_type=None):
    """
    Get safety inspections for a project.

    Args:
        project (str): Project name
        inspection_type (str, optional): Filter by type

    Returns:
        list: Inspections
    """
    filters = {"project": project}
    if inspection_type:
        filters["inspection_type"] = inspection_type

    return frappe.get_all(
        "Safety Inspection",
        filters=filters,
        fields=["name", "inspection_number", "inspection_date", "inspection_type",
                "inspector", "overall_status", "non_conformances"],
        order_by="inspection_date desc"
    )


@frappe.whitelist()
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
        "talk_id": doc.talk_id,
        "total_attendees": doc.total_attendees
    }


@frappe.whitelist()
def get_toolbox_talks(project, days=30):
    """
    Get toolbox talks for a project.

    Args:
        project (str): Project name
        days (int): Lookback period

    Returns:
        list: Toolbox talks
    """
    from frappe.utils import add_days as add_days_util

    cutoff = add_days_util(today(), -days)

    return frappe.get_all(
        "Toolbox Talk Record",
        filters={"project": project, "talk_date": [">=", cutoff]},
        fields=["name", "talk_id", "talk_date", "talk_topic", "talk_presenter",
                "total_attendees", "location"],
        order_by="talk_date desc"
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
    from frappe.utils import add_days as add_days_util

    cutoff = add_days_util(today(), -days)

    # Incident statistics
    incidents = frappe.get_all(
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
    inspections = frappe.get_all(
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
    talks = frappe.get_all(
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
    from frappe.utils import add_months

    cutoff = add_months(today(), -months)

    incidents = frappe.get_all(
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
    from frappe.utils import add_days as add_days_util

    cutoff = add_days_util(today(), -days)

    incidents = frappe.get_all(
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
