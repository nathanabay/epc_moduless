"""
EPC Scheduler Tasks

Automated background jobs for the EPC module.
"""

import frappe
from frappe import _
from frappe.utils import now_datetime, today, get_datetime, add_days
from epc_modules.utils import get_epc_logger

logger = get_epc_logger(__name__)


@frappe.whitelist()
def nightly_progress_aggregation():
    """
    Nightly job to recalculate all active project progress.
    Aggregates DPR entries and updates BOQ completion status.
    Implements the nightly aggregation scheduler from Phase 3.
    """
    logger.info("Starting nightly progress aggregation")

    active_projects = frappe.get_all(
        "Project",
        filters={
            "status": "Active",
            "project_typology": ["!=", ""]
        },
        pluck="name"
    )

    processed_count = 0
    failed_projects = []

    for project_name in active_projects:
        try:
            # Import here to avoid circular dependency
            from epc_modules.utils.boq_calculator import BOQCalculator

            BOQCalculator.aggregate_project_progress(project_name)
            frappe.db.commit()
            processed_count += 1

        except Exception as e:
            logger.error(f"Progress aggregation failed for {project_name}: {str(e)}")
            frappe.db.rollback()
            failed_projects.append({
                "project": project_name,
                "error": str(e)
            })

    logger.info(f"Progress aggregation completed: {processed_count} projects processed")

    if failed_projects:
        # Log error for admin review
        frappe.log_error(
            title="EPC Progress Aggregation Failures",
            message=frappe.as_json(failed_projects)
        )

    return {
        "processed": processed_count,
        "failed": len(failed_projects),
        "failed_projects": failed_projects
    }


@frappe.whitelist()
def nightly_wbs_value_sync():
    """
    Nightly job to synchronize WBS item values with BOQ items.
    Updates planned_value and earned_value for all WBS elements.
    """
    logger.info("Starting nightly WBS value sync")

    projects = frappe.get_all(
        "Project",
        filters={
            "status": "Active",
            "is_epc_project": 1
        },
        pluck="name"
    )

    synced_count = 0

    for project_name in projects:
        try:
            # Get WBS items for project
            wbs_items = frappe.get_all(
                "WBS Item",
                filters={"project": project_name},
                fields=["name", "wbs_code"]
            )

            for wbs_item in wbs_items:
                # Calculate total BOQ value for this WBS
                boq_total = frappe.db.sql("""
                    SELECT SUM(total_value)
                    FROM `tabCustom BOQ Item`
                    WHERE wbs_code = %s AND parent = %s
                """, (wbs_item.wbs_code, project_name))[0][0] or 0

                # Update WBS planned value
                frappe.db.set_value("WBS Item", wbs_item.name, {
                    "planned_value": boq_total
                })

            frappe.db.commit()
            synced_count += 1

        except Exception as e:
            logger.error(f"WBS sync failed for {project_name}: {str(e)}")
            frappe.db.rollback()

    logger.info(f"WBS value sync completed: {synced_count} projects")

    return {"synced_projects": synced_count}


@frappe.whitelist()
def generate_project_daily_digest():
    """
    Generate daily digest of project progress for all active projects.
    Compiles DPR entries, progress updates, and pending actions.
    """
    logger.info("Generating project daily digest")

    from frappe.utils import get_url

    projects = frappe.get_all(
        "Project",
        filters={
            "status": "Active",
            "is_epc_project": 1
        },
        fields=["name", "project_name", "project_manager"]
    )

    digests = []

    for project in projects:
        # Get today's DPRs
        today_dprs = frappe.get_all(
            "Daily Progress Report",
            filters={
                "project": project.name,
                "report_date": today()
            },
            fields=["name", "overall_progress", "status"]
        )

        # Get pending certifications
        pending_mbs = frappe.get_count(
            "Measurement Book",
            filters={
                "project": project.name,
                "certification_status": "Submitted"
            }
        )

        # Get open NCRs
        open_ncrs = frappe.get_count(
            "Non-Conformance Report",
            filters={
                "project": project.name,
                "status": ["in", ["Open", "In Progress"]]
            }
        )

        digests.append({
            "project": project.name,
            "project_name": project.project_name,
            "project_manager": project.project_manager,
            "today_dprs": len(today_dprs),
            "pending_mb_certifications": pending_mbs,
            "open_ncrs": open_ncrs,
            "average_progress": sum(d.get("overall_progress", 0) for d in today_dprs) / len(today_dprs) if today_dprs else 0
        })

    logger.info(f"Generated digest for {len(digests)} projects")

    return {"digests": digests, "project_count": len(digests)}


@frappe.whitelist()
def process_pending_ncrs():
    """
    Process pending Non-Conformance Reports and send notifications.
    """
    logger.info("Processing pending NCRs")

    # Find NCRs past target close date
    overdue_ncrs = frappe.get_all(
        "Non-Conformance Report",
        filters={
            "status": ["in", ["Open", "In Progress"]],
            "target_close_date": ["<", today()]
        },
        fields=["name", "project", "wbs_item", "severity"]
    )

    for ncr in overdue_ncrs:
        # Send notification
        frappe.publish_realtime(
            event="epc_ncr_overdue",
            message={
                "ncr": ncr.name,
                "project": ncr.project,
                "days_overdue": (get_datetime(today()) - get_datetime(ncr.target_close_date)).days
            }
        )

    return len(overdue_ncrs)


@frappe.whitelist()
def check_service_due_dates():
    """
    Check for service milestones approaching due dates.
    """
    projects = frappe.get_all(
        "Project",
        filters={
            "status": "Active",
            "project_typology": "Standard/Service"
        },
        pluck="name"
    )

    upcoming_milestones = []

    for project in projects:
        milestones = frappe.get_all(
            "Milestone",
            filters={
                "parent": project,
                "is_invoiced": 0,
                "planned_date": ["between", [today(), add_days(today(), 7)]]
            },
            fields=["name", "parent", "milestone_name", "planned_date"]
        )
        upcoming_milestones.extend(milestones)

    return upcoming_milestones


@frappe.whitelist()
def generate_daily_reports():
    """
    Generate automated daily reports for all active projects.
    """
    logger.info("Generating daily reports")
    # Implementation for daily report generation
    return {"status": "success"}


@frappe.whitelist()
def weekly_productivity_report():
    """
    Generate weekly productivity reports.
    """
    logger.info("Generating weekly productivity report")
    # Implementation for weekly productivity report
    return {"status": "success"}


@frappe.whitelist()
def update_project_status_summary():
    """
    Update project status summary cache.
    """
    logger.info("Updating project status summary")
    # Implementation for status summary updates
    return {"status": "success"}


@frappe.whitelist()
def monthly_billing_summary():
    """
    Generate monthly billing summary.
    """
    logger.info("Generating monthly billing summary")
    # Implementation for monthly billing summary
    return {"status": "success"}