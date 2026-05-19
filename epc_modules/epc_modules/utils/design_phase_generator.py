"""
Design Phase Generator

Auto-generates design phases based on ECDSWC workflows
from the MiOT (Menilik Institute of Technology) reference documents.
"""
import frappe
from frappe import _
from frappe.utils import add_days, add_months


PHASE_TEMPLATES = {
    "Civil": [
        {
            "phase_number": 1,
            "phase_name": "Analysis & Information",
            "phase_type": "Design",
            "duration_weeks": 1.0,
            "checklist_template": "ECDSWC-Predesign-Study",
            "deliverables": [
                {"deliverable_name": "Project Background Report", "document_type": "Report", "format": "A3 Report", "copies_required": 2},
                {"deliverable_name": "Case Study Analysis", "document_type": "Report", "format": "A3 Report", "copies_required": 2},
                {"deliverable_name": "Site Analysis Report", "document_type": "Report", "format": "A3 Report", "copies_required": 2},
            ]
        },
        {
            "phase_number": 2,
            "phase_name": "Setting Ideas",
            "phase_type": "Design",
            "duration_weeks": 1.0,
            "deliverables": [
                {"deliverable_name": "Concept Diagrams", "document_type": "Drawing", "format": "A1 Panels", "copies_required": 2},
                {"deliverable_name": "Massing Study", "document_type": "Drawing", "format": "A1 Panels", "copies_required": 2},
            ]
        },
        {
            "phase_number": 3,
            "phase_name": "Schematic + Preliminary Design",
            "phase_type": "Design",
            "duration_weeks": 3.5,
            "checklist_template": "ECDSWC-Schematic-Design",
            "deliverables": [
                {"deliverable_name": "Schematic Design Report", "document_type": "Report", "format": "A3 Report", "copies_required": 2},
                {"deliverable_name": "2D Drawings", "document_type": "Drawing", "format": "A1 Panels", "copies_required": 2},
                {"deliverable_name": "3D Perspectives", "document_type": "Drawing", "format": "A1 Panels", "copies_required": 2},
                {"deliverable_name": "Physical/Digital Model", "document_type": "Model", "format": "Physical", "copies_required": 1},
                {"deliverable_name": "Internal Presentation", "document_type": "Presentation", "format": "Digital", "copies_required": 1},
            ]
        },
        {
            "phase_number": 4,
            "phase_name": "Final Design & Detailing",
            "phase_type": "Design",
            "duration_weeks": 2.0,
            "deliverables": [
                {"deliverable_name": "Final Design Drawings", "document_type": "Drawing", "format": "A1 Panels", "copies_required": 4},
                {"deliverable_name": "Design Development Report", "document_type": "Report", "format": "A3 Report", "copies_required": 2},
            ]
        },
        {
            "phase_number": 5,
            "phase_name": "Specialty Design",
            "phase_type": "Specialty",
            "duration_weeks": 4.0,
            "deliverables": [
                {"deliverable_name": "Structural Design Drawings", "document_type": "Drawing", "format": "A1 Panels", "copies_required": 3},
                {"deliverable_name": "Electrical Design Drawings", "document_type": "Drawing", "format": "A1 Panels", "copies_required": 3},
                {"deliverable_name": "Sanitary Design Drawings", "document_type": "Drawing", "format": "A1 Panels", "copies_required": 3},
                {"deliverable_name": "Mechanical Design Drawings", "document_type": "Drawing", "format": "A1 Panels", "copies_required": 3},
            ]
        },
        {
            "phase_number": 6,
            "phase_name": "Documentation",
            "phase_type": "Documentation",
            "duration_weeks": 5.5,
            "deliverables": [
                {"deliverable_name": "Specifications", "document_type": "Specification", "format": "A4 Report", "copies_required": 3},
                {"deliverable_name": "Bill of Quantities", "document_type": "BOQ", "format": "A4 Report", "copies_required": 3},
                {"deliverable_name": "Cost Estimation", "document_type": "Cost Estimate", "format": "A4 Report", "copies_required": 3},
                {"deliverable_name": "SBD Document", "document_type": "Report", "format": "A4 Report", "copies_required": 3},
            ]
        },
        {
            "phase_number": 7,
            "phase_name": "Plotting & Printing",
            "phase_type": "Documentation",
            "duration_weeks": 1.0,
            "deliverables": [
                {"deliverable_name": "Final Printed Drawings", "document_type": "Drawing", "format": "A1 Panels", "copies_required": 6},
                {"deliverable_name": "Final Printed Reports", "document_type": "Report", "format": "A3 Report", "copies_required": 6},
            ]
        },
    ],
    "Electromechanical": [
        {
            "phase_number": 1,
            "phase_name": "Analysis & Information",
            "phase_type": "Design",
            "duration_weeks": 1.0,
            "checklist_template": "ECDSWC-Predesign-Study",
            "deliverables": [
                {"deliverable_name": "Project Background Report", "document_type": "Report", "format": "A3 Report", "copies_required": 2},
            ]
        },
        {
            "phase_number": 2,
            "phase_name": "Setting Ideas",
            "phase_type": "Design",
            "duration_weeks": 1.0,
            "deliverables": [
                {"deliverable_name": "Concept Layouts", "document_type": "Drawing", "format": "A1 Panels", "copies_required": 2},
            ]
        },
        {
            "phase_number": 3,
            "phase_name": "Schematic + Preliminary Design",
            "phase_type": "Design",
            "duration_weeks": 3.5,
            "checklist_template": "ECDSWC-Schematic-Design",
            "deliverables": [
                {"deliverable_name": "Schematic Drawings", "document_type": "Drawing", "format": "A1 Panels", "copies_required": 2},
                {"deliverable_name": "Equipment Layout", "document_type": "Drawing", "format": "A1 Panels", "copies_required": 2},
                {"deliverable_name": "Single Line Diagrams", "document_type": "Drawing", "format": "A1 Panels", "copies_required": 2},
            ]
        },
        {
            "phase_number": 4,
            "phase_name": "Final Design & Detailing",
            "phase_type": "Design",
            "duration_weeks": 2.0,
            "deliverables": [
                {"deliverable_name": "Final Design Drawings", "document_type": "Drawing", "format": "A1 Panels", "copies_required": 4},
            ]
        },
        {
            "phase_number": 5,
            "phase_name": "Specialty Design",
            "phase_type": "Specialty",
            "duration_weeks": 4.0,
            "deliverables": [
                {"deliverable_name": "Electrical Detail Design", "document_type": "Drawing", "format": "A1 Panels", "copies_required": 3},
                {"deliverable_name": "Mechanical Detail Design", "document_type": "Drawing", "format": "A1 Panels", "copies_required": 3},
                {"deliverable_name": "Control & Instrumentation", "document_type": "Drawing", "format": "A1 Panels", "copies_required": 3},
            ]
        },
        {
            "phase_number": 6,
            "phase_name": "Documentation",
            "phase_type": "Documentation",
            "duration_weeks": 5.5,
            "deliverables": [
                {"deliverable_name": "Specifications", "document_type": "Specification", "format": "A4 Report", "copies_required": 3},
                {"deliverable_name": "Bill of Quantities", "document_type": "BOQ", "format": "A4 Report", "copies_required": 3},
                {"deliverable_name": "Cost Estimation", "document_type": "Cost Estimate", "format": "A4 Report", "copies_required": 3},
            ]
        },
        {
            "phase_number": 7,
            "phase_name": "Plotting & Printing",
            "phase_type": "Documentation",
            "duration_weeks": 1.0,
            "deliverables": [
                {"deliverable_name": "Final Printed Set", "document_type": "Drawing", "format": "A1 Panels", "copies_required": 6},
            ]
        },
    ],
    "Standard/Service": [
        {
            "phase_number": 1,
            "phase_name": "Scope Definition",
            "phase_type": "Design",
            "duration_weeks": 1.0,
            "deliverables": [
                {"deliverable_name": "Scope of Services", "document_type": "Report", "format": "A4 Report", "copies_required": 2},
            ]
        },
        {
            "phase_number": 2,
            "phase_name": "Service Planning",
            "phase_type": "Design",
            "duration_weeks": 2.0,
            "deliverables": [
                {"deliverable_name": "Service Delivery Plan", "document_type": "Report", "format": "A4 Report", "copies_required": 2},
            ]
        },
        {
            "phase_number": 3,
            "phase_name": "Execution",
            "phase_type": "Construction",
            "duration_weeks": 8.0,
            "deliverables": [
                {"deliverable_name": "Progress Reports", "document_type": "Report", "format": "A4 Report", "copies_required": 2},
                {"deliverable_name": "Milestone Deliverables", "document_type": "Report", "format": "A4 Report", "copies_required": 2},
            ]
        },
        {
            "phase_number": 4,
            "phase_name": "Closeout",
            "phase_type": "Documentation",
            "duration_weeks": 1.0,
            "deliverables": [
                {"deliverable_name": "Final Report", "document_type": "Report", "format": "A4 Report", "copies_required": 4},
            ]
        },
    ],
}


@frappe.whitelist()
def generate_design_phases(project, typology_type=None):
    """Auto-generate design phases based on typology."""
    if not typology_type:
        project_doc = frappe.get_cached_doc("Project", project)
        if not project_doc.project_typology:
            return {"created": 0, "message": "No typology assigned to project"}
        typology = frappe.get_cached_doc("Project Typology", project_doc.project_typology)
        typology_type = typology.typology_type

    templates = PHASE_TEMPLATES.get(typology_type, [])
    if not templates:
        return {"created": 0, "message": f"No phase template for {typology_type}"}

    created = 0
    for phase_data in templates:
        phase_code = f"DP-{project}-{phase_data['phase_number']:02d}"

        if frappe.db.exists("Design Phase", phase_code):
            continue

        doc = frappe.get_doc({
            "doctype": "Design Phase",
            "phase_code": phase_code,
            "phase_name": phase_data["phase_name"],
            "project": project,
            "phase_number": phase_data["phase_number"],
            "phase_type": phase_data["phase_type"],
            "duration_weeks": phase_data["duration_weeks"],
            "status": "Not Started",
            "gate_status": "Pending" if phase_data.get("checklist_template") else "Not Required",
            "checklist_template": phase_data.get("checklist_template"),
        })

        for deliv in phase_data.get("deliverables", []):
            doc.append("deliverables", deliv)

        doc.insert(ignore_permissions=True)
        created += 1

    frappe.db.commit()
    return {"created": created, "total": len(templates), "typology": typology_type}


@frappe.whitelist()
def get_design_phases(project):
    """Get all design phases for a project."""
    phases = frappe.get_all(
        "Design Phase",
        filters={"project": project},
        fields=["name", "phase_code", "phase_name", "phase_number", "phase_type",
                "status", "gate_status", "duration_weeks",
                "planned_start", "planned_end", "actual_start", "actual_end",
                "checklist_template"],
        order_by="phase_number asc"
    )

    for phase in phases:
        phase["team_members"] = frappe.get_all(
            "Design Phase Team",
            filters={"parent": phase["name"]},
            fields=["discipline", "role", "professional", "no_of_professionals"]
        )
        phase["deliverables_list"] = frappe.get_all(
            "Design Deliverable",
            filters={"parent": phase["name"]},
            fields=["deliverable_name", "document_type", "status", "submission_date", "approval_date"]
        )

    return phases


@frappe.whitelist()
def advance_design_phase(design_phase, new_status=None):
    """Advance a design phase to the next status."""
    doc = frappe.get_doc("Design Phase", design_phase)

    status_flow = ["Not Started", "In Progress", "Under Review", "Approved", "Completed"]

    if new_status:
        if new_status not in status_flow:
            frappe.throw(f"Invalid status: {new_status}")
        doc.status = new_status
    else:
        current_idx = status_flow.index(doc.status) if doc.status in status_flow else -1
        if current_idx < len(status_flow) - 1:
            doc.status = status_flow[current_idx + 1]
        else:
            frappe.throw("Phase is already in final status")

    if doc.status == "In Progress" and not doc.actual_start:
        from frappe.utils import today
        doc.actual_start = today()

    if doc.status == "Completed" and not doc.actual_end:
        from frappe.utils import today
        doc.actual_end = today()

    if doc.status == "Approved" and doc.gate_status == "Pending":
        doc.gate_status = "Pass"

    doc.save(ignore_permissions=True)
    frappe.db.commit()
    return {"phase": doc.name, "status": doc.status}
