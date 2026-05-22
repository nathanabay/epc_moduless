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

    # Validate required fields
    if not data.get("risk_category"):
        frappe.throw(_("Risk Category is required"))
    if not data.get("risk_title"):
        frappe.throw(_("Risk Title is required"))

    risk_id = frappe.generate_hash("Risk Register", 10)

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

    try:
        doc.insert()
    except frappe.DuplicateEntryError:
        frappe.throw(_("Risk with this ID already exists"))
    except frappe.ValidationError as e:
        frappe.throw(_("Validation error: {0}").format(str(e)))
    except Exception as e:
        logger.error(f"Failed to create risk: {e}")
        frappe.throw(_("Failed to create risk: {0}").format(str(e)))

    logger.info(f"Created risk {risk_id} for project {project}")

    return {
        "name": doc.name,
        "risk_id": doc.risk_id,
        "risk_score": risk_score,
        "risk_rating": rating
    }


@frappe.whitelist()
def get_project_risks(project, status=None, limit=20, offset=0):
    """
    Get risks for a project.

    Args:
        project (str): Project name
        status (str, optional): Filter by status
        limit (int): Page size (max 100)
        offset (int): Starting offset

    Returns:
        list: Project risks
    """
    frappe.has_permission("Risk Register", "read", throw=True)

    if not frappe.db.exists("Project", project):
        frappe.throw(_("Project {0} does not exist").format(project))

    filters = {"project": project}
    if status:
        filters["status"] = status

    limit = min(int(limit), 100)

    return frappe.get_list(
        "Risk Register",
        filters=filters,
        fields=["name", "risk_id", "risk_category", "risk_title", "risk_score",
                "risk_rating", "status", "responsible_person", "review_date"],
        order_by="risk_score desc",
        limit_page_length=limit,
        limit_start=offset
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

    try:
        doc.save()
    except frappe.ValidationError as e:
        frappe.throw(_("Validation error: {0}").format(str(e)))
    except Exception as e:
        logger.error(f"Failed to update risk action: {e}")
        frappe.throw(_("Failed to update risk action: {0}").format(str(e)))

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

    try:
        doc.save()
    except frappe.ValidationError as e:
        frappe.throw(_("Validation error: {0}").format(str(e)))
    except Exception as e:
        logger.error(f"Failed to close risk: {e}")
        frappe.throw(_("Failed to close risk: {0}").format(str(e)))

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

    equipment_id = frappe.generate_hash("Equipment Register", 10)

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

    try:
        doc.insert()
    except frappe.DuplicateEntryError:
        frappe.throw(_("Equipment with this ID already exists"))
    except frappe.ValidationError as e:
        frappe.throw(_("Validation error: {0}").format(str(e)))
    except Exception as e:
        logger.error(f"Failed to create equipment: {e}")
        frappe.throw(_("Failed to create equipment: {0}").format(str(e)))

    logger.info(f"Created equipment {equipment_id}: {doc.equipment_name}")

    return {
        "name": doc.name,
        "equipment_id": doc.equipment_id
    }


@frappe.whitelist()
def get_equipment_list(filters=None, limit=20, offset=0):
    """
    Get equipment list with filters.

    Args:
        filters (dict): Filter options
        limit (int): Page size (max 100)
        offset (int): Starting offset

    Returns:
        list: Equipment records
    """
    frappe.has_permission("Equipment Register", "read", throw=True)

    filter_dict = {}
    if filters:
        if filters.get("project"):
            filter_dict["project"] = filters["project"]
        if filters.get("status"):
            filter_dict["equipment_status"] = filters["status"]
        if filters.get("category"):
            filter_dict["equipment_category"] = filters["category"]

    limit = min(int(limit), 100)

    return frappe.get_list(
        "Equipment Register",
        filters=filter_dict,
        fields=["name", "equipment_id", "equipment_name", "equipment_category",
                "equipment_status", "project", "operator_required"],
        order_by="equipment_id asc",
        limit_page_length=limit,
        limit_start=offset
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

    try:
        doc.save()
    except frappe.ValidationError as e:
        frappe.throw(_("Validation error: {0}").format(str(e)))
    except Exception as e:
        logger.error(f"Failed to update equipment status: {e}")
        frappe.throw(_("Failed to update equipment status: {0}").format(str(e)))

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

    log_id = frappe.generate_hash("Equipment Utilization Log", 10)

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

    try:
        doc.insert()
    except frappe.DuplicateEntryError:
        frappe.throw(_("Utilization log with this ID already exists"))
    except frappe.ValidationError as e:
        frappe.throw(_("Validation error: {0}").format(str(e)))
    except Exception as e:
        logger.error(f"Failed to log equipment utilization: {e}")
        frappe.throw(_("Failed to log utilization: {0}").format(str(e)))

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

    schedule_id = frappe.generate_hash("Equipment Maintenance Schedule", 10)

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

    try:
        doc.insert()
    except frappe.DuplicateEntryError:
        frappe.throw(_("Maintenance schedule with this ID already exists"))
    except frappe.ValidationError as e:
        frappe.throw(_("Validation error: {0}").format(str(e)))
    except Exception as e:
        logger.error(f"Failed to create maintenance schedule: {e}")
        frappe.throw(_("Failed to create schedule: {0}").format(str(e)))

    return {
        "name": doc.name,
        "schedule_id": doc.schedule_id,
        "next_service_date": next_service
    }


@frappe.whitelist()
def get_maintenance_alerts(limit=50, offset=0):
    """
    Get upcoming maintenance alerts.

    Args:
        limit (int): Page size (max 100)
        offset (int): Starting offset

    Returns:
        list: Maintenance due alerts
    """
    frappe.has_permission("Equipment Maintenance Schedule", "read", throw=True)

    upcoming = add_days(today(), 7)

    limit = min(int(limit), 100)

    return frappe.get_list(
        "Equipment Maintenance Schedule",
        filters={
            "is_scheduled": 1,
            "alerts_enabled": 1,
            "next_service_date": ["<=", upcoming]
        },
        fields=["name", "schedule_id", "equipment", "maintenance_type",
                "description", "next_service_date", "alert_days_before"],
        order_by="next_service_date asc",
        limit_page_length=limit,
        limit_start=offset
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

    movement_id = frappe.generate_hash("Equipment Movement", 10)

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

    try:
        doc.insert()
    except frappe.DuplicateEntryError:
        frappe.throw(_("Movement with this ID already exists"))
    except frappe.ValidationError as e:
        frappe.throw(_("Validation error: {0}").format(str(e)))
    except Exception as e:
        logger.error(f"Failed to record equipment movement: {e}")
        frappe.throw(_("Failed to record movement: {0}").format(str(e)))

    # Update equipment location if movement type is Transfer
    if data.get("movement_type") == "Transfer" and data.get("to_project"):
        frappe.has_permission("Equipment Register", "write", throw=True)
        eq_doc = frappe.get_doc("Equipment Register", equipment_name)
        eq_doc.project = data.get("to_project")
        eq_doc.current_location = data.get("to_project")
        try:
            eq_doc.save()
        except frappe.ValidationError as e:
            frappe.throw(_("Validation error: {0}").format(str(e)))
        except Exception as e:
            logger.error(f"Failed to update equipment location: {e}")
            frappe.throw(_("Failed to update equipment location: {0}").format(str(e)))

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
    frappe.has_permission("Equipment Register", "read", throw=True)

    from frappe.utils import add_days as add_days_util

    cutoff = add_days_util(today(), -days)

    filters = {"log_date": [">=", cutoff]}
    if project:
        filters["project"] = project

    # Use SQL GROUP BY for aggregation instead of Python looping
    result = frappe.db.sql("""
        SELECT
            equipment,
            SUM(hours_worked) as total_hours,
            SUM(idle_hours) as total_idle,
            SUM(fuel_consumed_ltr) as total_fuel,
            SUM(total_cost) as total_cost
        FROM `tabEquipment Utilization Log`
        WHERE log_date >= %s {project_filter}
        GROUP BY equipment
    """.format(project_filter="AND project = %(project)s" if project else ""),
        {"cutoff": cutoff, "project": project} if project else {"cutoff": cutoff},
        as_dict=True
    )

    # Calculate utilization rates
    by_equipment = {}
    for row in result:
        total = row.total_hours + row.total_idle
        by_equipment[row.equipment] = {
            "hours": row.total_hours or 0,
            "idle": row.total_idle or 0,
            "fuel": row.total_fuel or 0,
            "cost": row.total_cost or 0,
            "utilization_rate": round((row.total_hours / total * 100) if total > 0 else 0, 2)
        }

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
    frappe.has_permission("Equipment Register", "read", throw=True)

    filters = {}
    if project:
        filters["project"] = project

    equipment_list = frappe.get_list(
        "Equipment Register",
        filters=filters,
        fields=["name", "equipment_id", "ownership_type", "lease_rate",
                "average_fuel_consumption", "project"],
        limit=50,
        offset=0
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

    subcontractor_id = frappe.generate_hash("Subcontractor Profile", 10)

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

    try:
        doc.insert()
    except frappe.DuplicateEntryError:
        frappe.throw(_("Subcontractor with this ID already exists"))
    except frappe.ValidationError as e:
        frappe.throw(_("Validation error: {0}").format(str(e)))
    except Exception as e:
        logger.error(f"Failed to create subcontractor profile: {e}")
        frappe.throw(_("Failed to create subcontractor: {0}").format(str(e)))

    return {
        "name": doc.name,
        "subcontractor_id": doc.subcontractor_id
    }


@frappe.whitelist()
def get_subcontractor_list(active_only=True, limit=20, offset=0):
    """
    Get subcontractor list.

    Args:
        active_only (bool): Filter active only
        limit (int): Page size (max 100)
        offset (int): Starting offset

    Returns:
        list: Subcontractors
    """
    frappe.has_permission("Subcontractor Profile", "read", throw=True)

    filters = {}
    if active_only:
        filters["status"] = "Active"

    limit = min(int(limit), 100)

    return frappe.get_list(
        "Subcontractor Profile",
        filters=filters,
        fields=["name", "subcontractor_id", "subcontractor_name", "trade_category",
                "safety_rating", "quality_rating", "insurance_expiry", "status"],
        order_by="subcontractor_name asc",
        limit_page_length=limit,
        limit_start=offset
    )


@frappe.whitelist()
def get_expiring_insurance(days=30, limit=50, offset=0):
    """
    Get subcontractors with expiring insurance.

    Args:
        days (int): Days to check
        limit (int): Page size (max 100)
        offset (int): Starting offset

    Returns:
        list: Expiring insurance alerts
    """
    frappe.has_permission("Subcontractor Profile", "read", throw=True)

    cutoff = add_days(today(), days)

    limit = min(int(limit), 100)

    return frappe.get_list(
        "Subcontractor Profile",
        filters={
            "status": "Active",
            "insurance_expiry": ["<=", cutoff],
            "blacklist": 0
        },
        fields=["name", "subcontractor_id", "subcontractor_name", "insurance_expiry"],
        order_by="insurance_expiry asc",
        limit_page_length=limit,
        limit_start=offset
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

    work_order_id = frappe.generate_hash("Subcontractor Work Order", 10)

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

    try:
        doc.insert()
    except frappe.DuplicateEntryError:
        frappe.throw(_("Work order with this ID already exists"))
    except frappe.ValidationError as e:
        frappe.throw(_("Validation error: {0}").format(str(e)))
    except Exception as e:
        logger.error(f"Failed to create work order: {e}")
        frappe.throw(_("Failed to create work order: {0}").format(str(e)))

    return {
        "name": doc.name,
        "work_order_id": doc.work_order_id
    }


@frappe.whitelist()
def get_subcontractor_work_orders(subcontractor=None, project=None, limit=20, offset=0):
    """
    Get work orders.

    Args:
        subcontractor (str, optional): Filter by subcontractor
        project (str, optional): Filter by project
        limit (int): Page size (max 100)
        offset (int): Starting offset

    Returns:
        list: Work orders
    """
    frappe.has_permission("Subcontractor Profile", "read", throw=True)

    filters = {}
    if subcontractor:
        filters["subcontractor"] = subcontractor
    if project:
        filters["project"] = project

    limit = min(int(limit), 100)

    return frappe.get_list(
        "Subcontractor Work Order",
        filters=filters,
        fields=["name", "work_order_id", "project", "subcontractor",
                "contract_value", "status", "start_date", "end_date"],
        order_by="creation desc",
        limit_page_length=limit,
        limit_start=offset
    )
