"""
Arat Kilo Building Construction — WBS Structure Generator

Civil Phase-Based WBS for the 4B+SB+G+25+T high-rise building.
Maps to the 6 BOQ sections: Demolishing, Excavation, Concrete Sub/Super,
Block Works, Thermal/Moisture.
"""

import frappe
from frappe import _
from epc_modules.utils import get_epc_logger

logger = get_epc_logger(__name__)


ARAT_KILO_WBS_TEMPLATE = [
    {
        "level": 2,
        "name": "01 - Demolishing Work",
        "code_prefix": "DEMO",
        "planned_value": 3520000,
        "wbs_type": "phase",
        "children": [
            {"level": 3, "name": "RC Structure Demolition", "code_prefix": "DEMO-01", "planned_value": 3520000}
        ]
    },
    {
        "level": 2,
        "name": "02 - Excavation & Earth Work",
        "code_prefix": "EXCV",
        "planned_value": 74000500,
        "wbs_type": "phase",
        "children": [
            {"level": 3, "name": "Hard Rock Excavation 4.5-15m", "code_prefix": "EXCV-01", "planned_value": 62000000},
            {"level": 3, "name": "Hard Rock Excavation 15-16.8m", "code_prefix": "EXCV-02", "planned_value": 11970000},
            {"level": 3, "name": "Backfill & Compaction", "code_prefix": "EXCV-03", "planned_value": 973800},
            {"level": 3, "name": "Hardcore & Blinding", "code_prefix": "EXCV-04", "planned_value": 456000},
            {"level": 3, "name": "Cart Away Surplus", "code_prefix": "EXCV-05", "planned_value": 9330500},
        ]
    },
    {
        "level": 2,
        "name": "03 - Concrete Work (Sub-Structure)",
        "code_prefix": "CONS-SUB",
        "planned_value": 44310501.52,
        "wbs_type": "phase",
        "children": [
            {"level": 3, "name": "Lean Concrete C-5", "code_prefix": "CONS-SUB-01", "planned_value": 697500},
            {"level": 3, "name": "RC Concrete C-40 Sub", "code_prefix": "CONS-SUB-02", "planned_value": 9066545},
            {"level": 3, "name": "RC Concrete C-50 Sub", "code_prefix": "CONS-SUB-03", "planned_value": 6073732},
            {"level": 3, "name": "Formwork Sub-Structure", "code_prefix": "CONS-SUB-04", "planned_value": 34157270},
            {"level": 3, "name": "Steel Reinforcement Sub", "code_prefix": "CONS-SUB-05", "planned_value": 9031570},
            {"level": 3, "name": "Concrete Ancillaries", "code_prefix": "CONS-SUB-06", "planned_value": 131660},
        ]
    },
    {
        "level": 2,
        "name": "04 - Concrete Work (Super-Structure)",
        "code_prefix": "CONS-SUP",
        "planned_value": 136384329.04,
        "wbs_type": "phase",
        "children": [
            {"level": 3, "name": "RC Columns & Shear Wall C-50", "code_prefix": "CONS-SUP-01", "planned_value": 9000383},
            {"level": 3, "name": "RC Floors & Roof Slab C-40", "code_prefix": "CONS-SUP-02", "planned_value": 20142668},
            {"level": 3, "name": "Formwork Super-Structure", "code_prefix": "CONS-SUP-03", "planned_value": 107484770},
            {"level": 3, "name": "Steel Reinforcement Sup", "code_prefix": "CONS-SUP-04", "planned_value": 19017438},
            {"level": 3, "name": "Concrete Finishing & Screed", "code_prefix": "CONS-SUP-05", "planned_value": 9882120},
        ]
    },
    {
        "level": 2,
        "name": "05 - Block Works",
        "code_prefix": "BLKW",
        "planned_value": 0,
        "wbs_type": "phase",
        "children": [
            {"level": 3, "name": "200mm HCB Wall", "code_prefix": "BLKW-01", "planned_value": 0},
            {"level": 3, "name": "150mm HCB Wall", "code_prefix": "BLKW-02", "planned_value": 0},
            {"level": 3, "name": "100mm HCB Wall", "code_prefix": "BLKW-03", "planned_value": 0},
            {"level": 3, "name": "Solid Concrete Block", "code_prefix": "BLKW-04", "planned_value": 0},
            {"level": 3, "name": "Double Brick Protection", "code_prefix": "BLKW-05", "planned_value": 0},
            {"level": 3, "name": "Stone Masonry", "code_prefix": "BLKW-06", "planned_value": 0},
        ]
    },
    {
        "level": 2,
        "name": "06 - Thermal & Moisture Protection",
        "code_prefix": "THRM",
        "planned_value": 0,
        "wbs_type": "phase",
        "children": [
            {"level": 3, "name": "Bituminous Damp Proofing", "code_prefix": "THRM-01", "planned_value": 0},
            {"level": 3, "name": "Cementitious Damp Proofing", "code_prefix": "THRM-02", "planned_value": 0},
            {"level": 3, "name": "Urethane Coating", "code_prefix": "THRM-03", "planned_value": 0},
            {"level": 3, "name": "PVC Water Stopper", "code_prefix": "THRM-04", "planned_value": 0},
            {"level": 3, "name": "Granite/Marble Coping", "code_prefix": "THRM-05", "planned_value": 0},
        ]
    },
]


def create_arat_kilo_wbs_structure(project_name):
    """Create complete WBS structure for Arat Kilo building project."""
    if not frappe.db.exists("Project", project_name):
        raise ValueError(f"Project {project_name} does not exist")

    project = frappe.get_doc("Project", project_name)
    project_code = f"P-{project_name[:4].upper()}"

    # Batch load all existing WBS codes for this project to avoid N+1 queries
    existing_wbs = set(
        row.wbs_code for row in frappe.get_all(
            "WBS Item",
            filters={"project": project_name},
            fields=["wbs_code"],
        )
    )

    # Create project root WBS Item
    if project_code not in existing_wbs:
        root = frappe.get_doc({
            "doctype": "WBS Item",
            "project": project_name,
            "wbs_code": project_code,
            "wbs_name": f"{project.project_name} - WBS",
            "level": 1,
            "is_milestone": 0,
            "planned_value": 0,
            "wbs_status": "In Progress",
        })
        try:
            root.insert()
            existing_wbs.add(project_code)
        except frappe.PermissionError:
            logger.error(f"Permission denied creating root WBS Item for project {project_name}")
            raise
        except Exception as e:
            logger.error(f"Failed to insert root WBS Item for project {project_name}: {e}")
            frappe.log_error(f"WBS Creation Error: {e}", "Arat Kilo WBS")
            raise
    else:
        # Get existing root WBS Item by wbs_code
        root_rows = frappe.get_all("WBS Item", filters={"wbs_code": project_code}, fields=["name"], limit=1)
        if root_rows:
            root = frappe.get_doc("WBS Item", root_rows[0].name)
            project_code = root.wbs_code
        else:
            root = None

    created = []

    for phase in ARAT_KILO_WBS_TEMPLATE:
        phase_code = phase["code_prefix"]

        if phase_code not in existing_wbs:
            phase_doc = frappe.get_doc({
                "doctype": "WBS Item",
                "project": project_name,
                "wbs_code": phase_code,
                "wbs_name": phase["name"],
                "level": 2,
                "parent_wbs": project_code,
                "is_milestone": 0,
                "planned_value": phase["planned_value"],
                "wbs_status": "Pending",
            })
            try:
                phase_doc.insert()
                existing_wbs.add(phase_code)
            except frappe.PermissionError:
                logger.error(f"Permission denied creating phase WBS Item {phase_code} for project {project_name}")
                raise
            except Exception as e:
                logger.error(f"Failed to insert phase WBS Item {phase_code}: {e}")
                frappe.log_error(f"WBS Creation Error: {e}", "Arat Kilo WBS")
                raise
            created.append({"wbs_code": phase_code, "wbs_name": phase["name"], "level": 2})
        else:
            # Get existing phase WBS Item by wbs_code
            phase_rows = frappe.get_all("WBS Item", filters={"wbs_code": phase_code}, fields=["name"], limit=1)
            if phase_rows:
                phase_doc = frappe.get_doc("WBS Item", phase_rows[0].name)
                phase_code = phase_doc.wbs_code
            else:
                phase_doc = None

        for child_idx, child in enumerate(phase.get("children", [])):
            child_code = child["code_prefix"]

            if child_code not in existing_wbs:
                child_doc = frappe.get_doc({
                    "doctype": "WBS Item",
                    "project": project_name,
                    "wbs_code": child_code,
                    "wbs_name": child["name"],
                    "level": 3,
                    "parent_wbs": phase_code,
                    "is_milestone": 0,
                    "planned_value": child["planned_value"],
                    "wbs_status": "Pending",
                })
                try:
                    child_doc.insert()
                    existing_wbs.add(child_code)
                except frappe.PermissionError:
                    logger.error(f"Permission denied creating child WBS Item {child_code} for project {project_name}")
                    raise
                except Exception as e:
                    logger.error(f"Failed to insert child WBS Item {child_code}: {e}")
                    frappe.log_error(f"WBS Creation Error: {e}", "Arat Kilo WBS")
                    raise
                created.append({"wbs_code": child_code, "wbs_name": child["name"], "level": 3})

    logger.info(f"Created {len(created)} WBS elements for project {project_name}")
    return created


@frappe.whitelist()
def create_arat_kilo_wbs(project_name):
    """Whitelist endpoint to create Arat Kilo WBS structure."""
    frappe.has_permission("Project", "write", project_name, throw=True)

    if not frappe.db.exists("Project", project_name):
        frappe.throw(_("Project {0} does not exist").format(project_name))

    elements = create_arat_kilo_wbs_structure(project_name)
    return {
        "project": project_name,
        "elements_created": len(elements),
        "wbs_codes": [e["wbs_code"] for e in elements]
    }