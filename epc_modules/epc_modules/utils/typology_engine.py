"""
Typology Engine Module

Server-side engine for managing project typology configurations and dynamic behaviors.
"""

import frappe
from frappe import _
from typing import Dict, List, Optional, Any
from epc_modules.utils import get_epc_logger, EPCException
from epc_modules.utils.constants import (
    TYPOLOGY_ELECTROMECHANICAL,
    TYPOLOGY_CIVIL,
    TYPOLOGY_STANDARD_SERVICE,
    BILLING_RA,
    BILLING_MILESTONE,
    WBS_EQUIPMENT_BASED,
    WBS_PHASE_BASED,
    WBS_MILESTONE_BASED,
    INVENTORY_SPATIAL_ZONE,
    INVENTORY_BULK_WAREHOUSE,
    INVENTORY_HIDDEN
)

logger = get_epc_logger(__name__)


class TypologyEngine:
    """
    Engine for managing typology-based dynamic behavior in the EPC module.

    This class provides methods to:
    - Retrieve typology configurations
    - Compute field visibility based on typology
    - Apply typology-specific defaults
    - Validate typology constraints
    """

    # Field visibility configuration by typology
    FIELD_VISIBILITY_MAP = {
        TYPOLOGY_ELECTROMECHANICAL: {
            "measurement_book": {"display": True, "reqd": False},
            "site_zones": {"display": True, "reqd": True},
            "tbe_reference": {"display": True, "reqd": True},
            "equipment_tag": {"display": True, "reqd": True},
            "concrete_controls": {"display": False, "reqd": False},
            "milestone_tracking": {"display": False, "reqd": False},
            "ra_billing": {"display": True, "reqd": False},
            "milestone_billing": {"display": False, "reqd": False},
        },
        TYPOLOGY_CIVIL: {
            "measurement_book": {"display": True, "reqd": True},
            "site_zones": {"display": True, "reqd": False},
            "tbe_reference": {"display": True, "reqd": False},
            "equipment_tag": {"display": False, "reqd": False},
            "concrete_controls": {"display": True, "reqd": True},
            "milestone_tracking": {"display": False, "reqd": False},
            "ra_billing": {"display": True, "reqd": False},
            "milestone_billing": {"display": False, "reqd": False},
        },
        TYPOLOGY_STANDARD_SERVICE: {
            "measurement_book": {"display": False, "reqd": False},
            "site_zones": {"display": False, "reqd": False},
            "tbe_reference": {"display": False, "reqd": False},
            "equipment_tag": {"display": False, "reqd": False},
            "concrete_controls": {"display": False, "reqd": False},
            "milestone_tracking": {"display": True, "reqd": True},
            "ra_billing": {"display": False, "reqd": False},
            "milestone_billing": {"display": True, "reqd": False},
        }
    }

    # Tab visibility configuration by typology
    TAB_VISIBILITY_MAP = {
        TYPOLOGY_ELECTROMECHANICAL: {
            "tab_quality_gate": True,
            "tab_site_management": True,
            "tab_measurements": True,
            "tab_concrete": False,
            "tab_milestones": False,
        },
        TYPOLOGY_CIVIL: {
            "tab_quality_gate": True,
            "tab_site_management": True,
            "tab_measurements": True,
            "tab_concrete": True,
            "tab_milestones": False,
        },
        TYPOLOGY_STANDARD_SERVICE: {
            "tab_quality_gate": False,
            "tab_site_management": False,
            "tab_measurements": False,
            "tab_concrete": False,
            "tab_milestones": True,
        }
    }

    @staticmethod
    def get_typology(project_name: str) -> "frappe.doc":
        """
        Retrieve typology configuration for a project.

        Args:
            project_name: Name of the project

        Returns:
            Project Typology document

        Raises:
            EPCException: If project or typology not found
        """
        if not frappe.db.exists("Project", project_name):
            raise EPCException(f"Project {project_name} does not exist")

        project = frappe.get_doc("Project", project_name)

        if not project.project_typology:
            raise EPCException("Project must have a Typology assigned")

        if not frappe.db.exists("Project Typology", project.project_typology):
            raise EPCException(f"Typology {project.project_typology} does not exist")

        return frappe.get_doc("Project Typology", project.project_typology)

    @staticmethod
    def get_typology_by_name(typology_name: str) -> "frappe.doc":
        """
        Retrieve a typology document by name.

        Args:
            typology_name: Name of the typology

        Returns:
            Project Typology document

        Raises:
            EPCException: If typology not found
        """
        if not frappe.db.exists("Project Typology", typology_name):
            raise EPCException(f"Typology {typology_name} does not exist")

        return frappe.get_doc("Project Typology", typology_name)

    @staticmethod
    def get_field_visibility(typology_name: str) -> Dict[str, Dict[str, bool]]:
        """
        Get field visibility configuration for a typology.

        Args:
            typology_name: Name of the typology

        Returns:
            Dictionary of field visibility settings
        """
        typology = frappe.get_cached_doc("Project Typology", typology_name)
        return TypologyEngine.FIELD_VISIBILITY_MAP.get(
            typology.typology_type,
            {}
        )

    @staticmethod
    def get_tab_visibility(typology_name: str) -> Dict[str, bool]:
        """
        Get tab visibility configuration for a typology.

        Args:
            typology_name: Name of the typology

        Returns:
            Dictionary of tab visibility settings
        """
        typology = frappe.get_cached_doc("Project Typology", typology_name)
        return TypologyEngine.TAB_VISIBILITY_MAP.get(
            typology.typology_type,
            {}
        )

    @staticmethod
    def get_ui_config(typology_name: str) -> Dict[str, Any]:
        """
        Get complete UI configuration for a typology.

        Args:
            typology_name: Name of the typology

        Returns:
            Complete UI configuration dictionary
        """
        typology = frappe.get_cached_doc("Project Typology", typology_name)

        field_visibility = TypologyEngine.get_field_visibility(typology_name)
        tab_visibility = TypologyEngine.get_tab_visibility(typology_name)

        return {
            "typology_name": typology.name,
            "typology_type": typology.typology_type,
            "field_visibility": field_visibility,
            "tab_visibility": tab_visibility,
            "billing_track": typology.billing_track,
            "wbs_architecture": typology.wbs_architecture,
            "inventory_strategy": typology.inventory_strategy,
            "requires_tbe": typology.requires_tbe,
            "requires_measurement_book": typology.requires_measurement_book,
            "requires_spatial_zones": typology.requires_spatial_zones,
            "requires_itp": typology.requires_itp,
            "icon": getattr(typology, 'icon', None),
            "color": getattr(typology, 'color', None)
        }

    @staticmethod
    def apply_typology_defaults(doctype: str, doc, typology=None) -> None:
        """
        Apply typology-specific defaults to a document.

        Args:
            doctype: Document type (e.g., "Project")
            doc: Document object
            typology: Optional typology document (will be fetched if not provided)
        """
        if doctype == "Project":
            if not typology:
                typology = frappe.get_cached_doc(
                    "Project Typology",
                    doc.project_typology
                )

            typology_type = typology.typology_type

            # Apply billing track
            doc.billing_track = typology.billing_track

            # Apply WBS architecture
            if hasattr(typology, 'wbs_architecture'):
                doc.wbs_architecture = typology.wbs_architecture

            # Apply retention percentage
            if hasattr(typology, 'default_retention_percentage'):
                doc.retention_percentage = typology.default_retention_percentage

            # Apply advance recovery settings
            if hasattr(typology, 'advance_recovery_threshold'):
                doc.advance_recovery_threshold = typology.advance_recovery_threshold
            if hasattr(typology, 'advance_recovery_cap'):
                doc.advance_recovery_cap = typology.advance_recovery_cap

            # Mark as EPC project
            doc.is_epc_project = 1

            logger.info(f"Applied typology defaults for {doctype}: {typology_type}")

    @staticmethod
    def validate_project_typology(project_name: str) -> bool:
        """
        Validate that a project has a valid typology.

        Args:
            project_name: Name of the project

        Returns:
            bool: True if valid

        Raises:
            EPCException: If validation fails
        """
        try:
            typology = TypologyEngine.get_typology(project_name)
            return True
        except EPCException:
            raise
        except Exception as e:
            logger.error(f"Error validating typology for {project_name}: {str(e)}")
            raise EPCException(f"Error validating project typology: {str(e)}")

    @staticmethod
    def validate_typology_type(project_name: str, expected_type: str) -> bool:
        """
        Validate that a project's typology matches expected type.

        Args:
            project_name: Name of the project
            expected_type: Expected typology type

        Returns:
            bool: True if match

        Raises:
            EPCException: If typology doesn't match
        """
        typology = TypologyEngine.get_typology(project_name)

        if typology.typology_type != expected_type:
            raise EPCException(
                f"Project {project_name} typology is '{typology.typology_type}', "
                f"expected '{expected_type}'"
            )

        return True

    @staticmethod
    def get_all_typologies(include_inactive: bool = False) -> List[Dict]:
        """
        Get all available typologies.

        Args:
            include_inactive: Include inactive typologies

        Returns:
            List of typology configurations
        """
        filters = {}
        if not include_inactive:
            filters["is_active"] = 1

        typologies = frappe.get_all(
            "Project Typology",
            filters=filters,
            fields=["*"],
            order_by="priority asc"
        )

        return typologies

    @staticmethod
    def check_field_visibility(
        typology_name: str,
        field_name: str
    ) -> Dict[str, bool]:
        """
        Check visibility of a specific field for a typology.

        Args:
            typology_name: Name of the typology
            field_name: Name of the field

        Returns:
            Dictionary with visibility settings
        """
        field_visibility = TypologyEngine.get_field_visibility(typology_name)
        return field_visibility.get(field_name, {"display": False, "reqd": False})

    @staticmethod
    def get_required_fields(typology_name: str) -> List[str]:
        """
        Get list of required fields for a typology.

        Args:
            typology_name: Name of the typology

        Returns:
            List of required field names
        """
        field_visibility = TypologyEngine.get_field_visibility(typology_name)
        return [
            field for field, config in field_visibility.items()
            if config.get("reqd", False)
        ]

    @staticmethod
    def get_measurement_methods(typology_name: str) -> List[str]:
        """
        Get available measurement methods for a typology.

        Args:
            typology_name: Name of the typology

        Returns:
            List of allowed measurement methods
        """
        typology = frappe.get_cached_doc("Project Typology", typology_name)

        # Return typology's default if set
        if typology.measurement_method_default:
            return [typology.measurement_method_default]

        # Return based on typology type
        typology_type = typology.typology_type

        if typology_type == TYPOLOGY_CIVIL:
            return ["Unit-Based"]
        elif typology_type == TYPOLOGY_ELECTROMECHANICAL:
            return ["Percentage-Based", "Milestone-Based"]
        else:  # Standard/Service
            return ["Milestone-Based"]

    @staticmethod
    def get_inventory_strategy(typology_name: str) -> str:
        """
        Get inventory strategy for a typology.

        Args:
            typology_name: Name of the typology

        Returns:
            Inventory strategy name
        """
        typology = frappe.get_cached_doc("Project Typology", typology_name)
        return typology.inventory_strategy

    @staticmethod
    def should_require_tbe(typology_name: str) -> bool:
        """
        Check if TBE (Technical Bid Evaluation) is required.

        Args:
            typology_name: Name of the typology

        Returns:
            bool: True if TBE is required
        """
        typology = frappe.get_cached_doc("Project Typology", typology_name)
        return bool(typology.requires_tbe)

    @staticmethod
    def should_require_measurement_book(typology_name: str) -> bool:
        """
        Check if Measurement Book is required.

        Args:
            typology_name: Name of the typology

        Returns:
            bool: True if Measurement Book is required
        """
        typology = frappe.get_cached_doc("Project Typology", typology_name)
        return bool(typology.requires_measurement_book)