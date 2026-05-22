"""
WBS Structure Generator Module

Dynamic Work Breakdown Structure generation based on project typology.
"""

import frappe
from frappe import _
from typing import Dict, List, Optional, Any
from epc_modules.utils import get_epc_logger, EPCException
from epc_modules.utils.constants import (
    WBS_EQUIPMENT_BASED,
    WBS_PHASE_BASED,
    WBS_MILESTONE_BASED,
    TYPOLOGY_ELECTROMECHANICAL,
    TYPOLOGY_CIVIL,
    TYPOLOGY_STANDARD_SERVICE
)

logger = get_epc_logger(__name__)


class WBSStructureGenerator:
    """
    Generator for creating and managing Work Breakdown Structures
    based on project typology.
    """

    # WBS level configurations by architecture type
    LEVEL_CONFIG = {
        WBS_EQUIPMENT_BASED: {
            1: {"name": "Project", "label": "Project", "max_items": 1},
            2: {"name": "System", "label": "System/Subsystem", "max_items": 20},
            3: {"name": "Package", "label": "Package", "max_items": 100},
            4: {"name": "Activity", "label": "Activity", "max_items": 500},
            5: {"name": "Task", "label": "Task", "max_items": 2000},
        },
        WBS_PHASE_BASED: {
            1: {"name": "Project", "label": "Project", "max_items": 1},
            2: {"name": "Phase", "label": "Phase", "max_items": 10},
            3: {"name": "Work Package", "label": "Work Package", "max_items": 50},
            4: {"name": "Activity", "label": "Activity", "max_items": 200},
            5: {"name": "Task", "label": "Task", "max_items": 1000},
        },
        WBS_MILESTONE_BASED: {
            1: {"name": "Project", "label": "Project", "max_items": 1},
            2: {"name": "Milestone", "label": "Milestone", "max_items": 20},
            3: {"name": "Deliverable", "label": "Deliverable", "max_items": 100},
            4: {"name": "Subtask", "label": "Subtask", "max_items": 500},
        },
    }

    # Standard WBS templates
    WBS_TEMPLATES = {
        TYPOLOGY_ELECTROMECHANICAL: [
            {"level": 2, "name": "Procurement", "code_prefix": "PROC"},
            {"level": 2, "name": "Installation", "code_prefix": "INST"},
            {"level": 2, "name": "Testing", "code_prefix": "TEST"},
            {"level": 2, "name": "Commissioning", "code_prefix": "COMM"},
        ],
        TYPOLOGY_CIVIL: [
            {"level": 2, "name": "Site Preparation", "code_prefix": "SITE"},
            {"level": 2, "name": "Foundation", "code_prefix": "FOUN"},
            {"level": 2, "name": "Structure", "code_prefix": "STRU"},
            {"level": 2, "name": "Finishing", "code_prefix": "FINI"},
            {"level": 2, "name": "Handover", "code_prefix": "HAND"},
        ],
        TYPOLOGY_STANDARD_SERVICE: [
            {"level": 2, "name": "Planning", "code_prefix": "PLAN"},
            {"level": 2, "name": "Execution", "code_prefix": "EXEC"},
            {"level": 2, "name": "Delivery", "code_prefix": "DELV"},
        ],
    }

    @staticmethod
    def get_architecture_for_typology(typology_name: str) -> str:
        """
        Get WBS architecture for a given typology.

        Args:
            typology_name: Name of the typology

        Returns:
            WBS architecture type
        """
        typology = frappe.get_cached_doc("Project Typology", typology_name)
        return typology.wbs_architecture or WBS_PHASE_BASED

    @staticmethod
    def get_wbs_level_config(architecture: str, level: int) -> Dict:
        """
        Get configuration for a specific WBS level.

        Args:
            architecture: WBS architecture type
            level: WBS level (1-5)

        Returns:
            Level configuration dictionary
        """
        config = WBSStructureGenerator.LEVEL_CONFIG.get(architecture, {})
        return config.get(level, {})

    @staticmethod
    def generate_wbs_code(
        parent_code: str,
        level: int,
        index: int,
        architecture: str
    ) -> str:
        """
        Generate WBS code for a new element.

        Args:
            parent_code: Parent WBS code
            level: Current level
            index: Index at this level
            architecture: WBS architecture type

        Returns:
            Generated WBS code
        """
        level_config = WBSStructureGenerator.get_wbs_level_config(architecture, level)

        if not level_config:
            return f"{parent_code}.{index:03d}"

        code_prefix = level_config.get("code_prefix", "")
        level_num = level

        if code_prefix:
            return f"{parent_code}.{code_prefix}{index:02d}"
        return f"{parent_code}.L{level_num}{index:03d}"

    @staticmethod
    def create_wbs_structure(project_name: str, typology_name: str) -> List[Dict]:
        """
        Create complete WBS structure for a project based on typology.

        Args:
            project_name: Name of the project
            typology_name: Name of the typology

        Returns:
            List of WBS element dictionaries
        """
        typology = frappe.get_cached_doc("Project Typology", typology_name)
        architecture = typology.wbs_architecture or WBS_PHASE_BASED
        typology_type = typology.typology_type

        import hashlib
        # Use full project name + random component to avoid collision
        short = hashlib.md5(project_name.encode()).hexdigest()[:6].upper()
        project_code = f"P-{short}"

        wbs_elements = []

        # Add project root level
        wbs_elements.append({
            "wbs_code": project_code,
            "wbs_name": project_name,
            "level": 1,
            "parent_wbs": None,
            "is_milestone": False,
            "planned_value": 0,
        })

        # Get template for typology
        template = WBSStructureGenerator.WBS_TEMPLATES.get(
            typology_type,
            WBSStructureGenerator.WBS_TEMPLATES[TYPOLOGY_STANDARD_SERVICE]
        )

        # Generate WBS elements from template
        for level2_item in template:
            level2_code = WBSStructureGenerator.generate_wbs_code(
                project_code, 2, template.index(level2_item) + 1, architecture
            )

            wbs_elements.append({
                "wbs_code": level2_code,
                "wbs_name": level2_item["name"],
                "level": 2,
                "parent_wbs": project_code,
                "is_milestone": False,
                "planned_value": 0,
            })

        logger.info(f"Generated WBS structure for project {project_name}: {len(wbs_elements)} elements")
        return wbs_elements

    @staticmethod
    def add_wbs_element(
        parent_wbs: str,
        name: str,
        level: int,
        is_milestone: bool = False,
        planned_value: float = 0
    ) -> Dict:
        """
        Add a single WBS element under a parent.

        Args:
            parent_wbs: Parent WBS code
            name: Element name
            level: WBS level
            is_milestone: Whether this is a milestone
            planned_value: Planned value

        Returns:
            Created WBS element
        """
        # Lock the parent row and get architecture to determine WBS type
        parent_rows = frappe.get_all(
            "WBS Item",
            filters={"wbs_code": parent_wbs},
            fields=["name", "architecture"],
            limit=1
        )
        if not parent_rows:
            frappe.throw(_("Parent WBS Item with code {0} not found").format(parent_wbs))
        architecture = parent_rows[0].architecture or WBS_PHASE_BASED

        # Lock the parent row to prevent race conditions on concurrent inserts
        frappe.db.sql(
            "SELECT name FROM `tabWBS Item` WHERE wbs_code = %s FOR UPDATE",
            (parent_wbs,)
        )

        # Get next index at this level using a single query
        existing = frappe.get_all(
            "WBS Item",
            filters={"parent_wbs": parent_wbs},
            fields=["wbs_code"],
            order_by="wbs_code desc",
            limit=1
        )

        index = 1
        if existing:
            last_code = existing[0].wbs_code
            try:
                index = int(last_code.split(".")[-1]) + 1
            except (ValueError, IndexError):
                index = 1

        wbs_code = WBSStructureGenerator.generate_wbs_code(
            parent_wbs, level, index, architecture
        )

        frappe.has_permission("WBS Item", "create", throw=True)
        doc = frappe.get_doc({
            "doctype": "WBS Item",
            "wbs_code": wbs_code,
            "wbs_name": name,
            "level": level,
            "parent_wbs": parent_wbs,
            "is_milestone": is_milestone,
            "planned_value": planned_value,
            "architecture": architecture
        })
        try:
            doc.insert()
        except Exception as e:
            frappe.log_error(f"Failed to insert WBS Item: {str(e)}", "WBS Generator Error")
            raise

        return {"wbs_code": wbs_code, "wbs_name": name}

    @staticmethod
    def get_wbs_hierarchy(project_name: str) -> List[Dict]:
        """
        Get complete WBS hierarchy for a project.

        Args:
            project_name: Name of the project

        Returns:
            Hierarchical list of WBS elements
        """
        elements = frappe.get_all(
            "WBS Item",
            filters={"project": project_name},
            fields=["wbs_code", "wbs_name", "level", "parent_wbs", "is_milestone", "planned_value"],
            order_by="wbs_code"
        )

        return elements

    @staticmethod
    def get_wbs_Element_cost_distribution(project_name: str) -> Dict:
        """
        Calculate cost distribution across WBS levels.

        Args:
            project_name: Name of the project

        Returns:
            Cost distribution by level and element
        """
        hierarchy = WBSStructureGenerator.get_wbs_hierarchy(project_name)

        distribution = {
            "total_value": 0,
            "by_level": {},
            "by_element": {}
        }

        for element in hierarchy:
            value = element.get("planned_value", 0)
            level = element.get("level", 1)

            distribution["total_value"] += value
            distribution["by_level"][level] = distribution["by_level"].get(level, 0) + value
            distribution["by_element"][element["wbs_code"]] = value

        return distribution
