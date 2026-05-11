"""
Advanced Construction API Module

REST API endpoints for risk management, equipment management,
subcontractor management, HSE, and document management.
"""

import frappe
from frappe import _
from frappe.utils import today, add_days, flt
from epc_modules.utils import get_epc_logger

logger = get_epc_logger(__name__)


# =============================================
# Risk Management
# =============================================

@frappe.whitelist()
def create_risk(project, data):
    """
    Create a new risk register entry.

    Args:
        project (str): Project name
        data (dict): Risk data

    Returns:
        dict: Created risk info
    """
    frappe.has_permission("Risk Register", "create", throw=True)

    if not frappe.db.exists("Project", project):
        frappe.throw(_("Project {0} does not exist").format(project))

    count = frappe.db.count("Risk Register", {"project": project}) or 0
    risk_id = f"RSK-{project[:4].upper()}-{count + 1:04d}"

    # Calculate risk score
    probability_scores = {"Very Low": 1, "Low": 2, "Medium": 3, "High": 4, "Very High": 5}
    impact_scores = {"Very Low": 1, "Low": 2, "Medium": 3, "High": 4, "Very High": 5}

    prob_score = probability_scores.get(data.get("probability", "Medium"), 3)
    imp_score = impact_scores.get(data.get("impact", "Medium"), 3)
    risk_score = prob_score * imp_score

    # Determine rating
    if risk_score >= 20:
        rating = "Critical"
    elif risk_score >= 15:
        rating = "High"
    elif risk_score >= 8:
        rating = "Medium"
    else:
        rating = "Low"

    doc = frappe.get_doc({
        "doctype": "Risk Register",
        "risk_id": risk_id,
        "project": project,
        "risk_category": data.get("risk_category"),
        "risk_title": data.get("risk_title"),
        "probability": data.get("probability"),
        "impact": data.get("impact"),
        "risk_score": risk_score,
        "risk_rating": rating,
        "potential_impact": data.get("potential_impact"),
        "mitigation_strategy": data.get("mitigation_strategy"),
        "contingency_plan": data.get("contingency_plan"),
        "responsible_person": data.get("responsible_person"),
        "review_date": data.get("review_date"),
        "status": "Identified"
    })

    doc.insert()

    logger.info(f"Created risk {risk_id} for project {project}")

    return {
        "name": doc.name,
        "risk_id": doc.risk_id,
        "risk_score": risk_score,
        "risk_rating": rating
    }


@frappe.whitelist()
def get_project_risks(project, status=None):
    """
    Get risks for a project.

    Args:
        project (str): Project name
        status (str, optional): Filter by status

    Returns:
        list: Project risks
    """
    filters = {"project": project}
    if status:
        filters["status"] = status

    return frappe.get_all(
        "Risk Register",
        filters=filters,
        fields=["name", "risk_id", "risk_category", "risk_title", "risk_score",
                "risk_rating", "status", "responsible_person", "review_date"],
        order_by="risk_score desc"
    )


@frappe.whitelist()
def update_risk_action(risk_name, action_data):
    """
    Update a risk response action.

    Args:
        risk_name (str): Risk register name
        action_data (dict): Action update data

    Returns:
        dict: Update result
    """
    frappe.has_permission("Risk Register", "write", throw=True)

    doc = frappe.get_doc("Risk Register", risk_name)

    for action in doc.risk_actions:
        if action.name == action_data.get("action_name"):
            action.status = action_data.get("status", action.status)
            if action.status == "Completed":
                action.completed_date = today()
            break

    doc.save()

    return {"name": doc.name, "status": "updated"}


@frappe.whitelist()
def close_risk(risk_name, lessons_learned=None):
    """
    Close a risk and record lessons learned.

    Args:
        risk_name (str): Risk register name
        lessons_learned (str): Post-mortem notes

    Returns:
        dict: Closure result
    """
    frappe.has_permission("Risk Register", "write", throw=True)

    doc = frappe.get_doc("Risk Register", risk_name)

    doc.status = "Closed"
    doc.is_closed = 1
    doc.closure_date = today()
    if lessons_learned:
        doc.lessons_learned = lessons_learned

    doc.save()

    logger.info(f"Risk {doc.risk_id} closed")

    return {
        "name": doc.name,
        "status": "Closed",
        "closure_date": doc.closure_date
    }


# =============================================
# Equipment Management
# =============================================

@frappe.whitelist()
def create_equipment(data):
    """
    Create equipment register entry.

    Args:
        data (dict): Equipment data

    Returns:
        dict: Created equipment info
    """
    frappe.has_permission("Equipment Register", "create", throw=True)

    count = frappe.db.count("Equipment Register") or 0
    equipment_id = f"EQ-{count + 1:05d}"

    doc = frappe.get_doc({
        "doctype": "Equipment Register",
        "equipment_id": equipment_id,
        "equipment_name": data.get("equipment_name"),
        "equipment_category": data.get("equipment_category"),
        "manufacturer": data.get("manufacturer"),
        "model_number": data.get("model_number"),
        "serial_number": data.get("serial_number"),
        "year_of_manufacture": data.get("year_of_manufacture"),
        "project": data.get("project"),
        "equipment_status": data.get("equipment_status", "Available"),
        "ownership_type": data.get("ownership_type"),
        "lease_vendor": data.get("lease_vendor"),
        "lease_start_date": data.get("lease_start_date"),
        "lease_end_date": data.get("lease_end_date"),
        "lease_rate": data.get("lease_rate"),
        "fuel_type": data.get("fuel_type"),
        "fuel_capacity_ltr": data.get("fuel_capacity_ltr"),
        "average_fuel_consumption": data.get("average_fuel_consumption"),
        "operator_required": data.get("operator_required", 0),
        "insurance_expiry": data.get("insurance_expiry"),
        "road_tax_expiry": data.get("road_tax_expiry"),
        "fitness_certificate_expiry": data.get("fitness_certificate_expiry"),
        "current_location": data.get("current_location")
    })

    doc.insert()

    logger.info(f"Created equipment {equipment_id}: {doc.equipment_name}")

    return {
        "name": doc.name,
        "equipment_id": doc.equipment_id
    }


@frappe.whitelist()
def get_equipment_list(filters=None):
    """
    Get equipment list with filters.

    Args:
        filters (dict): Filter options

    Returns:
        list: Equipment records
    """
    filter_dict = {}
    if filters:
        if filters.get("project"):
            filter_dict["project"] = filters["project"]
        if filters.get("status"):
            filter_dict["equipment_status"] = filters["status"]
        if filters.get("category"):
            filter_dict["equipment_category"] = filters["category"]

    return frappe.get_all(
        "Equipment Register",
        filters=filter_dict,
        fields=["name", "equipment_id", "equipment_name", "equipment_category",
                "equipment_status", "project", "operator_required"],
        order_by="equipment_id asc"
    )


@frappe.whitelist()
def update_equipment_status(equipment_name, status):
    """
    Update equipment status.

    Args:
        equipment_name (str): Equipment name
        status (str): New status

    Returns:
        dict: Update result
    """
    frappe.has_permission("Equipment Register", "write", throw=True)
    if not frappe.db.exists("Equipment Register", equipment_name):
        frappe.throw(_("Equipment {0} not found").format(equipment_name))

    doc = frappe.get_doc("Equipment Register", equipment_name)
    doc.equipment_status = status
    doc.save()

    return {
        "name": doc.name,
        "equipment_status": status
    }


@frappe.whitelist()
def log_equipment_utilization(data):
    """
    Log equipment utilization.

    Args:
        data (dict): Utilization data

    Returns:
        dict: Log entry info
    """
    frappe.has_permission("Equipment Utilization Log", "create", throw=True)

    count = frappe.db.count("Equipment Utilization Log") or 0
    log_id = f"UTIL-{count + 1:06d}"

    # Calculate costs
    operator_rate = data.get("operator_rate", 0)
    fuel_cost = data.get("fuel_cost", 0)
    total_cost = operator_rate + fuel_cost

    doc = frappe.get_doc({
        "doctype": "Equipment Utilization Log",
        "log_id": log_id,
        "equipment": data.get("equipment"),
        "project": data.get("project"),
        "log_date": data.get("log_date", today()),
        "operator": data.get("operator"),
        "work_description": data.get("work_description"),
        "hours_worked": data.get("hours_worked", 0),
        "idle_hours": data.get("idle_hours", 0),
        "fuel_consumed_ltr": data.get("fuel_consumed_ltr"),
        "location": data.get("location"),
        "output_quantity": data.get("output_quantity"),
        "output_unit": data.get("output_unit"),
        "operator_rate": operator_rate,
        "fuel_cost": fuel_cost,
        "total_cost": total_cost,
        "remarks": data.get("remarks")
    })

    doc.insert()

    return {
        "name": doc.name,
        "log_id": doc.log_id,
        "total_cost": total_cost
    }


@frappe.whitelist()
def create_maintenance_schedule(equipment_name, data):
    """
    Create maintenance schedule for equipment.

    Args:
        equipment_name (str): Equipment name
        data (dict): Schedule data

    Returns:
        dict: Created schedule info
    """
    frappe.has_permission("Equipment Maintenance Schedule", "create", throw=True)

    count = frappe.db.count("Equipment Maintenance Schedule") or 0
    schedule_id = f"MNT-{count + 1:05d}"

    # Calculate next service date
    interval = data.get("interval_days", 30)
    next_service = add_days(today(), interval)

    doc = frappe.get_doc({
        "doctype": "Equipment Maintenance Schedule",
        "schedule_id": schedule_id,
        "equipment": equipment_name,
        "maintenance_type": data.get("maintenance_type"),
        "description": data.get("description"),
        "interval_days": interval,
        "last_service_date": data.get("last_service_date"),
        "next_service_date": next_service,
        "last_service_hours": data.get("last_service_hours"),
        "estimated_cost": data.get("estimated_cost"),
        "responsible_vendor": data.get("responsible_vendor"),
        "is_scheduled": 1,
        "alerts_enabled": data.get("alerts_enabled", 1),
        "alert_days_before": data.get("alert_days_before", 7)
    })

    doc.insert()

    return {
        "name": doc.name,
        "schedule_id": doc.schedule_id,
        "next_service_date": next_service
    }


@frappe.whitelist()
def get_maintenance_alerts():
    """
    Get upcoming maintenance alerts.

    Returns:
        list: Maintenance due alerts
    """
    upcoming = add_days(today(), 7)

    return frappe.get_all(
        "Equipment Maintenance Schedule",
        filters={
            "is_scheduled": 1,
            "alerts_enabled": 1,
            "next_service_date": ["<=", upcoming]
        },
        fields=["name", "schedule_id", "equipment", "maintenance_type",
                "description", "next_service_date", "alert_days_before"],
        order_by="next_service_date asc"
    )


@frappe.whitelist()
def move_equipment(equipment_name, data):
    """
    Record equipment movement.

    Args:
        equipment_name (str): Equipment name
        data (dict): Movement data

    Returns:
        dict: Movement record info
    """
    frappe.has_permission("Equipment Movement", "create", throw=True)

    count = frappe.db.count("Equipment Movement") or 0
    movement_id = f"MOV-{count + 1:05d}"

    doc = frappe.get_doc({
        "doctype": "Equipment Movement",
        "movement_id": movement_id,
        "equipment": equipment_name,
        "movement_date": data.get("movement_date", today()),
        "from_project": data.get("from_project"),
        "to_project": data.get("to_project"),
        "movement_type": data.get("movement_type"),
        "transportation_mode": data.get("transportation_mode"),
        "transportation_cost": data.get("transportation_cost"),
        "authorized_by": data.get("authorized_by"),
        "purpose": data.get("purpose")
    })

    doc.insert()

    # Update equipment location if movement type is Transfer
    if data.get("movement_type") == "Transfer" and data.get("to_project"):
        frappe.has_permission("Equipment Register", "write", throw=True)
        eq_doc = frappe.get_doc("Equipment Register", equipment_name)
        eq_doc.project = data.get("to_project")
        eq_doc.current_location = data.get("to_project")
        eq_doc.save()

    return {
        "name": doc.name,
        "movement_id": doc.movement_id
    }


# =============================================
# Equipment Analytics
# =============================================

@frappe.whitelist()
def get_equipment_utilization_summary(project=None, days=30):
    """
    Get equipment utilization summary.

    Args:
        project (str, optional): Filter by project
        days (int): Lookback period

    Returns:
        dict: Utilization summary
    """
    from frappe.utils import add_days as add_days_util

    cutoff = add_days_util(today(), -days)

    filters = {"log_date": [">=", cutoff]}
    if project:
        filters["project"] = project

    logs = frappe.get_all(
        "Equipment Utilization Log",
        filters=filters,
        fields=["equipment", "hours_worked", "idle_hours", "fuel_consumed_ltr", "total_cost"]
    )

    # Group by equipment
    by_equipment = {}
    for log in logs:
        eq = log.equipment
        if eq not in by_equipment:
            by_equipment[eq] = {"hours": 0, "idle": 0, "fuel": 0, "cost": 0}
        by_equipment[eq]["hours"] += log.hours_worked or 0
        by_equipment[eq]["idle"] += log.idle_hours or 0
        by_equipment[eq]["fuel"] += log.fuel_consumed_ltr or 0
        by_equipment[eq]["cost"] += log.total_cost or 0

    # Calculate utilization rates
    for eq, data in by_equipment.items():
        total = data["hours"] + data["idle"]
        data["utilization_rate"] = round((data["hours"] / total * 100) if total > 0 else 0, 2)

    return {
        "period_days": days,
        "equipment_count": len(by_equipment),
        "total_hours": sum(d["hours"] for d in by_equipment.values()),
        "by_equipment": by_equipment
    }


@frappe.whitelist()
def get_equipment_cost_analysis(project=None):
    """
    Get equipment cost analysis by ownership type.

    Args:
        project (str, optional): Filter by project

    Returns:
        dict: Cost analysis
    """
    filters = {}
    if project:
        filters["project"] = project

    equipment_list = frappe.get_all(
        "Equipment Register",
        filters=filters,
        fields=["name", "equipment_id", "ownership_type", "lease_rate",
                "average_fuel_consumption", "project"]
    )

    analysis = {
        "owned": {"count": 0, "monthly_cost": 0},
        "leased": {"count": 0, "monthly_cost": 0},
        "rented": {"count": 0, "monthly_cost": 0}
    }

    for eq in equipment_list:
        ownership = eq.ownership_type or "Owned"
        ownership_key = ownership.lower()

        if ownership_key in analysis:
            analysis[ownership_key]["count"] += 1
            analysis[ownership_key]["monthly_cost"] += flt(eq.lease_rate or 0)

    return {
        "project": project,
        "analysis": analysis,
        "total_equipment": len(equipment_list)
    }


# =============================================
# Subcontractor Management
# =============================================

@frappe.whitelist()
def create_subcontractor_profile(data):
    """
    Create subcontractor profile.

    Args:
        data (dict): Subcontractor data

    Returns:
        dict: Created profile info
    """
    frappe.has_permission("Subcontractor Profile", "create", throw=True)

    count = frappe.db.count("Subcontractor Profile") or 0
    subcontractor_id = f"SC-{count + 1:04d}"

    doc = frappe.get_doc({
        "doctype": "Subcontractor Profile",
        "subcontractor_id": subcontractor_id,
        "subcontractor_name": data.get("subcontractor_name"),
        "contact_person": data.get("contact_person"),
        "email": data.get("email"),
        "phone": data.get("phone"),
        "address": data.get("address"),
        "trade_category": data.get("trade_category"),
        "registration_number": data.get("registration_number"),
        "tax_id": data.get("tax_id"),
        "years_in_business": data.get("years_in_business"),
        "bonding_capacity": data.get("bonding_capacity"),
        "insurance_coverage": data.get("insurance_coverage"),
        "insurance_expiry": data.get("insurance_expiry"),
        "safety_rating": data.get("safety_rating"),
        "quality_rating": data.get("quality_rating"),
        "bank_name": data.get("bank_name"),
        "account_number": data.get("account_number"),
        "ifsc_swift": data.get("ifsc_swift"),
        "status": "Active"
    })

    doc.insert()

    return {
        "name": doc.name,
        "subcontractor_id": doc.subcontractor_id
    }


@frappe.whitelist()
def get_subcontractor_list(active_only=True):
    """
    Get subcontractor list.

    Args:
        active_only (bool): Filter active only

    Returns:
        list: Subcontractors
    """
    filters = {}
    if active_only:
        filters["status"] = "Active"

    return frappe.get_all(
        "Subcontractor Profile",
        filters=filters,
        fields=["name", "subcontractor_id", "subcontractor_name", "trade_category",
                "safety_rating", "quality_rating", "insurance_expiry", "status"],
        order_by="subcontractor_name asc"
    )


@frappe.whitelist()
def get_expiring_insurance(days=30):
    """
    Get subcontractors with expiring insurance.

    Args:
        days (int): Days to check

    Returns:
        list: Expiring insurance alerts
    """
    cutoff = add_days(today(), days)

    return frappe.get_all(
        "Subcontractor Profile",
        filters={
            "status": "Active",
            "insurance_expiry": ["<=", cutoff],
            "blacklist": 0
        },
        fields=["name", "subcontractor_id", "subcontractor_name", "insurance_expiry"],
        order_by="insurance_expiry asc"
    )


@frappe.whitelist()
def create_subcontractor_work_order(project, subcontractor, data):
    """
    Create work order for subcontractor.

    Args:
        project (str): Project name
        subcontractor (str): Subcontractor name
        data (dict): Work order data

    Returns:
        dict: Created work order info
    """
    frappe.has_permission("Subcontractor Work Order", "create", throw=True)

    count = frappe.db.count("Subcontractor Work Order", {"project": project}) or 0
    work_order_id = f"WO-{project[:4].upper()}-{count + 1:04d}"

    doc = frappe.get_doc({
        "doctype": "Subcontractor Work Order",
        "work_order_id": work_order_id,
        "project": project,
        "subcontractor": subcontractor,
        "work_order_number": data.get("work_order_number"),
        "scope_of_work": data.get("scope_of_work"),
        "start_date": data.get("start_date"),
        "end_date": data.get("end_date"),
        "contract_value": data.get("contract_value"),
        "payment_terms": data.get("payment_terms"),
        "retention_percentage": data.get("retention_percentage", 10),
        "insurance_required": data.get("insurance_required", 1),
        "mobilization_advance": data.get("mobilization_advance"),
        "advance_recovery_percentage": data.get("advance_recovery_percentage", 20),
        "status": "Draft"
    })

    doc.insert()

    return {
        "name": doc.name,
        "work_order_id": doc.work_order_id
    }


@frappe.whitelist()
def get_subcontractor_work_orders(subcontractor=None, project=None):
    """
    Get work orders.

    Args:
        subcontractor (str, optional): Filter by subcontractor
        project (str, optional): Filter by project

    Returns:
        list: Work orders
    """
    filters = {}
    if subcontractor:
        filters["subcontractor"] = subcontractor
    if project:
        filters["project"] = project

    return frappe.get_all(
        "Subcontractor Work Order",
        filters=filters,
        fields=["name", "work_order_id", "project", "subcontractor",
                "contract_value", "status", "start_date", "end_date"],
        order_by="creation desc"
    )
