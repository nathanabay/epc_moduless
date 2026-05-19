"""
Quality Gate Module

Quality management utilities for EPC module.
Implements inspection templates, ITP management, and NCR handling.
"""

import frappe
from frappe import _
from frappe.utils import today, now_datetime, get_datetime, add_days
from typing import Dict, List, Optional, Any
from epc_modules.utils import get_epc_logger, EPCException

logger = get_epc_logger(__name__)


class QualityTemplateCloner:
    """
    Handles cloning of inspection templates for projects based on typology.
    Implements ISO 9001:2015 compliance for inspection management.
    """

    @staticmethod
    def clone_templates_for_project(project_name: str) -> int:
        """
        Clone appropriate inspection templates based on project typology.

        Args:
            project_name: Name of the project

        Returns:
            int: Number of ITPs created
        """
        logger.info(f"Cloning inspection templates for project: {project_name}")

        project = frappe.get_doc("Project", project_name)

        if not project.project_typology:
            logger.warning(f"Project {project_name} has no typology assigned")
            return 0

        typology = frappe.get_doc("Project Typology", project.project_typology)

        # Find applicable templates
        applicable_templates = frappe.get_all(
            "Master Inspection Template",
            filters={
                "is_active": 1,
                "applicable_typologies": ["like", f"%{typology.typology_type}%"]
            },
            fields=["name", "template_name", "inspection_category"]
        )

        cloned_count = 0

        for template in applicable_templates:
            try:
                # Check if this template is relevant to project's BOQ items
                if QualityTemplateCloner._is_template_relevant(template, project):
                    itp = QualityTemplateCloner._clone_template(template, project)
                    cloned_count += 1
                    logger.info(f"Created ITP: {itp.name} from template {template.name}")
            except Exception as e:
                logger.error(f"Failed to clone template {template.name}: {str(e)}")

        logger.info(f"Template cloning complete: {cloned_count} ITPs created")
        return cloned_count

    @staticmethod
    def _is_template_relevant(template: "frappe.doc", project: "frappe.doc") -> bool:
        """
        Determine if template is relevant to project scope.

        Args:
            template: Master Inspection Template document
            project: Project document

        Returns:
            bool: True if template is relevant
        """
        # Check BOQ items for matching categories
        boq_items = frappe.get_all(
            "Custom BOQ",
            filters={"parent": project.name},
            fields=["name", "item_code", "is_electromechanical", "is_civil"]
        )

        if not boq_items:
            # If no BOQ items, include all templates
            return True

        # Template relevance logic based on inspection category and typology
        for item in boq_items:
            if template.inspection_category == "Structural" and item.get("is_civil"):
                return True
            if template.inspection_category == "Mechanical" and item.get("is_electromechanical"):
                return True
            if template.inspection_category == "Electrical" and item.get("is_electromechanical"):
                return True

        return False

    @staticmethod
    def _clone_template(template: "frappe.doc", project: "frappe.doc") -> "frappe.doc":
        """
        Create project-specific ITP from master template.

        Args:
            template: Master Inspection Template document
            project: Project document

        Returns:
            Created ITP document
        """
        # Generate ITP code
        itp_code = f"ITP-{project.name[:4].upper()}-{frappe.utils.random_string(6)}"

        itp = frappe.get_doc({
            "doctype": "Project Inspection Plan",
            "project": project.name,
            "itp_code": itp_code,
            "source_template": template.name,
            "status": "Draft",
            "inspection_records": []
        })

        # Deep copy hold points to inspection records
        for hold_point in template.hold_points:
            itp.append("inspection_records", {
                "hold_point": hold_point.name,
                "hold_point_name": hold_point.hold_point_name,
                "sequence": hold_point.sequence,
                "scheduled_date": None,
                "inspector": None,
                "status": "Pending"
            })

        itp.insert(ignore_permissions=True)

        # Update summary fields
        itp.total_hold_points = len(itp.inspection_records)
        itp.pending_hold_points = len(itp.inspection_records)
        itp.save(ignore_permissions=True)

        return itp


class NCRManager:
    """
    Manages Non-Conformance Reports and their lifecycle.
    Implements quality-finance integration by blocking billing on open NCRs.
    """

    @staticmethod
    def create_ncr_from_inspection(
        project: str,
        wbs_item: str,
        inspection_record: str,
        description: str,
        severity: str,
        target_close_date=None
    ) -> "frappe.doc":
        """
        Create NCR from failed inspection record.

        Args:
            project: Project name
            wbs_item: WBS Item name
            inspection_record: Inspection Record name
            description: NCR description
            severity: Severity level (Critical, Major, Minor)
            target_close_date: Target close date

        Returns:
            Created NCR document
        """
        # Generate NCR number
        ncr_count = frappe.db.count("Non-Conformance Report", {"project": project}) or 0
        ncr_number = f"NCR-{project[:4].upper()}-{ncr_count + 1:04d}"

        if not target_close_date:
            # Default to 7 days for minor, 3 for major, 1 for critical
            days = {"Minor": 7, "Major": 3, "Critical": 1}
            target_close_date = add_days(today(), days.get(severity, 7))

        doc = frappe.get_doc({
            "doctype": "Non-Conformance Report",
            "ncr_number": ncr_number,
            "project": project,
            "wbs_item": wbs_item,
            "inspection_record": inspection_record,
            "description": description,
            "severity": severity,
            "identified_date": today(),
            "identified_by": frappe.session.user,
            "target_close_date": target_close_date,
            "status": "Open"
        })

        doc.insert(ignore_permissions=True)

        # Update inspection record with NCR link
        frappe.db.set_value("Inspection Record", inspection_record, {
            "non_conformance": doc.name,
            "status": "Fail"
        })

        logger.info(f"Created NCR {ncr_number} for project {project}")
        return doc

    @staticmethod
    def validate_wbs_completion(wbs_item: str) -> bool:
        """
        Ensure no open NCRs block WBS completion.

        Args:
            wbs_item: WBS Item name

        Returns:
            bool: True if WBS can be completed

        Raises:
            frappe.ValidationError: If open NCRs exist
        """
        open_ncrs = frappe.get_all(
            "Non-Conformance Report",
            filters={
                "wbs_item": wbs_item,
                "status": ["in", ["Open", "In Progress"]]
            },
            fields=["name", "ncr_number", "severity"]
        )

        if open_ncrs:
            ncr_list = ", ".join([n["ncr_number"] for n in open_ncrs])
            frappe.throw(
                _("Cannot mark WBS as Complete. {0} open NCR(s) exist: {1}").format(
                    len(open_ncrs), ncr_list
                )
            )

        return True

    @staticmethod
    def check_project_ncr_blocking(project: str) -> Dict[str, Any]:
        """
        Check if project has NCRs that block billing.

        Args:
            project: Project name

        Returns:
            dict: Blocking status
        """
        open_critical = frappe.db.count("Non-Conformance Report", {
            "project": project,
            "severity": "Critical",
            "status": ["in", ["Open", "In Progress"]]
        })

        open_major = frappe.db.count("Non-Conformance Report", {
            "project": project,
            "severity": "Major",
            "status": ["in", ["Open", "In Progress"]]
        })

        is_blocked = open_critical > 0

        return {
            "is_blocked": is_blocked,
            "open_critical": open_critical,
            "open_major": open_major,
            "can_bill": not is_blocked
        }

    @staticmethod
    def close_ncr(ncr_name: str, closure_remarks: str = None) -> "frappe.doc":
        """
        Close an NCR.

        Args:
            ncr_name: NCR document name
            closure_remarks: Optional closure remarks

        Returns:
            Updated NCR document
        """
        doc = frappe.get_doc("Non-Conformance Report", ncr_name)

        if doc.status == "Closed":
            return doc

        doc.status = "Closed"
        doc.actual_close_date = today()
        doc.closed_by = frappe.session.user
        if closure_remarks:
            doc.closure_remarks = closure_remarks

        doc.save(ignore_permissions=True)

        # Notify project manager
        frappe.publish_realtime(
            event="ncr_closed",
            message={
                "ncr": ncr_name,
                "project": doc.project,
                "wbs": doc.wbs_item,
                "severity": doc.severity
            }
        )

        logger.info(f"NCR {doc.ncr_number} closed")
        return doc

    @staticmethod
    def get_project_ncr_summary(project: str) -> Dict[str, Any]:
        """
        Get NCR summary for a project.

        Args:
            project: Project name

        Returns:
            dict: NCR summary
        """
        ncrs = frappe.get_all(
            "Non-Conformance Report",
            filters={"project": project},
            fields=["status", "severity", "name"]
        )

        summary = {
            "total": len(ncrs),
            "open": 0,
            "in_progress": 0,
            "closed": 0,
            "verified": 0,
            "critical_open": 0,
            "major_open": 0,
            "minor_open": 0
        }

        for ncr in ncrs:
            status = ncr.get("status", "")
            severity = ncr.get("severity", "")

            if status == "Open":
                summary["open"] += 1
                if severity == "Critical":
                    summary["critical_open"] += 1
                elif severity == "Major":
                    summary["major_open"] += 1
                elif severity == "Minor":
                    summary["minor_open"] += 1
            elif status == "In Progress":
                summary["in_progress"] += 1
            elif status == "Closed":
                summary["closed"] += 1
            elif status == "Verified":
                summary["verified"] += 1

        return summary


class ITPManager:
    """
    Manages Project Inspection Plans and inspection records.
    """

    @staticmethod
    def update_inspection_status(
        record_name: str,
        status: str,
        actual_reading: float = None,
        inspector: str = None,
        remarks: str = None
    ) -> "frappe.doc":
        """
        Update inspection record status.

        Args:
            record_name: Inspection Record name
            status: New status (Pass, Fail, Waived)
            actual_reading: Actual measurement reading
            inspector: Inspector user
            remarks: Inspector remarks

        Returns:
            Updated inspection record
        """
        record = frappe.get_doc("Inspection Record", record_name)

        record.status = status
        record.actual_date = today()
        record.inspector = inspector or frappe.session.user

        if actual_reading is not None:
            record.actual_reading = actual_reading

        if remarks:
            record.remarks = remarks

        # Check tolerance if pass status
        if status == "Pass" and actual_reading is not None:
            # Get hold point for tolerance check
            hold_point = frappe.get_doc("Inspection Hold Point", record.hold_point)

            if hold_point.tolerance_min is not None:
                record.is_within_tolerance = actual_reading >= hold_point.tolerance_min
            if hold_point.tolerance_max is not None:
                record.is_within_tolerance = record.is_within_tolerance and (actual_reading <= hold_point.tolerance_max)

            # Create NCR if out of tolerance
            if not record.is_within_tolerance:
                ITPManager._create_ncr_from_inspection_fail(record)

        record.save(ignore_permissions=True)

        # Update parent ITP summary
        ITPManager._update_itp_summary(record.parent)

        return record

    @staticmethod
    def _create_ncr_from_inspection_fail(record: "frappe.doc") -> None:
        """Create NCR when inspection fails."""
        # Get parent ITP to find project and WBS
        itp = frappe.get_doc("Project Inspection Plan", record.parent)

        hold_point = frappe.get_doc("Inspection Hold Point", record.hold_point)

        NCRManager.create_ncr_from_inspection(
            project=itp.project,
            wbs_item=itp.wbs_item,
            inspection_record=record.name,
            description=f"Inspection hold point '{hold_point.hold_point_name}' failed tolerance check. "
                        f"Reading: {record.actual_reading}",
            severity="Major" if record.is_within_tolerance else "Critical",
            target_close_date=add_days(today(), 7)
        )

    @staticmethod
    def _update_itp_summary(itp_name: str) -> None:
        """Update ITP summary after inspection record update."""
        itp = frappe.get_doc("Project Inspection Plan", itp_name)

        total = len(itp.inspection_records)
        passed = sum(1 for r in itp.inspection_records if r.status == "Pass")
        failed = sum(1 for r in itp.inspection_records if r.status == "Fail")
        pending = sum(1 for r in itp.inspection_records if r.status == "Pending")
        waived = sum(1 for r in itp.inspection_records if r.status == "Waived")

        progress = ((passed + waived) / total * 100) if total > 0 else 0

        frappe.db.set_value("Project Inspection Plan", itp_name, {
            "total_hold_points": total,
            "completed_hold_points": passed + failed + waived,
            "pending_hold_points": pending,
            "passed_hold_points": passed,
            "failed_hold_points": failed,
            "progress_percentage": progress
        })

        # Update status if all mandatory hold points passed
        mandatory_records = [r for r in itp.inspection_records if r.status == "Pass"]
        hold_points_with_mandatory = [
            frappe.get_doc("Inspection Hold Point", r.hold_point)
            for r in itp.inspection_records if r.status == "Pass"
        ]

        all_mandatory_passed = all(
            hp.is_mandatory == 0 or hp.is_mandatory is None
            for hp in hold_points_with_mandatory
        )

        if all_mandatory_passed and pending == 0:
            frappe.db.set_value("Project Inspection Plan", itp_name, {
                "status": "Completed"
            })

    @staticmethod
    def get_project_itp_summary(project: str) -> Dict[str, Any]:
        """
        Get ITP summary for a project.

        Args:
            project: Project name

        Returns:
            dict: ITP summary
        """
        itps = frappe.get_all(
            "Project Inspection Plan",
            filters={"project": project},
            fields=["name", "status", "total_hold_points", "progress_percentage"]
        )

        return {
            "total_itps": len(itps),
            "draft": sum(1 for i in itps if i.status == "Draft"),
            "active": sum(1 for i in itps if i.status in ["Active", "In Progress"]),
            "completed": sum(1 for i in itps if i.status == "Completed"),
            "itps": itps
        }