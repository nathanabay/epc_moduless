"""
Dashboard API Module

REST API endpoints for EPC dashboard and KPI operations.
"""

import frappe
from frappe import _
from frappe.utils import today, add_days, flt, now_datetime
from epc_modules.utils import get_epc_logger
from epc_modules.utils.billing_calculator import BillingEngine

logger = get_epc_logger(__name__)


@frappe.whitelist()
def get_management_dashboard():
    """
    Get management dashboard KPIs.

    Returns:
        dict: Dashboard metrics
    """
    # Active projects count
    active_projects = frappe.get_all(
        "Project",
        filters={"status": "Active", "is_epc_project": 1},
        fields=["name", "percent_complete", "contract_value", "project_typology"],
        order_by="creation desc"
    )

    # Calculate aggregate metrics
    total_projects = len(active_projects)
    avg_progress = sum(p.get("percent_complete", 0) or 0 for p in active_projects) / total_projects if total_projects > 0 else 0
    total_contract_value = sum(flt(p.get("contract_value", 0)) for p in active_projects)

    # By typology breakdown
    by_typology = {}
    for p in active_projects:
        typology = p.get("project_typology", "Unknown")
        if typology not in by_typology:
            by_typology[typology] = {"count": 0, "total_value": 0, "avg_progress": 0}
        by_typology[typology]["count"] += 1
        by_typology[typology]["total_value"] += flt(p.get("contract_value", 0))

    # Calculate billing totals
    total_certified = frappe.db.sql("""
        SELECT SUM(total_invoice_value)
        FROM `tabRA Bill`
        WHERE docstatus = 1
    """, as_dict=0)[0][0] or 0

    total_pending = frappe.db.sql("""
        SELECT SUM(gross_certified_value)
        FROM `tabRA Bill`
        WHERE docstatus = 0
    """, as_dict=0)[0][0] or 0

    # NCR metrics
    open_ncrs = frappe.db.count("Non-Conformance Report", {
        "status": ["in", ["Open", "In Progress"]]
    })

    critical_ncrs = frappe.db.count("Non-Conformance Report", {
        "status": ["in", ["Open", "In Progress"]],
        "severity": "Critical"
    })

    # Quality metrics
    pending_mb_certification = frappe.db.count("Measurement Book", {
        "certification_status": "Submitted"
    })

    pending_itp_inspections = frappe.db.count("Inspection Record", {
        "status": "Pending"
    })

    # Resource metrics
    total_labor = 0  # Would aggregate from DPR entries
    total_equipment = frappe.db.count("Equipment Register", {
        "equipment_status": "In Use"
    })

    return {
        "timestamp": now_datetime(),
        "projects": {
            "active_count": total_projects,
            "avg_progress": round(avg_progress, 2),
            "total_contract_value": total_contract_value,
            "by_typology": by_typology
        },
        "billing": {
            "total_certified": total_certified,
            "total_pending": total_pending,
            "certification_rate": round((total_certified / total_contract_value * 100) if total_contract_value > 0 else 0, 2)
        },
        "quality": {
            "open_ncrs": open_ncrs,
            "critical_ncrs": critical_ncrs,
            "pending_mb_certification": pending_mb_certification,
            "pending_itp_inspections": pending_itp_inspections,
            "is_blocked": critical_ncrs > 0
        },
        "resources": {
            "active_equipment": total_equipment,
            "labor_on_site": total_labor
        }
    }


@frappe.whitelist()
def get_project_dashboard_kpis(project):
    """
    Get detailed KPIs for a specific project.

    Args:
        project (str): Project name

    Returns:
        dict: Project dashboard metrics
    """
    if not frappe.db.exists("Project", project):
        frappe.throw(_("Project {0} does not exist").format(project))

    project_doc = frappe.get_doc("Project", project)

    # Progress metrics
    boq_items = frappe.get_all(
        "Custom BOQ",
        filters={"parent": project},
        fields=["name", "total_value", "measurement_method"]
    )

    total_boq_value = sum(flt(item.get("total_value", 0)) for item in boq_items)

    # WBS metrics
    wbs_items = frappe.get_all(
        "WBS Item",
        filters={"project": project},
        fields=["name", "physical_progress", "status"]
    )

    completed_wbs = sum(1 for w in wbs_items if w.get("status") == "Completed")
    in_progress_wbs = sum(1 for w in wbs_items if w.get("status") == "In Progress")

    # DPR metrics
    today_dprs = frappe.get_all(
        "Daily Progress Report",
        filters={"project": project, "report_date": today()},
        fields=["name"]
    )

    # Quality metrics
    itp_summary = frappe.db.get_value(
        "Project Inspection Plan",
        {"project": project, "status": ["!=", "Completed"]},
        "COUNT(*)"
    ) or 0

    open_ncrs = frappe.db.count("Non-Conformance Report", {
        "project": project,
        "status": ["in", ["Open", "In Progress"]]
    })

    critical_ncrs = frappe.db.count("Non-Conformance Report", {
        "project": project,
        "severity": "Critical",
        "status": ["in", ["Open", "In Progress"]]
    })

    # Billing summary
    billing_summary = BillingEngine.get_billing_summary(project)

    # Measurement book status
    certified_mbs = frappe.db.count("Measurement Book", {
        "project": project,
        "certification_status": "Certified"
    })
    pending_mbs = frappe.db.count("Measurement Book", {
        "project": project,
        "certification_status": "Submitted"
    })

    # Labor metrics (from DPR)
    labor_today = frappe.db.sql("""
        SELECT SUM(labor_count)
        FROM `tabDaily Progress Report`
        WHERE project = %s AND report_date = %s
    """, (project, today()))[0][0] or 0

    return {
        "project": project,
        "project_name": project_doc.project_name,
        "typology": project_doc.project_typology,
        "status": project_doc.status,

        "progress": {
            "percent_complete": flt(project_doc.percent_complete or 0),
            "total_boq_value": total_boq_value,
            "wbs_items": len(wbs_items),
            "completed_wbs": completed_wbs,
            "in_progress_wbs": in_progress_wbs,
            "today_dprs": len(today_dprs)
        },

        "quality": {
            "itps_active": itp_summary,
            "open_ncrs": open_ncrs,
            "critical_ncrs": critical_ncrs,
            "is_blocked": critical_ncrs > 0
        },

        "billing": billing_summary,

        "measurement_books": {
            "certified": certified_mbs,
            "pending": pending_mbs
        },

        "resources": {
            "labor_today": labor_today
        }
    }


@frappe.whitelist()
def get_project_progress_trend(project, months=6):
    """
    Get project progress trend over time.

    Args:
        project (str): Project name
        months (int): Number of months to include

    Returns:
        list: Progress data points
    """
    if not frappe.db.exists("Project", project):
        frappe.throw(_("Project {0} does not exist").format(project))

    from frappe.utils import get_datetime, date_diff

    # Get DPR dates for progress entries
    dpr_entries = frappe.get_all(
        "Daily Progress Report",
        filters={"project": project},
        fields=["report_date", "overall_progress"],
        order_by="report_date asc"
    )

    trend = []
    cumulative_progress = 0
    count = 0

    for entry in dpr_entries:
        if entry.overall_progress:
            count += 1
            cumulative_progress += entry.overall_progress
            trend.append({
                "date": entry.report_date,
                "progress": entry.overall_progress,
                "avg_progress": round(cumulative_progress / count, 2)
            })

    return {
        "project": project,
        "data_points": len(trend),
        "trend": trend[-30:] if len(trend) > 30 else trend  # Last 30 entries
    }


@frappe.whitelist()
def get_billing_trend(months=12):
    """
    Get billing trend across all projects.

    Args:
        months (int): Number of months to include

    Returns:
        list: Monthly billing data
    """
    # Get monthly RA bill totals
    monthly_data = frappe.db.sql("""
        SELECT
            DATE_FORMAT(billing_period_end, '%%Y-%%m') as month,
            COUNT(*) as bill_count,
            SUM(gross_certified_value) as gross_value,
            SUM(advance_recovered) as advance_recovery,
            SUM(vat_amount) as vat_amount,
            SUM(total_invoice_value) as total_value
        FROM `tabRA Bill`
        WHERE docstatus = 1
        GROUP BY DATE_FORMAT(billing_period_end, '%%Y-%%m')
        ORDER BY month DESC
        LIMIT %s
    """, (months,), as_dict=1)

    return {
        "periods": months,
        "data": monthly_data
    }


@frappe.whitelist()
def get_quality_metrics(project=None):
    """
    Get quality metrics for dashboard.

    Args:
        project (str, optional): Filter by project

    Returns:
        dict: Quality metrics
    """
    filters = {}
    if project:
        filters["project"] = project

    # NCR statistics
    if project:
        ncr_stats = frappe.db.sql("""
            SELECT
                status,
                severity,
                COUNT(*) as count
            FROM `tabNon-Conformance Report`
            WHERE project = %s
            GROUP BY status, severity
        """, (project,), as_dict=1)
    else:
        ncr_stats = frappe.db.sql("""
            SELECT
                status,
                severity,
                COUNT(*) as count
            FROM `tabNon-Conformance Report`
            GROUP BY status, severity
        """, as_dict=1)

    ncr_summary = {
        "total": 0,
        "open": 0,
        "in_progress": 0,
        "closed": 0,
        "critical": 0,
        "major": 0,
        "minor": 0
    }

    for stat in ncr_stats:
        ncr_summary["total"] += stat.count
        if stat.status == "Open":
            ncr_summary["open"] += stat.count
        elif stat.status == "In Progress":
            ncr_summary["in_progress"] += stat.count
        elif stat.status == "Closed":
            ncr_summary["closed"] += stat.count

        if stat.severity == "Critical":
            ncr_summary["critical"] += stat.count
        elif stat.severity == "Major":
            ncr_summary["major"] += stat.count
        elif stat.severity == "Minor":
            ncr_summary["minor"] += stat.count

    # ITP statistics
    if project:
        itp_stats = frappe.db.sql("""
            SELECT
                status,
                COUNT(*) as count
            FROM `tabProject Inspection Plan`
            WHERE project = %s
            GROUP BY status
        """, (project,), as_dict=1)
    else:
        itp_stats = frappe.db.sql("""
            SELECT
                status,
                COUNT(*) as count
            FROM `tabProject Inspection Plan`
            GROUP BY status
        """, as_dict=1)

    itp_summary = {
        "total": 0,
        "active": 0,
        "completed": 0
    }

    for stat in itp_stats:
        itp_summary["total"] += stat.count
        if stat.status in ["Active", "In Progress"]:
            itp_summary["active"] += stat.count
        elif stat.status == "Completed":
            itp_summary["completed"] += stat.count

    # Cube test statistics
    if project:
        cube_stats = frappe.db.sql("""
            SELECT
                is_pass,
                COUNT(*) as count
            FROM `tabCube Test Result`
            WHERE project = %s
            GROUP BY is_pass
        """, (project,), as_dict=1)
    else:
        cube_stats = frappe.db.sql("""
            SELECT
                is_pass,
                COUNT(*) as count
            FROM `tabCube Test Result`
            GROUP BY is_pass
        """, as_dict=1)

    cube_summary = {
        "total": 0,
        "passing": 0,
        "failing": 0
    }

    for stat in cube_stats:
        cube_summary["total"] += stat.count
        if stat.is_pass:
            cube_summary["passing"] += stat.count
        else:
            cube_summary["failing"] += stat.count

    return {
        "ncr": ncr_summary,
        "itp": itp_summary,
        "cube_tests": cube_summary,
        "project_filter": project
    }


@frappe.whitelist()
def get_resource_utilization(project=None):
    """
    Get resource utilization metrics.

    Args:
        project (str, optional): Filter by project

    Returns:
        dict: Resource utilization
    """
    filters = {}
    if project:
        filters["project"] = project

    # Equipment utilization
    equipment_stats = frappe.db.sql("""
        SELECT
            equipment_status,
            COUNT(*) as count
        FROM `tabEquipment Register`
        GROUP BY equipment_status
    """, as_dict=1)

    equipment = {
        "total": 0,
        "available": 0,
        "in_use": 0,
        "maintenance": 0
    }

    for stat in equipment_stats:
        equipment["total"] += stat.count
        if stat.equipment_status == "Available":
            equipment["available"] += stat.count
        elif stat.equipment_status == "In Use":
            equipment["in_use"] += stat.count
        elif stat.equipment_status in ["Under Maintenance", "Under Repair"]:
            equipment["maintenance"] += stat.count

    # Labor metrics from DPR
    if project:
        labor_stats = frappe.db.sql("""
            SELECT
                SUM(labor_count) as total_labor,
                SUM(equipment_count) as total_equipment,
                AVG(labor_count) as avg_labor
            FROM `tabDaily Progress Report`
            WHERE report_date >= DATE_SUB(%s, INTERVAL 30 DAY)
            AND project = %s
        """, (today(), project), as_dict=1)
    else:
        labor_stats = frappe.db.sql("""
            SELECT
                SUM(labor_count) as total_labor,
                SUM(equipment_count) as total_equipment,
                AVG(labor_count) as avg_labor
            FROM `tabDaily Progress Report`
            WHERE report_date >= DATE_SUB(%s, INTERVAL 30 DAY)
        """, (today(),), as_dict=1)

    labor = labor_stats[0] if labor_stats else {}

    return {
        "equipment": equipment,
        "labor": {
            "current_on_site": flt(labor.get("total_labor", 0)),
            "avg_daily": flt(labor.get("avg_labor", 0))
        },
        "utilization_rate": round((equipment["in_use"] / equipment["total"] * 100) if equipment["total"] > 0 else 0, 2)
    }


@frappe.whitelist()
def get_notification_alerts():
    """
    Get notification alerts for dashboard.

    Returns:
        list: Active alerts
    """
    alerts = []

    # Overdue NCRs
    overdue_ncrs = frappe.get_all(
        "Non-Conformance Report",
        filters={
            "status": ["in", ["Open", "In Progress"]],
            "target_close_date": ["<", today()]
        },
        fields=["name", "ncr_number", "severity", "target_close_date", "project"]
    )

    for ncr in overdue_ncrs:
        alerts.append({
            "type": "ncr_overdue",
            "severity": ncr.severity,
            "title": f"Overdue NCR: {ncr.ncr_number}",
            "description": f"Target date was {ncr.target_close_date}",
            "reference": ncr.name,
            "project": ncr.project
        })

    # Pending certifications
    pending_mbs = frappe.get_all(
        "Measurement Book",
        filters={"certification_status": "Submitted"},
        fields=["name", "mb_code", "project"],
        limit=5
    )

    for mb in pending_mbs:
        alerts.append({
            "type": "mb_pending",
            "severity": "info",
            "title": f"Pending MB: {mb.mb_code}",
            "description": "Awaiting certification",
            "reference": mb.name,
            "project": mb.project
        })

    # Equipment maintenance due
    maintenance_due = frappe.get_all(
        "Equipment Maintenance Schedule",
        filters={"next_service_date": ["<=", add_days(today(), 7)]},
        fields=["name", "equipment", "maintenance_type", "next_service_date"]
    )

    for m in maintenance_due:
        alerts.append({
            "type": "maintenance_due",
            "severity": "warning",
            "title": f"Maintenance Due: {m.maintenance_type}",
            "description": f"Due on {m.next_service_date}",
            "reference": m.name
        })

    # Insurance/expiry alerts
    expiring_contracts = frappe.get_all(
        "Subcontractor Profile",
        filters={"insurance_expiry": ["between", [today(), add_days(today(), 30)]]},
        fields=["name", "subcontractor_name", "insurance_expiry"]
    )

    for c in expiring_contracts:
        alerts.append({
            "type": "contract_expiry",
            "severity": "warning",
            "title": f"Insurance Expiring: {c.subcontractor_name}",
            "description": f"Expires on {c.insurance_expiry}",
            "reference": c.name
        })

    return {
        "count": len(alerts),
        "alerts": alerts,
        "critical_count": sum(1 for a in alerts if a.get("severity") == "Critical"),
        "warning_count": sum(1 for a in alerts if a.get("severity") == "warning"),
        "info_count": sum(1 for a in alerts if a.get("severity") == "info")
    }


@frappe.whitelist()
def get_project_health_score(project):
    """
    Calculate overall project health score.

    Args:
        project (str): Project name

    Returns:
        dict: Health score breakdown
    """
    if not frappe.db.exists("Project", project):
        frappe.throw(_("Project {0} does not exist").format(project))

    project_doc = frappe.get_doc("Project", project)
    score = 100
    issues = []

    # Schedule health (based on DPR submissions)
    dpr_count = frappe.db.count("Daily Progress Report", {"project": project})
    expected_days = 1  # At least one DPR per day
    # Simplified - would need actual date range calculation
    if dpr_count == 0:
        score -= 20
        issues.append("No DPR entries recorded")

    # Quality health (NCRs)
    critical_ncrs = frappe.db.count("Non-Conformance Report", {
        "project": project,
        "severity": "Critical",
        "status": ["in", ["Open", "In Progress"]]
    })

    if critical_ncrs > 0:
        score -= 25
        issues.append(f"{critical_ncrs} Critical NCR(s) open")

    open_ncrs = frappe.db.count("Non-Conformance Report", {
        "project": project,
        "status": ["in", ["Open", "In Progress"]]
    })

    if open_ncrs > 5:
        score -= 10
        issues.append(f"{open_ncrs} NCR(s) open")

    # Billing health
    billing_summary = BillingEngine.get_billing_summary(project)
    billing_pct = billing_summary.get("billing_percentage", 0)
    progress_pct = flt(project_doc.percent_complete or 0)

    # Billing should be within 15% of progress
    if billing_pct < progress_pct - 15:
        score -= 15
        issues.append("Billing behind schedule")

    # Scope health (BOQ coverage)
    boq_value = frappe.db.sql("""
        SELECT SUM(total_value)
        FROM `tabCustom BOQ`
        WHERE parent = %s
    """, project)[0][0] or 0

    if boq_value == 0:
        score -= 15
        issues.append("No BOQ items defined")

    return {
        "project": project,
        "health_score": max(0, score),
        "status": "Good" if score >= 80 else "Warning" if score >= 50 else "Critical",
        "issues": issues,
        "factors": {
            "schedule": 20 if dpr_count > 0 else 0,
            "quality": 25 if critical_ncrs == 0 else 0,
            "billing": 15 if billing_pct >= progress_pct - 15 else 0,
            "scope": 15 if boq_value > 0 else 0
        }
    }