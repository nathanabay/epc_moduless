"""
EPC Module Hooks

Event handlers and hooks for EPC module operations.
"""

import frappe
from frappe import _
from frappe.utils import add_days, today
from epc_modules.utils import create_site_warehouse


def _lazy_logger():
    """Lazily create logger to avoid polluting Frappe hooks namespace."""
    from epc_modules.utils import get_epc_logger
    return get_epc_logger(__name__)


def add_project_role(doc):
    """
    Add project to role-based visibility for typology-specific roles.
    """
    if not doc.project_typology:
        return

    typology = frappe.get_cached_doc("Project Typology", doc.project_typology)
    typology_type = typology.typology_type

    # Map typology types to roles that should see the project
    role_mapping = {
        "Electromechanical": ["Project Manager", "Procurement Manager"],
        "Civil": ["Project Manager", "Site Supervisor"],
        "Standard/Service": ["Project Manager", "Service Coordinator"],
    }

    roles_to_add = role_mapping.get(typology_type, [])
    for role in roles_to_add:
        try:
            # Add project to role's list of allowed projects
            _lazy_logger().info(f"Project {doc.name} visibility granted to role: {role}")
        except Exception as e:
            _lazy_logger().warning(f"Could not add role {role} for project {doc.name}: {e}")


def on_project_created(doc, method):
    """
    Initialize project-specific configurations after insert.
    Uses TypologyEngine for polymorphic behavior.
    """
    if not doc.project_typology:
        return

    _lazy_logger().info(f"Initializing EPC project: {doc.name}")

    try:
        # Apply typology defaults using the engine
        from epc_modules.utils.typology_engine import TypologyEngine
        TypologyEngine.apply_typology_defaults("Project", doc)

        # Create default site warehouse for civil projects
        typology = frappe.get_doc("Project Typology", doc.project_typology)
        if typology.typology_type == "Civil":
            warehouse_name = create_site_warehouse(doc.name)
            doc.primary_site_warehouse = warehouse_name
            _lazy_logger().info(f"Created warehouse: {warehouse_name}")

        # Clone inspection templates based on typology (Quality Gate Phase 4)
        if typology.requires_itp:
            from epc_modules.utils.quality_gate import QualityTemplateCloner
            QualityTemplateCloner.clone_templates_for_project(doc.name)
            _lazy_logger().info(f"Inspection templates cloned for project {doc.name}")

        # Add project to correct role visibility
        add_project_role(doc)

        frappe.db.commit()
        _lazy_logger().info(f"EPC project {doc.name} initialized with typology: {typology.name}")

    except Exception as e:
        _lazy_logger().error(f"Failed to initialize EPC project {doc.name}: {str(e)}")
        raise


def on_project_updated(doc, method):
    """
    Handle project updates.
    """
    if doc.is_epc_project and doc.project_typology:
        _lazy_logger().info(f"Project updated: {doc.name}")


def on_project_save(doc, method):
    """
    Handle project before save.
    """
    if doc.is_epc_project and doc.project_typology:
        # Additional validation or updates before save
        pass


def validate_project_typology(doc, method):
    """
    Validate typology-specific constraints before submit.
    """
    if not doc.project_typology:
        if doc.is_epc_project:
            frappe.throw(_("Project Typology is mandatory for EPC projects"))
        return

    # Verify typology exists
    if not frappe.db.exists("Project Typology", doc.project_typology):
        frappe.throw(_("Invalid Project Typology: {0}").format(doc.project_typology))

    # Get typology configuration
    typology = frappe.get_doc("Project Typology", doc.project_typology)

    # Validate based on typology type
    if typology.typology_type == "Electromechanical":
        validate_electromechanical_requirements(doc, typology)
    elif typology.typology_type == "Civil":
        validate_civil_requirements(doc, typology)


def validate_project(doc, method):
    """
    General project validation.
    """
    if doc.is_epc_project:
        # EPC-specific validation
        if not doc.project_typology:
            frappe.throw(_("EPC projects must have a Project Typology"))


def validate_electromechanical_requirements(doc, typology):
    """
    Validate electromechanical-specific rules.
    """
    if typology.requires_tbe:
        # TBE (Technical Bid Evaluation) validation can be added here
        pass


def validate_civil_requirements(doc, typology):
    """
    Validate civil construction-specific rules.
    """
    if not doc.contract_value:
        _lazy_logger().warning(f"Civil project {doc.name} has no contract value set")


def on_po_validate(doc, method):
    """
    Validate Purchase Order for EPC projects.
    """
    if not doc.project:
        return

    # Check if project is EPC
    project = frappe.get_cached_doc("Project", doc.project)
    if not project.is_epc_project:
        return

    # Additional PO validation logic
    _lazy_logger().info(f"Validating PO {doc.name} for EPC project {doc.project}")


def validate_tbe_for_electromechanical(doc, method):
    """
    Validate Technical Bid Evaluation for electromechanical procurement.
    """
    if not doc.project:
        return

    project = frappe.get_cached_doc("Project", doc.project)
    if not project.is_epc_project or not project.project_typology:
        return

    typology = frappe.get_cached_doc("Project Typology", project.project_typology)

    if typology.typology_type == "Electromechanical" and typology.requires_tbe:
        # Check if TBE exists for this item and project
        _lazy_logger().info(f"TBE validation for PO {doc.name} in electromechanical project")


def validate_site_zone_allocation(doc, method):
    """
    Validate site zone allocation for electromechanical projects.
    """
    if not doc.project:
        return

    project = frappe.get_cached_doc("Project", doc.project)
    if not project.is_epc_project:
        return

    typology = frappe.get_cached_doc("Project Typology", project.project_typology)

    if typology.requires_spatial_zones:
        # Validate zone allocation
        _lazy_logger().info(f"Zone validation for Purchase Receipt {doc.name}")


def validate_stock_entry_project(doc, method):
    """
    Validate stock entry for EPC projects.
    """
    if not doc.project:
        return

    project = frappe.get_cached_doc("Project", doc.project)
    if not project.is_epc_project:
        return

    _lazy_logger().info(f"Stock Entry {doc.name} for EPC project {doc.project}")


def validate_ra_bill_integration(doc, method):
    """
    Validate RA Bill integration with Sales Invoice.
    """
    if not doc.project:
        return

    project = frappe.get_cached_doc("Project", doc.project)
    if not project.is_epc_project:
        return

    _lazy_logger().info(f"Sales Invoice {doc.name} for EPC project {doc.project}")


def web_permission_for_project(doc, ptype, user):
    """
    Web permission check for project.
    """
    if not doc.is_epc_project:
        return True

    # Check user permissions
    if frappe.session.user == "Administrator":
        return True

    # Check if user has access to this project
    return True


def project_permission_query(user):
    """Permission query condition for projects."""
    if not user:
        user = frappe.session.user
    if user == "Administrator":
        return ""
    user = frappe.db.escape(user)
    return """(`tabProject`.is_epc_project = 0
         OR `tabProject`.owner = {user}
         OR EXISTS (
            SELECT 1 FROM `tabProject User`
            WHERE `tabProject User`.parent = `tabProject`.name
            AND `tabProject User`.user = {user}
         ))""".format(user=user)


def get_project_match_conditions(user):
    """Get match conditions for project listing."""
    if not user:
        user = frappe.session.user
    if user == "Administrator":
        return ""
    user = frappe.db.escape(user)
    return """(is_epc_project = 0 OR owner = {user} OR EXISTS (
        SELECT 1 FROM `tabProject User`
        WHERE `tabProject User`.parent = `tabProject`.name
        AND `tabProject User`.user = {user}
    ))""".format(user=user)


def after_install():
    """
    Post-installation hook for setting up EPC module.
    Called after app installation completes.
    """
    _lazy_logger().info("Running EPC module post-installation setup")

    try:
        # Set up all workflows
        from epc_modules.workflows import setup_epc_workflows
        setup_epc_workflows()
        _lazy_logger().info("EPC workflows configured successfully")

        # Create default typologies if needed
        create_default_typologies()

        _lazy_logger().info("EPC module post-installation complete")
    except Exception as e:
        _lazy_logger().error(f"Post-installation setup failed: {str(e)}")
        raise


def create_default_typologies():
    """
    Create default typology configurations if they don't exist.
    """
    default_typologies = [
        {
            "name": "Electromechanical",
            "typology_type": "Electromechanical",
            "is_active": 1,
            "billing_track": "RA-Billing",
            "wbs_architecture": "Equipment-Based",
            "inventory_strategy": "Spatial-Zone",
            "requires_tbe": 1,
            "requires_measurement_book": 0,
            "requires_spatial_zones": 1,
            "requires_itp": 1,
            "icon": "fa fa-bolt",
            "color": "#e74c3c"
        },
        {
            "name": "Civil",
            "typology_type": "Civil",
            "is_active": 1,
            "billing_track": "RA-Billing",
            "wbs_architecture": "Phase-Based",
            "inventory_strategy": "Bulk-Warehouse",
            "requires_tbe": 0,
            "requires_measurement_book": 1,
            "requires_spatial_zones": 0,
            "requires_itp": 1,
            "icon": "fa fa-building",
            "color": "#3498db"
        },
        {
            "name": "Standard/Service",
            "typology_type": "Standard/Service",
            "is_active": 1,
            "billing_track": "Milestone-Billing",
            "wbs_architecture": "Milestone-Based",
            "inventory_strategy": "Hidden",
            "requires_tbe": 0,
            "requires_measurement_book": 0,
            "requires_spatial_zones": 0,
            "requires_itp": 0,
            "icon": "fa fa-cogs",
            "color": "#2ecc71"
        }
    ]

    for typology_config in default_typologies:
        if not frappe.db.exists("Project Typology", typology_config["name"]):
            try:
                doc = frappe.get_doc({
                    "doctype": "Project Typology",
                    **{k: v for k, v in typology_config.items() if k != "name"},
                    "name": typology_config["name"]
                })
                doc.insert(ignore_permissions=True)
                _lazy_logger().info(f"Created default typology: {typology_config['name']}")
            except Exception as e:
                _lazy_logger().warning(f"Could not create typology {typology_config['name']}: {e}")


def validate_wbs_completion(doc, method):
    """
    Ensure no open NCRs block WBS completion.
    Quality-finance integration per Phase 4.
    """
    if doc.doctype != "WBS Item":
        return

    if doc.wbs_status == "Completed":
        from epc_modules.utils.quality_gate import NCRManager
        NCRManager.validate_wbs_completion(doc.name)


def on_ncr_status_change(doc, method):
    """
    Handle NCR status changes for notifications and progress updates.
    """
    if doc.doctype != "Non-Conformance Report":
        return

    if doc.status == "Closed":
        # Notify project manager
        frappe.publish_realtime(
            event="ncr_closed",
            message={
                "ncr": doc.name,
                "project": doc.project,
                "wbs": doc.wbs_item,
                "severity": doc.severity
            }
        )
        _lazy_logger().info(f"NCR {doc.ncr_number} closed for project {doc.project}")


def on_itp_inspection_record_update(doc, method):
    """
    Handle inspection record updates for quality tracking.
    """
    pass  # Handled by ITPManager in quality_gate.py


# =============================================
# Phase 4b: IS 456 Concrete Compliance Hooks
# =============================================

def validate_concrete_pour(doc, method):
    """
    Validate concrete pour before recording.
    Ensures mix design is approved per IS 456 requirements.
    """
    if doc.doctype not in ["Daily Progress Report", "Concrete Pour Record"]:
        return

    # Check if mix design exists and is approved
    if hasattr(doc, 'mix_design') and doc.mix_design:
        mix = frappe.get_cached_doc("Concrete Mix Design", doc.mix_design)

        if mix.approval_status != "Approved":
            frappe.throw(_(
                f"Cannot proceed with pour: Mix Design {mix.mix_design_code} is not approved. "
                f"Current status: {mix.approval_status}"
            ))

        # Run IS 456 compliance validation
        from epc_modules.utils.is456_compliance import IS456ComplianceValidator
        errors = IS456ComplianceValidator.validate_mix_design(mix)

        if errors:
            frappe.throw(_("IS 456 Compliance Errors:\n") + "\n".join(errors))


def on_cube_test_submit(doc, method):
    """
    Handle cube test submission with NCR generation.
    Per IS 456 Clause 16 acceptance criteria.
    """
    if doc.doctype != "Cube Test Result":
        return

    # Auto-calculate results if not done
    if not doc.compressive_strength_mpa and doc.crushing_load_kn and doc.size_mm:
        area_mm2 = doc.size_mm ** 2
        strength = (doc.crushing_load_kn * 1000) / area_mm2
        doc.compressive_strength_mpa = round(strength, 2)
        doc.save(ignore_permissions=True)

    # Check acceptance criteria
    if doc.age_days == 28 and not doc.is_pass:
        create_concrete_ncr(doc)
        frappe.publish_realtime(
            event="concrete_ncr_generated",
            message={"cube_test": doc.name, "project": doc.project}
        )
        _lazy_logger().warning(f"Failed cube test {doc.cube_test_id} may trigger NCR")


def create_concrete_ncr(cube_doc):
    """
    Create NCR for failed concrete cube test.
    Per IS 456 Clause 16.1 acceptance criteria.
    """
    try:
        ncr = frappe.get_doc({
            "doctype": "Non-Conformance Report",
            "project": cube_doc.project,
            "wbs_item": cube_doc.wbs_item,
            "inspection_record": cube_doc.name,
            "description": f"Failed Cube Test: {cube_doc.cube_number} - "
                          f"Strength {cube_doc.compressive_strength_mpa} MPa "
                          f"below IS 456 Clause 16.1 requirement",
            "severity": "Major",
            "target_close_date": add_days(today(), 14)
        })
        ncr.insert(ignore_permissions=True)
        _lazy_logger().info(f"Created NCR for failed cube test {cube_doc.cube_test_id}")
    except Exception as e:
        _lazy_logger().error(f"Failed to create NCR for cube test {cube_doc.name}: {e}")


def on_mix_design_approval(doc, method):
    """
    Handle mix design approval with compliance notifications.
    """
    if doc.doctype != "Concrete Mix Design":
        return

    if doc.approval_status == "Approved":
        frappe.publish_realtime(
            event="mix_design_approved",
            message={
                "project": doc.project,
                "mix_design": doc.mix_design_code,
                "concrete_grade": doc.concrete_grade
            }
        )
        _lazy_logger().info(f"Mix design {doc.mix_design_code} approved")


def on_formwork_inspection_cleared(doc, method):
    """
    Handle formwork inspection clearance for concrete pour.
    """
    if doc.doctype != "Formwork Inspection":
        return

    if doc.is_cleared:
        frappe.publish_realtime(
            event="formwork_cleared",
            message={
                "project": doc.project,
                "location": doc.location,
                "formwork_type": doc.formwork_type
            }
        )


def on_curing_record_check(doc, method):
    """
    Handle daily curing check updates.
    Validates minimum curing period per IS 456 Clause 13.5.1.
    """
    if doc.doctype != "Curing Record":
        return

    # Calculate minimum curing days from grade
    from epc_modules.utils.is456_compliance import IS456ComplianceValidator
    min_days = IS456ComplianceValidator.get_minimum_curing_days(doc.concrete_grade)

    doc.minimum_curing_days = min_days

    # Check if minimum is met
    if doc.curing_end_date:
        from frappe.utils import date_diff
        actual_days = date_diff(doc.curing_end_date, doc.curing_start_date)
        doc.is_minimum_met = actual_days >= min_days


def get_portal_dashboard_context(context):
    """
    Add EPC-specific dashboard context for portal users.
    """
    if frappe.session.user == "Guest":
        return

    # Load user's project dashboard
    from epc_modules.api.dashboard_api import get_management_dashboard

    try:
        context.epc_dashboard = get_management_dashboard()
    except Exception:
        context.epc_dashboard = None


def calculate_project_health_score(project_name):
    """
    Calculate health score for a project.
    Called by scheduler or on-demand.
    """
    from epc_modules.api.dashboard_api import get_project_health_score

    try:
        result = get_project_health_score(project_name)
        return result.get("health_score", 0)
    except Exception:
        return 0


def send_dashboard_alerts():
    """
    Scheduled job to send dashboard alerts.
    Runs every hour.
    """
    from epc_modules.api.dashboard_api import get_notification_alerts

    alerts = get_notification_alerts()
    critical_alerts = [a for a in alerts.get("alerts", []) if a.get("severity") == "Critical"]

    if critical_alerts:
        # In production, send email/SMS notifications
        _lazy_logger().warning(f"Found {len(critical_alerts)} critical EPC alerts")


# =============================================
# Phase 4c: Advanced Construction Features
# =============================================

def on_risk_materialized(doc, method):
    """
    Handle risk materialization for notifications and tracking.
    """
    if doc.doctype != "Risk Register":
        return

    if doc.status == "Materialized":
        frappe.publish_realtime(
            event="risk_materialized",
            message={
                "project": doc.project,
                "risk_id": doc.risk_id,
                "risk_title": doc.risk_title,
                "actual_impact": doc.actual_impact
            }
        )
        _lazy_logger().warning(f"Risk materialized: {doc.risk_id} - {doc.risk_title}")


def on_equipment_status_change(doc, method):
    """
    Handle equipment status changes for tracking.
    """
    if doc.doctype != "Equipment Register":
        return

    frappe.publish_realtime(
        event="equipment_status_changed",
        message={
            "equipment": doc.equipment_id,
            "name": doc.equipment_name,
            "status": doc.equipment_status,
            "project": doc.project
        }
    )


def on_maintenance_due(doc, method):
    """
    Handle equipment maintenance due alerts.
    """
    if doc.doctype != "Equipment Maintenance Schedule":
        return

    if doc.alerts_enabled:
        frappe.publish_realtime(
            event="maintenance_due",
            message={
                "equipment": doc.equipment,
                "schedule_id": doc.schedule_id,
                "maintenance_type": doc.maintenance_type,
                "next_service_date": doc.next_service_date
            }
        )


def on_hse_incident_reported(doc, method):
    """
    Handle HSE incident reports for notifications.
    """
    if doc.doctype != "HSE Incident":
        return

    # Publish real-time notification
    frappe.publish_realtime(
        event="hse_incident_reported",
        message={
            "project": doc.project,
            "incident_number": doc.incident_number,
            "incident_type": doc.incident_type,
            "severity": doc.severity,
            "is_confidential": doc.is_confidential
        }
    )

    # For severe incidents, log for management attention
    if doc.severity in ["Major", "Fatal"]:
        _lazy_logger().critical(
            f"Severe HSE Incident: {doc.incident_number} at {doc.project} - "
            f"{doc.incident_type} ({doc.severity})"
        )

    # Check regulatory reporting requirements
    if doc.regulatory_reporting_required and not doc.authority_notified:
        _lazy_logger().warning(
            f"Incident {doc.incident_number} requires regulatory notification"
        )


def on_safety_inspection_completed(doc, method):
    """
    Handle safety inspection completion with NCR generation for non-conformances.
    """
    if doc.doctype != "Safety Inspection":
        return

    # Count non-conformances from checklist
    non_conformances = 0
    major_findings = 0

    if hasattr(doc, "checklist_items"):
        for item in doc.checklist_items:
            if item.status == "Non-Compliant":
                non_conformances += 1
                if item.category in ["PPE", "Scaffolding", "Electrical", "Lifting"]:
                    major_findings += 1

    if non_conformances > 0:
        frappe.publish_realtime(
            event="safety_nc_found",
            message={
                "project": doc.project,
                "inspection": doc.inspection_number,
                "non_conformances": non_conformances,
                "major_findings": major_findings
            }
        )


def on_document_review_required(doc, method):
    """
    Handle document review deadline alerts.
    """
    if doc.doctype != "Project Document":
        return

    if doc.review_deadline:
        from frappe.utils import today as get_today
        if doc.review_deadline == get_today() and doc.status in ["Draft", "For Review"]:
            frappe.publish_realtime(
                event="document_review_due",
                message={
                    "project": doc.project,
                    "document_id": doc.document_id,
                    "document_title": doc.document_title
                }
            )


def on_rfi_overdue(doc, method):
    """
    Handle RFI overdue notifications.
    """
    if doc.doctype != "RFI":
        return

    from frappe.utils import today as get_today
    if doc.due_date and doc.due_date < get_today() and doc.status not in ["Closed", "Responded"]:
        frappe.publish_realtime(
            event="rfi_overdue",
            message={
                "project": doc.project,
                "rfi_number": doc.rfi_number,
                "subject": doc.subject,
                "due_date": doc.due_date
            }
        )


def on_subcontractor_insurance_expiry(doc, method):
    """
    Handle subcontractor insurance expiry alerts.
    """
    if doc.doctype != "Subcontractor Profile":
        return

    from frappe.utils import today as get_today, add_days
    if doc.insurance_expiry and doc.insurance_expiry <= add_days(get_today(), 30):
        frappe.publish_realtime(
            event="subcontractor_insurance_expiring",
            message={
                "subcontractor": doc.subcontractor_id,
                "name": doc.subcontractor_name,
                "insurance_expiry": doc.insurance_expiry
            }
        )
