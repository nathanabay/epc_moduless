"""
Document Management API Module

REST API endpoints for project document control, RFI, and submittal management.
"""

import frappe
from frappe import _
from frappe.utils import today, add_days, flt
from epc_modules.utils import get_epc_logger

logger = get_epc_logger(__name__)


# =============================================
# Project Document Register
# =============================================

@frappe.whitelist()
def create_project_document(project, data):
    """
    Create project document register entry.

    Args:
        project (str): Project name
        data (dict): Document data

    Returns:
        dict: Created document info
    """
    frappe.has_permission("Project Document", "create", throw=True)

    if not frappe.db.exists("Project", project):
        frappe.throw(_("Project {0} does not exist").format(project))

    count = frappe.db.count("Project Document", {"project": project}) or 0
    document_id = f"DOC-{project[:4].upper()}-{count + 1:04d}"

    doc = frappe.get_doc({
        "doctype": "Project Document",
        "document_id": document_id,
        "project": project,
        "document_type": data.get("document_type"),
        "document_number": data.get("document_number"),
        "document_title": data.get("document_title"),
        "document_description": data.get("document_description"),
        "revision": data.get("revision", "01"),
        "discipline": data.get("discipline"),
        "received_date": data.get("received_date", today()),
        "received_from": data.get("received_from"),
        "review_deadline": data.get("review_deadline"),
        "file": data.get("file"),
        "linked_wbs": data.get("linked_wbs"),
        "tags": data.get("tags"),
        "status": "Draft"
    })

    doc.insert()

    logger.info(f"Document registered: {document_id}")

    return {
        "name": doc.name,
        "document_id": doc.document_id
    }


@frappe.whitelist()
def get_project_documents(project, document_type=None):
    """
    Get documents for a project.

    Args:
        project (str): Project name
        document_type (str, optional): Filter by type

    Returns:
        list: Documents
    """
    filters = {"project": project, "is_latest": 1}
    if document_type:
        filters["document_type"] = document_type

    return frappe.get_all(
        "Project Document",
        filters=filters,
        fields=["name", "document_id", "document_type", "document_number",
                "document_title", "revision", "status", "received_date"],
        order_by="received_date desc"
    )


@frappe.whitelist()
def update_document_status(document_name, status, comments=None):
    """
    Update document review status.

    Args:
        document_name (str): Document name
        status (str): New status
        comments (str, optional): Review comments

    Returns:
        dict: Update result
    """
    frappe.has_permission("Project Document", "write", throw=True)
    doc = frappe.get_doc("Project Document", document_name)

    doc.status = status
    doc.reviewed_by = frappe.session.user
    doc.review_date = today()

    if comments:
        doc.comments = comments

    if status == "Approved":
        doc.is_approved = 1
        doc.approved_by = frappe.session.user
        doc.approval_date = today()

    doc.save()

    return {
        "name": doc.name,
        "status": doc.status
    }


@frappe.whitelist()
def supersede_document(document_name, new_revision_data):
    """
    Supersede a document with a new revision.

    Args:
        document_name (str): Current document name
        new_revision_data (dict): New revision data

    Returns:
        dict: New document info
    """
    frappe.has_permission("Project Document", "write", throw=True)
    old_doc = frappe.get_doc("Project Document", document_name)

    # Mark old as superseded
    old_doc.status = "Superseded"
    old_doc.is_latest = 0
    old_doc.save()

    # Create new revision
    count = frappe.db.count("Project Document", {"project": old_doc.project}) or 0
    new_document_id = f"DOC-{old_doc.project[:4].upper()}-{count + 1:04d}"

    new_doc = frappe.get_doc({
        "doctype": "Project Document",
        "document_id": new_document_id,
        "project": old_doc.project,
        "document_type": old_doc.document_type,
        "document_number": old_doc.document_number,
        "document_title": old_doc.document_title,
        "revision": new_revision_data.get("revision"),
        "discipline": old_doc.discipline,
        "received_date": today(),
        "file": new_revision_data.get("file"),
        "linked_wbs": old_doc.linked_wbs,
        "tags": old_doc.tags,
        "is_latest": 1,
        "supersedes": old_doc.name,
        "status": "Draft"
    })

    new_doc.insert()

    return {
        "name": new_doc.name,
        "document_id": new_doc.document_id,
        "supersedes": old_doc.name
    }


# =============================================
# Request for Information (RFI)
# =============================================

@frappe.whitelist()
def create_rfi(project, data):
    """
    Create RFI (Request for Information).

    Args:
        project (str): Project name
        data (dict): RFI data

    Returns:
        dict: Created RFI info
    """
    frappe.has_permission("RFI", "create", throw=True)

    if not frappe.db.exists("Project", project):
        frappe.throw(_("Project {0} does not exist").format(project))

    count = frappe.db.count("RFI", {"project": project}) or 0
    rfi_number = f"RFI-{project[:4].upper()}-{count + 1:04d}"

    doc = frappe.get_doc({
        "doctype": "RFI",
        "rfi_number": rfi_number,
        "project": project,
        "rfi_number": rfi_number,
        "subject": data.get("subject"),
        "description": data.get("description"),
        "priority": data.get("priority", "Normal"),
        "raised_by": data.get("raised_by", frappe.session.user),
        "raised_date": today(),
        "due_date": data.get("due_date"),
        "assigned_to": data.get("assigned_to"),
        "drawing_reference": data.get("drawing_reference"),
        "specification_reference": data.get("specification_reference"),
        "wbs_item": data.get("wbs_item"),
        "status": "Draft"
    })

    doc.insert()

    logger.info(f"RFI created: {rfi_number}")

    return {
        "name": doc.name,
        "rfi_number": doc.rfi_number,
        "status": doc.status
    }


@frappe.whitelist()
def get_project_rfis(project, status=None):
    """
    Get RFIs for a project.

    Args:
        project (str): Project name
        status (str, optional): Filter by status

    Returns:
        list: RFIs
    """
    filters = {"project": project}
    if status:
        filters["status"] = status

    return frappe.get_all(
        "RFI",
        filters=filters,
        fields=["name", "rfi_number", "subject", "priority", "status",
                "raised_by", "due_date", "assigned_to", "days_to_close"],
        order_by="creation desc"
    )


@frappe.whitelist()
def respond_to_rfi(rfi_name, response_text):
    """
    Record RFI response.

    Args:
        rfi_name (str): RFI name
        response_text (str): Response content

    Returns:
        dict: Response result
    """
    frappe.has_permission("RFI", "write", throw=True)
    doc = frappe.get_doc("RFI", rfi_name)

    doc.response_text = response_text
    doc.responded_by = frappe.session.user
    doc.response_date = today()
    doc.status = "Responded"

    # Calculate days to close
    from frappe.utils import date_diff
    doc.days_to_close = date_diff(today(), doc.raised_date)

    doc.save()

    logger.info(f"RFI {doc.rfi_number} responded")

    return {
        "name": doc.name,
        "status": doc.status,
        "response_date": doc.response_date
    }


@frappe.whitelist()
def close_rfi(rfi_name):
    """
    Close an RFI.

    Args:
        rfi_name (str): RFI name

    Returns:
        dict: Closure result
    """
    frappe.has_permission("RFI", "write", throw=True)
    doc = frappe.get_doc("RFI", rfi_name)

    doc.status = "Closed"
    doc.closed_date = today()

    doc.save()

    return {
        "name": doc.name,
        "status": "Closed",
        "closed_date": doc.closed_date,
        "days_to_close": doc.days_to_close
    }


# =============================================
# Submittal Register
# =============================================

@frappe.whitelist()
def create_submittal(project, data):
    """
    Create submittal entry.

    Args:
        project (str): Project name
        data (dict): Submittal data

    Returns:
        dict: Created submittal info
    """
    frappe.has_permission("Submittal", "create", throw=True)

    if not frappe.db.exists("Project", project):
        frappe.throw(_("Project {0} does not exist").format(project))

    count = frappe.db.count("Submittal", {"project": project}) or 0
    submittal_number = f"SUB-{project[:4].upper()}-{count + 1:04d}"

    doc = frappe.get_doc({
        "doctype": "Submittal",
        "submittal_number": submittal_number,
        "project": project,
        "submittal_title": data.get("submittal_title"),
        "submittal_type": data.get("submittal_type"),
        "spec_section": data.get("spec_section"),
        "specification_reference": data.get("specification_reference"),
        "wbs_item": data.get("wbs_item"),
        "contractor": data.get("contractor"),
        "submitted_by": data.get("submitted_by", frappe.session.user),
        "submission_date": today(),
        "required_date": data.get("required_date"),
        "days_for_review": data.get("days_for_review", 14),
        "review_status": "Pending"
    })

    doc.insert()

    return {
        "name": doc.name,
        "submittal_number": doc.submittal_number
    }


@frappe.whitelist()
def get_project_submittals(project, status=None):
    """
    Get submittals for a project.

    Args:
        project (str): Project name
        status (str, optional): Filter by status

    Returns:
        list: Submittals
    """
    filters = {"project": project}
    if status:
        filters["review_status"] = status

    return frappe.get_all(
        "Submittal",
        filters=filters,
        fields=["name", "submittal_number", "submittal_title", "submittal_type",
                "review_status", "required_date", "submitted_by"],
        order_by="creation desc"
    )


@frappe.whitelist()
def review_submittal(submittal_name, review_data):
    """
    Record submittal review.

    Args:
        submittal_name (str): Submittal name
        review_data (dict): Review data

    Returns:
        dict: Review result
    """
    frappe.has_permission("Submittal", "write", throw=True)
    doc = frappe.get_doc("Submittal", submittal_name)

    doc.review_status = review_data.get("review_status")
    doc.reviewed_by = review_data.get("reviewed_by", frappe.session.user)
    doc.review_date = today()
    doc.reviewed_remarks = review_data.get("remarks")

    if review_data.get("review_status") in ["Approved", "Approved as Noted"]:
        doc.is_closed = 1
        doc.closed_date = today()
    elif review_data.get("review_status") == "Revise and Resubmit":
        doc.resubmission_required = 1
        doc.resubmission_number = (doc.resubmission_number or 0) + 1

    doc.save()

    return {
        "name": doc.name,
        "review_status": doc.review_status
    }


# =============================================
# Document Analytics
# =============================================

@frappe.whitelist()
def get_document_summary(project):
    """
    Get document management summary.

    Args:
        project (str): Project name

    Returns:
        dict: Summary
    """
    # Documents by type
    docs = frappe.get_all(
        "Project Document",
        filters={"project": project},
        fields=["name", "document_type", "status"]
    )

    by_type = {}
    by_status = {}
    for doc in docs:
        doc_type = doc.document_type or "Unknown"
        by_type[doc_type] = by_type.get(doc_type, 0) + 1
        by_status[doc.status] = by_status.get(doc.status, 0) + 1

    # RFIs
    rfis = frappe.get_all(
        "RFI",
        filters={"project": project},
        fields=["name", "status", "days_to_close"]
    )

    open_rfis = sum(1 for r in rfis if r.status not in ["Closed", "Superseded"])
    avg_close_days = sum(r.days_to_close or 0 for r in rfis) / len(rfis) if rfis else 0

    # Submittals
    submittals = frappe.get_all(
        "Submittal",
        filters={"project": project},
        fields=["name", "review_status"]
    )

    pending_submittals = sum(1 for s in submittals if s.review_status == "Pending")

    return {
        "project": project,
        "documents": {
            "total": len(docs),
            "by_type": by_type,
            "by_status": by_status
        },
        "rfis": {
            "total": len(rfis),
            "open": open_rfis,
            "avg_close_days": round(avg_close_days, 1)
        },
        "submittals": {
            "total": len(submittals),
            "pending": pending_submittals
        }
    }


@frappe.whitelist()
def get_overdue_items(project):
    """
    Get overdue documents, RFIs, and submittals.

    Args:
        project (str): Project name

    Returns:
        dict: Overdue items
    """
    today_date = today()
    overdue = {"documents": [], "rfis": [], "submittals": []}

    # Overdue document reviews
    overdue_docs = frappe.get_all(
        "Project Document",
        filters={
            "project": project,
            "review_deadline": ["<", today_date],
            "status": ["in", ["Draft", "For Review"]]
        },
        fields=["name", "document_id", "document_title", "review_deadline"]
    )
    overdue["documents"] = overdue_docs

    # Overdue RFIs
    overdue_rfis = frappe.get_all(
        "RFI",
        filters={
            "project": project,
            "due_date": ["<", today_date],
            "status": ["not in", ["Closed", "Responded", "Superseded"]]
        },
        fields=["name", "rfi_number", "subject", "due_date"]
    )
    overdue["rfis"] = overdue_rfis

    # Overdue submittals
    overdue_subs = frappe.get_all(
        "Submittal",
        filters={
            "project": project,
            "required_date": ["<", today_date],
            "is_closed": 0
        },
        fields=["name", "submittal_number", "submittal_title", "required_date"]
    )
    overdue["submittals"] = overdue_subs

    return {
        "project": project,
        "total_overdue": len(overdue["documents"]) + len(overdue["rfis"]) + len(overdue["submittals"]),
        "items": overdue
    }
