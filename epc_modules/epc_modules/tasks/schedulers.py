"""
EPC Scheduler Tasks

Automated background jobs for the EPC module.
"""

import frappe
from frappe import _
from frappe.utils import now_datetime, today, get_datetime, add_days
from epc_modules.utils import get_epc_logger

logger = get_epc_logger(__name__)


def process_pending_ra_bills():
	"""
	Process pending RA Bills for all active EPC projects.
	Checks for overdue NCRs and sends notifications.
	"""
	logger.info("Processing pending RA bills and NCRs")

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

	logger.info(f"Processed {len(overdue_ncrs)} overdue NCRs")

	try:
		frappe.db.commit()
	except Exception:
		frappe.log_error(frappe.get_traceback(), "RA Bill Processing Commit Error")

	return len(overdue_ncrs)


def update_project_progress():
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


def check_overdue_milestones():
	"""
	Check for milestones approaching due dates and overdue milestones.
	"""
	logger.info("Checking overdue milestones")

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

	logger.info(f"Found {len(upcoming_milestones)} upcoming/overdue milestones")

	try:
		frappe.db.commit()
	except Exception:
		frappe.log_error(frappe.get_traceback(), "Milestone Check Commit Error")

	return upcoming_milestones


def generate_project_reports():
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
		fields=["name", "project_name", "owner"]
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
			"project_manager": project.get("owner"),
			"today_dprs": len(today_dprs),
			"pending_mb_certifications": pending_mbs,
			"open_ncrs": open_ncrs,
			"average_progress": sum(d.get("overall_progress", 0) for d in today_dprs) / len(today_dprs) if today_dprs else 0
		})

	logger.info(f"Generated digest for {len(digests)} projects")

	try:
		frappe.db.commit()
	except Exception:
		frappe.log_error(frappe.get_traceback(), "Project Reports Commit Error")

	return {"digests": digests, "project_count": len(digests)}


def archive_completed_projects():
	"""
	Update project status summary and archive completed projects.
	"""
	logger.info("Archiving completed projects")

	# Find completed projects that need archiving
	completed_projects = frappe.get_all(
		"Project",
		filters={
			"status": "Completed",
			"is_epc_project": 1
		},
		pluck="name"
	)

	archived_count = 0

	for project_name in completed_projects:
		try:
			# Sync WBS values for final state
			wbs_items = frappe.get_all(
				"WBS Item",
				filters={"project": project_name},
				fields=["name", "wbs_code"]
			)

			for wbs_item in wbs_items:
				boq_total = frappe.db.sql("""
					SELECT SUM(total_value)
					FROM `tabCustom BOQ`
					WHERE wbs_code = %s AND parent = %s
				""", (wbs_item.wbs_code, project_name))[0][0] or 0

				frappe.db.set_value("WBS Item", wbs_item.name, {
					"planned_value": boq_total
				})

			archived_count += 1

		except Exception as e:
			logger.error(f"Archive failed for {project_name}: {str(e)}")
			frappe.db.rollback()

	try:
		frappe.db.commit()
	except Exception:
		frappe.log_error(frappe.get_traceback(), "Archive Projects Commit Error")

	logger.info(f"Archived {archived_count} completed projects")
	return {"archived": archived_count}


def calculate_retention_summary():
	"""
	Generate monthly billing and retention summary.
	"""
	logger.info("Calculating retention summary")

	# Get all active EPC projects
	projects = frappe.get_all(
		"Project",
		filters={
			"status": "Active",
			"is_epc_project": 1
		},
		fields=["name", "project_name"]
	)

	retention_data = []

	for project in projects:
		try:
			# Calculate retention amounts from billing records
			retention_amount = frappe.db.sql("""
				SELECT SUM(retention_amount)
				FROM `tabRA Bill`
				WHERE project = %s AND docstatus = 1
			""", (project.name,))[0][0] or 0

			retention_data.append({
				"project": project.name,
				"project_name": project.project_name,
				"total_retention": retention_amount
			})

		except Exception as e:
			logger.error(f"Retention calculation failed for {project.name}: {str(e)}")

	try:
		frappe.db.commit()
	except Exception:
		frappe.log_error(frappe.get_traceback(), "Retention Summary Commit Error")

	logger.info(f"Retention summary calculated for {len(retention_data)} projects")
	return {"retention_data": retention_data, "project_count": len(retention_data)}
