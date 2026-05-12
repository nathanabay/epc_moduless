"""
Validators Module

Validation utilities for EPC module.
"""

import frappe
from frappe import _
from epc_modules.utils import get_epc_logger

logger = get_epc_logger(__name__)


class EPCValidator:
    """Validator class for EPC module validations."""

    @staticmethod
    def validate_project_typology(project_name):
        """
        Validate that a project has a valid typology assigned.

        Args:
            project_name: Name of the project

        Returns:
            bool: True if valid

        Raises:
            frappe.ValidationError: If validation fails
        """
        if not frappe.db.exists("Project", project_name):
            frappe.throw(_("Project {0} does not exist").format(project_name))

        project = frappe.get_doc("Project", project_name)

        if not project.get("project_typology"):
            frappe.throw(_("Project must have a Typology assigned"))

        if not frappe.db.exists("Project Typology", project.project_typology):
            frappe.throw(_("Typology {0} does not exist").format(project.project_typology))

        return True

    @staticmethod
    def validate_electromechanical_procurement(project_name, item_code):
        """
        Validate procurement for electromechanical projects.

        Args:
            project_name: Name of the project
            item_code: Item code being procured

        Returns:
            bool: True if valid

        Raises:
            frappe.ValidationError: If TBE is required but not present
        """
        project = frappe.get_cached_doc("Project", project_name)

        if not project.is_epc_project or not project.project_typology:
            return True

        typology = frappe.get_cached_doc("Project Typology", project.project_typology)

        if typology.typology_type != "Electromechanical":
            return True

        if typology.requires_tbe:
            # Check if TBE exists for this item
            tbe_exists = frappe.db.exists("Technical Bid Evaluation", {
                "project": project_name,
                "item_code": item_code,
                "status": "Approved"
            })

            if not tbe_exists:
                frappe.throw(
                    _("Technical Bid Evaluation (TBE) is required for {0} "
                      "in Electromechanical projects").format(item_code)
                )

        return True

    @staticmethod
    def validate_measurement_book(project_name, wbs_item):
        """
        Validate that measurement book exists for civil projects.

        Args:
            project_name: Name of the project
            wbs_item: WBS item reference

        Returns:
            bool: True if valid
        """
        project = frappe.get_cached_doc("Project", project_name)

        if not project.is_epc_project or not project.project_typology:
            return True

        typology = frappe.get_cached_doc("Project Typology", project.project_typology)

        if typology.typology_type == "Civil" and typology.requires_measurement_book:
            # Check if measurement book exists
            mb_exists = frappe.db.exists("Measurement Book", {
                "project": project_name,
                "wbs_item": wbs_item,
                "certification_status": "Certified"
            })

            if not mb_exists:
                logger.warning(
                    f"Measurement Book not certified for WBS {wbs_item} in project {project_name}"
                )

        return True

    @staticmethod
    def validate_concrete_grade(grade):
        """
        Validate concrete grade against allowed values.

        Args:
            grade: Concrete grade (e.g., "M20", "M30")

        Returns:
            bool: True if valid

        Raises:
            frappe.ValidationError: If grade is invalid
        """
        from epc_modules.utils.constants import CONCRETE_GRADES

        if grade not in CONCRETE_GRADES:
            frappe.throw(
                _("Invalid concrete grade {0}. Allowed grades: {1}").format(
                    grade, ", ".join(CONCRETE_GRADES)
                )
            )

        return True

    @staticmethod
    def validate_exposure_condition(condition):
        """
        Validate exposure condition against allowed values.

        Args:
            condition: Exposure condition

        Returns:
            bool: True if valid

        Raises:
            frappe.ValidationError: If condition is invalid
        """
        from epc_modules.utils.constants import EXPOSURE_CHOICES

        if condition not in EXPOSURE_CHOICES:
            frappe.throw(
                _("Invalid exposure condition {0}. Allowed: {1}").format(
                    condition, ", ".join(EXPOSURE_CHOICES)
                )
            )

        return True