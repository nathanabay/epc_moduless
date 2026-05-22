"""
EPC Workflows Module

Workflow configurations for EPC module documents.
"""

import frappe
from frappe.model import workflow
from frappe.utils import nowdate, add_days
from epc_modules.utils import get_epc_logger

logger = get_epc_logger(__name__)


def setup_epc_workflows():
    """
    Set up all EPC module workflows.
    Called during app installation.
    """
    frappe.only_for("System Manager")
    logger.info("Setting up EPC workflows")

    setup_project_approval_workflow()
    setup_measurement_book_workflow()
    setup_ra_bill_workflow()
    setup_ncr_workflow()

    logger.info("EPC workflows setup complete")


def setup_project_approval_workflow():
    """
    Set up the EPC Project Approval workflow.

    States:
    - Draft
    - Typology Assigned
    - Resources Allocated
    - Active
    - On Hold
    - Completed

    Transitions:
    - Draft -> Typology Assigned (System Manager)
    - Typology Assigned -> Resources Allocated (Project Manager)
    - Resources Allocated -> Active (Project Manager)
    - Active -> On Hold (Project Manager)
    - On Hold -> Active (Project Manager)
    - Active -> Completed (Project Manager)
    """
    workflow_name = "EPC Project Approval"
    doctype = "Project"

    if frappe.db.exists("Workflow", workflow_name):
        logger.info(f"Workflow {workflow_name} already exists")
        return

    # Create workflow document
    doc = frappe.get_doc({
        "doctype": "Workflow",
        "workflow_name": workflow_name,
        "document_type": doctype,
        "is_active": 1,
        "send_email_alert": 0,
        "override_status": 0,
        "honour_very_special_roles": 0,
        "send_notification_alert": 0,
        "workflow_state_field": "workflow_state"
    })

    # Add states
    states = [
        {"state": "Draft", "style": "Warning", "doc_status": 0},
        {"state": "Typology Assigned", "style": "Info", "doc_status": 0},
        {"state": "Resources Allocated", "style": "Info", "doc_status": 0},
        {"state": "Active", "style": "Success", "doc_status": 1},
        {"state": "On Hold", "style": "Warning", "doc_status": 1},
        {"state": "Completed", "style": "Dark", "doc_status": 1},
        {"state": "Cancelled", "style": "Danger", "doc_status": 2}
    ]

    for state in states:
        doc.append("states", state)

    # Add transitions
    transitions = [
        {
            "state": "Draft",
            "action": "Assign Typology",
            "next_state": "Typology Assigned",
            "allowed": "System Manager",
            "allowed_user": None
        },
        {
            "state": "Typology Assigned",
            "action": "Allocate Resources",
            "next_state": "Resources Allocated",
            "allowed": "Project Manager",
            "allowed_user": None
        },
        {
            "state": "Resources Allocated",
            "action": "Activate",
            "next_state": "Active",
            "allowed": "Project Manager",
            "allowed_user": None
        },
        {
            "state": "Active",
            "action": "Hold",
            "next_state": "On Hold",
            "allowed": "Project Manager",
            "allowed_user": None
        },
        {
            "state": "On Hold",
            "action": "Resume",
            "next_state": "Active",
            "allowed": "Project Manager",
            "allowed_user": None
        },
        {
            "state": "Active",
            "action": "Complete",
            "next_state": "Completed",
            "allowed": "Project Manager",
            "allowed_user": None
        },
        {
            "state": "Active",
            "action": "Cancel",
            "next_state": "Cancelled",
            "allowed": "System Manager",
            "allowed_user": None
        }
    ]

    for transition in transitions:
        doc.append("transitions", transition)

    doc.insert()
    logger.info(f"Created workflow: {workflow_name}")


def setup_measurement_book_workflow():
    """
    Set up the Measurement Book approval workflow.

    States:
    - Draft
    - Submitted
    - Under Review
    - Certified
    - Rejected
    """
    workflow_name = "EPC Measurement Book Approval"
    doctype = "Measurement Book"

    if frappe.db.exists("Workflow", workflow_name):
        logger.info(f"Workflow {workflow_name} already exists")
        return

    doc = frappe.get_doc({
        "doctype": "Workflow",
        "workflow_name": workflow_name,
        "document_type": doctype,
        "is_active": 1,
        "send_email_alert": 1,
        "override_status": 0
    })

    states = [
        {"state": "Draft", "style": "Warning", "doc_status": 0},
        {"state": "Submitted", "style": "Info", "doc_status": 0},
        {"state": "Under Review", "style": "Primary", "doc_status": 0},
        {"state": "Certified", "style": "Success", "doc_status": 1},
        {"state": "Rejected", "style": "Danger", "doc_status": 0}
    ]

    for state in states:
        doc.append("states", state)

    transitions = [
        {
            "state": "Draft",
            "action": "Submit",
            "next_state": "Submitted",
            "allowed": "Site Supervisor",
            "allowed_user": None
        },
        {
            "state": "Submitted",
            "action": "Review",
            "next_state": "Under Review",
            "allowed": "Quality Manager",
            "allowed_user": None
        },
        {
            "state": "Under Review",
            "action": "Certify",
            "next_state": "Certified",
            "allowed": "Consulting Engineer",
            "allowed_user": None
        },
        {
            "state": "Under Review",
            "action": "Reject",
            "next_state": "Rejected",
            "allowed": "Consulting Engineer",
            "allowed_user": None
        },
        {
            "state": "Rejected",
            "action": "Resubmit",
            "next_state": "Submitted",
            "allowed": "Site Supervisor",
            "allowed_user": None
        }
    ]

    for transition in transitions:
        doc.append("transitions", transition)

    doc.insert()
    logger.info(f"Created workflow: {workflow_name}")


def setup_ra_bill_workflow():
    """
    Set up the RA Bill approval workflow.

    States:
    - Draft
    - Submitted
    - Under Review
    - Certified
    - Invoiced
    - Rejected
    """
    workflow_name = "EPC RA Bill Approval"
    doctype = "RA Bill"

    if frappe.db.exists("Workflow", workflow_name):
        logger.info(f"Workflow {workflow_name} already exists")
        return

    doc = frappe.get_doc({
        "doctype": "Workflow",
        "workflow_name": workflow_name,
        "document_type": doctype,
        "is_active": 1,
        "send_email_alert": 1,
        "override_status": 0
    })

    states = [
        {"state": "Draft", "style": "Warning", "doc_status": 0},
        {"state": "Submitted", "style": "Info", "doc_status": 0},
        {"state": "Under Review", "style": "Primary", "doc_status": 0},
        {"state": "Certified", "style": "Success", "doc_status": 1},
        {"state": "Invoiced", "style": "Dark", "doc_status": 1},
        {"state": "Rejected", "style": "Danger", "doc_status": 0}
    ]

    for state in states:
        doc.append("states", state)

    transitions = [
        {
            "state": "Draft",
            "action": "Submit",
            "next_state": "Submitted",
            "allowed": "Finance Manager",
            "allowed_user": None
        },
        {
            "state": "Submitted",
            "action": "Review",
            "next_state": "Under Review",
            "allowed": "Project Manager",
            "allowed_user": None
        },
        {
            "state": "Under Review",
            "action": "Certify",
            "next_state": "Certified",
            "allowed": "Client Representative",
            "allowed_user": None
        },
        {
            "state": "Under Review",
            "action": "Reject",
            "next_state": "Rejected",
            "allowed": "Client Representative",
            "allowed_user": None
        },
        {
            "state": "Certified",
            "action": "Generate Invoice",
            "next_state": "Invoiced",
            "allowed": "Finance Manager",
            "allowed_user": None
        },
        {
            "state": "Rejected",
            "action": "Revise",
            "next_state": "Draft",
            "allowed": "Finance Manager",
            "allowed_user": None
        }
    ]

    for transition in transitions:
        doc.append("transitions", transition)

    doc.insert()
    logger.info(f"Created workflow: {workflow_name}")


def setup_ncr_workflow():
    """
    Set up the NCR workflow.

    States:
    - Open
    - In Progress
    - Closed
    - Verified
    """
    workflow_name = "EPC NCR Workflow"
    doctype = "Non-Conformance Report"

    if frappe.db.exists("Workflow", workflow_name):
        logger.info(f"Workflow {workflow_name} already exists")
        return

    doc = frappe.get_doc({
        "doctype": "Workflow",
        "workflow_name": workflow_name,
        "document_type": doctype,
        "is_active": 1,
        "send_email_alert": 1,
        "override_status": 0
    })

    states = [
        {"state": "Open", "style": "Danger", "doc_status": 0},
        {"state": "In Progress", "style": "Warning", "doc_status": 0},
        {"state": "Closed", "style": "Success", "doc_status": 1},
        {"state": "Verified", "style": "Dark", "doc_status": 1}
    ]

    for state in states:
        doc.append("states", state)

    transitions = [
        {
            "state": "Open",
            "action": "Start Investigation",
            "next_state": "In Progress",
            "allowed": "QC Manager",
            "allowed_user": None
        },
        {
            "state": "In Progress",
            "action": "Close",
            "next_state": "Closed",
            "allowed": "QC Manager",
            "allowed_user": None
        },
        {
            "state": "Closed",
            "action": "Verify",
            "next_state": "Verified",
            "allowed": "Project Manager",
            "allowed_user": None
        },
        {
            "state": "Closed",
            "action": "Reopen",
            "next_state": "In Progress",
            "allowed": "QC Manager",
            "allowed_user": None
        }
    ]

    for transition in transitions:
        doc.append("transitions", transition)

    doc.insert()
    logger.info(f"Created workflow: {workflow_name}")


@frappe.whitelist()
def get_workflow_states(doctype):
    """
    Get workflow states for a doctype.

    Args:
        doctype: Document type name

    Returns:
        list: List of workflow states
    """
    if not frappe.has_permission("Workflow", "read"):
        frappe.throw(frappe._("No permission to read Workflow"))

    workflow_name = frappe.db.get_value(
        "Workflow",
        {"document_type": doctype, "is_active": 1},
        "name"
    )

    if not workflow_name:
        return []

    workflow = frappe.get_doc("Workflow", workflow_name)
    frappe.flags.in_import = True
    try:
        return [state.state for state in workflow.states]
    finally:
        frappe.flags.in_import = False


@frappe.whitelist()
def get_available_transitions(doctype, current_state):
    """
    Get available transitions from current state.

    Args:
        doctype: Document type name
        current_state: Current workflow state

    Returns:
        list: Available transitions
    """
    if not frappe.has_permission("Workflow", "read"):
        frappe.throw(frappe._("No permission to read Workflow"))

    workflow_name = frappe.db.get_value(
        "Workflow",
        {"document_type": doctype, "is_active": 1},
        "name"
    )

    if not workflow_name:
        return []

    workflow = frappe.get_doc("Workflow", workflow_name)
    transitions = []

    for t in workflow.transitions:
        if t.state == current_state:
            transitions.append({
                "action": t.action,
                "next_state": t.next_state,
                "allowed": t.allowed
            })

    return transitions