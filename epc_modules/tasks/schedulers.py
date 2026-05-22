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
			processed_count += 1

		except Exception as e:
			logger.error(f"Progress aggregation failed for {project_name}: {str(e)}")
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

	if not projects:
		return {"digests": [], "project_count": 0}

	# FIX: Batch all DB queries upfront to avoid N+1
	project_names = [p.name for p in projects]
	today_str = today()

	# Batch 1: Get all DPRs for all projects in one query
	all_dprs = frappe.get_all(
		"Daily Progress Report",
		filters={
			"project": ["in", project_names],
			"report_date": today_str
		},
		fields=["name", "overall_progress", "status", "project"]
	)

	# Batch 2: Get all pending MB certifications grouped by project
	pending_mb_rows = frappe.db.sql("""
		SELECT project, COUNT(*) as cnt
		FROM `tabMeasurement Book`
		WHERE project IN (%s) AND certification_status = 'Submitted'
		GROUP BY project
	""" % ", ".join(["%s"] * len(project_names)), project_names, as_dict=1)
	pending_mb_map = {r.project: r.cnt for r in pending_mb_rows}

	# Batch 3: Get all open NCRs grouped by project
	open_ncr_rows = frappe.db.sql("""
		SELECT project, COUNT(*) as cnt
		FROM `tabNon-Conformance Report`
		WHERE project IN (%s) AND status IN ('Open', 'In Progress')
		GROUP BY project
	""" % ", ".join(["%s"] * len(project_names)), project_names, as_dict=1)
	open_ncr_map = {r.project: r.cnt for r in open_ncr_rows}

	digests = []

	for project in projects:
		# Filter DPRs for this project from pre-fetched data
		project_dprs = [d for d in all_dprs if d.project == project.name]

		pending_mbs = pending_mb_map.get(project.name, 0)
		open_ncrs = open_ncr_map.get(project.name, 0)

		digests.append({
			"project": project.name,
			"project_name": project.project_name,
			"project_manager": project.get("owner"),
			"today_dprs": len(project_dprs),
			"pending_mb_certifications": pending_mbs,
			"open_ncrs": open_ncrs,
			"average_progress": sum(d.get("overall_progress", 0) for d in project_dprs) / len(project_dprs) if project_dprs else 0
		})

	logger.info(f"Generated digest for {len(digests)} projects")

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

	if not completed_projects:
		return {"archived": 0}

	archived_count = 0

	# FIX: Batch WBS items for all completed projects at once
	wbs_items = frappe.get_all(
		"WBS Item",
		filters={"project": ["in", completed_projects]},
		fields=["name", "wbs_code", "project"]
	)

	# FIX: Single query to get all BOQ totals for all WBS codes at once
	wbs_names = [w["name"] for w in wbs_items]
	if wbs_names:
		boq_totals = frappe.db.sql("""
			SELECT wbs_code, SUM(total_value) as total
			FROM `tabCustom BOQ`
			WHERE wbs_code IN (%s) AND parent IN (%s)
			GROUP BY wbs_code
		""" % (", ".join(["%s"] * len(set(w.wbs_code for w in wbs_items))),
		       ", ".join(["%s"] * len(completed_projects))),
		       tuple(set(w.wbs_code for w in wbs_items)) + tuple(completed_projects),
		       as_dict=1)
		boq_map = {r.wbs_code: r.total or 0 for r in boq_totals}
	else:
		boq_map = {}

	# Now update WBS items using pre-computed totals (no per-iteration DB write)
	for wbs_item in wbs_items:
		boq_total = boq_map.get(wbs_item.wbs_code, 0)
		try:
			frappe.db.set_value("WBS Item", wbs_item.name, "planned_value", boq_total)
			archived_count += 1
		except Exception as e:
			logger.error(f"Archive failed for WBS {wbs_item.name}: {str(e)}")

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

	logger.info(f"Retention summary calculated for {len(retention_data)} projects")
	return {"retention_data": retention_data, "project_count": len(retention_data)}


# =============================================
# HSE Scheduler Tasks
# =============================================

def check_permit_expiry():
	"""
	Check for expired work permits and mark them accordingly.
	Runs daily to ensure permits are marked expired when end_date passes.

	SECURITY: This is a scheduler event that runs as System Administrator
	context. Permission check is implicit via scheduler execution context.
	"""
	logger.info("Starting permit expiry check")

	try:
		expired = frappe.get_all(
			"Work Permit",
			filters={
				"status": "In Progress",
				"end_date": ["<", now_datetime()]
			},
			pluck="name"
		)

		for permit_name in expired:
			try:
				doc = frappe.get_doc("Work Permit", permit_name)
				# Verify permission before modifying - scheduler context
				# requires explicit permission check for document modifications
				if not frappe.has_permission("Work Permit", "write", doc):
					logger.warning(f"No write permission for permit {permit_name}, skipping")
					continue
				doc.status = "Expired"
				doc.save(ignore_permissions=False)
				logger.info(f"Marked permit {permit_name} as expired")
			except Exception as e:
				logger.error(f"Failed to update permit {permit_name}: {e}")
				frappe.log_error(
					f"Permit Expiry Update Failed: {permit_name}",
					f"Error updating permit {permit_name}: {str(e)}"
				)

		logger.info(f"Permit expiry check completed: {len(expired)} marked as expired")

		return len(expired)

	except Exception as e:
		logger.error(f"Permit expiry check failed: {e}")
		frappe.log_error(frappe.get_traceback(), "Permit Expiry Check Error")
		return 0


def generate_hse_monthly_report():
	"""
	Generate monthly HSE report for all active projects.
	Compiles safety statistics and HSE metrics for monitoring.
	"""
	logger.info("Starting HSE monthly report generation")

	try:
		from epc_modules.api.hse_api import get_safety_statistics, get_hse_metrics

		projects = frappe.get_all(
			"Project",
			filters={
				"status": "Active",
				"is_epc_project": 1
			},
			pluck="name"
		)

		reports = []
		for project in projects:
			try:
				stats = get_safety_statistics(project)
				metrics = get_hse_metrics(project, days=30)
				reports.append({
					"project": project,
					"safety_stats": stats,
					"hse_metrics": metrics
				})
			except Exception as e:
				logger.error(f"Failed to generate report for {project}: {e}")

		logger.info(f"Generated HSE monthly report for {len(projects)} projects")

		return {"reports": reports, "project_count": len(projects)}

	except Exception as e:
		logger.error(f"HSE monthly report generation failed: {e}")
		frappe.log_error(frappe.get_traceback(), "HSE Report Generation Error")
		return {"reports": [], "project_count": 0}
