import frappe
import random
from datetime import datetime, timedelta

@frappe.whitelist()
def run_demo_data_creation():
    """API endpoint to run demo data creation."""
    results = {
        "typologies": create_typologies(),
        "project": create_demo_project(),
        "site_zones": create_site_zones(),
        "wbs_items": create_wbs_items(),
        "boq_items": create_boq_items(),
        "mb_entries": create_mb_entries(),
        "ra_bills": create_ra_bills(),
        "dpr_entries": create_dpr_entries(),
        "ncr_entries": create_ncr_entries(),
        "equipment": create_equipment_register(),
    }

    frappe.db.commit()
    return {"status": "success", "results": results}

def create_typologies():
    """Create project typologies."""
    typologies = [
        {
            "doctype": "Project Typology",
            "typology_type": "Electromechanical",
            "description": "Equipment-based projects with spatial zone inventory",
            "wbs_structure": "Equipment-Based",
            "billing_method": "RA-Billing",
            "inventory_strategy": "Spatial-Zone",
            "is_active": 1
        },
        {
            "doctype": "Project Typology",
            "typology_type": "Civil",
            "description": "Phase-based civil construction projects",
            "wbs_structure": "Phase-Based",
            "billing_method": "RA-Billing",
            "inventory_strategy": "Bulk-Warehouse",
            "is_active": 1
        },
        {
            "doctype": "Project Typology",
            "typology_type": "Standard/Service",
            "description": "Service and consulting projects with milestone billing",
            "wbs_structure": "Milestone-Based",
            "billing_method": "Milestone-Billing",
            "inventory_strategy": "Hidden",
            "is_active": 1
        }
    ]

    created = 0
    for typ in typologies:
        name = typ["typology_type"]
        if not frappe.db.exists("Project Typology", name):
            doc = frappe.get_doc(typ)
            doc.insert()
            created += 1
    return {"created": created, "total": len(typologies)}

def create_demo_project():
    """Create a demo project."""
    if frappe.db.exists("Project", "EPC-DEMO-001"):
        return {"created": 0, "message": "EPC-DEMO-001 already exists"}

    try:
        project = frappe.get_doc({
            "doctype": "Project",
            "project_name": "EPC-DEMO-001",
            "project_title": "Demo EPC Project - Commercial Building",
            "status": "Open",
            "is_epc_project": 1,
            "project_typology": "Civil",
            "contract_value": 50000000,
            "project_value": 50000000,
            "expected_start_date": datetime.now().date(),
            "expected_end_date": (datetime.now() + timedelta(days=365)).date(),
            "department": "Projects",
            "priority": "High"
        })
        project.insert()
        frappe.db.commit()
        return {"created": 1, "name": "EPC-DEMO-001"}
    except Exception as e:
        return {"created": 0, "error": str(e)}

def create_site_zones():
    """Create site zones."""
    zones = [
        {"zone_name": "Foundation Works", "sequence": 1},
        {"zone_name": "Structural Works", "sequence": 2},
        {"zone_name": "MEP Installation", "sequence": 3},
        {"zone_name": "Finishing Works", "sequence": 4}
    ]

    created = 0
    for zone in zones:
        if not frappe.db.exists("Site Zone", zone["zone_name"]):
            doc = frappe.get_doc({
                "doctype": "Site Zone",
                "zone_name": zone["zone_name"],
                "project": "EPC-DEMO-001",
                "zone_sequence": zone["sequence"],
                "status": "Active",
                "is_active": 1
            })
            doc.insert()
            created += 1
    return {"created": created}

def create_wbs_items():
    """Create WBS items."""
    wbs_data = [
        {"item_code": "WBS-001", "item_name": "Site Preparation", "wbs_level": 1, "planned_value": 500000},
        {"item_code": "WBS-002", "item_name": "Foundation Work", "wbs_level": 1, "planned_value": 1500000},
        {"item_code": "WBS-003", "item_name": "Structural Work", "wbs_level": 1, "planned_value": 2000000},
        {"item_code": "WBS-004", "item_name": "MEP Work", "wbs_level": 1, "planned_value": 1200000},
        {"item_code": "WBS-005", "item_name": "Finishing Work", "wbs_level": 1, "planned_value": 800000}
    ]

    created = 0
    for item in wbs_data:
        if not frappe.db.exists("WBS Item", item["item_code"]):
            doc = frappe.get_doc({
                "doctype": "WBS Item",
                "item_code": item["item_code"],
                "item_name": item["item_name"],
                "project": "EPC-DEMO-001",
                "wbs_level": item["wbs_level"],
                "planned_value": item["planned_value"],
                "status": "Draft"
            })
            doc.insert()
            created += 1
    return {"created": created}

def create_boq_items():
    """Create Custom BOQ items."""
    boq_items = [
        {"item_code": "BOQ-001", "description": "Concrete M25 Grade", "boq_quantity": 500, "unit": "cum", "unit_rate": 5500, "measurement_method": "Unit-Based"},
        {"item_code": "BOQ-002", "description": "Reinforcement Steel HYSD", "boq_quantity": 50, "unit": "MT", "unit_rate": 65000, "measurement_method": "Unit-Based"},
        {"item_code": "BOQ-003", "description": "Formwork", "boq_quantity": 2000, "unit": "sqm", "unit_rate": 450, "measurement_method": "Unit-Based"},
        {"item_code": "BOQ-004", "description": "Brickwork", "boq_quantity": 300, "unit": "cum", "unit_rate": 3500, "measurement_method": "Unit-Based"},
        {"item_code": "BOQ-005", "description": "Plastering", "boq_quantity": 5000, "unit": "sqm", "unit_rate": 250, "measurement_method": "Unit-Based"}
    ]

    created = 0
    for item in boq_items:
        if not frappe.db.exists("Custom BOQ", item["item_code"]):
            doc = frappe.get_doc({
                "doctype": "Custom BOQ",
                "item_code": item["item_code"],
                "item_name": item["description"],
                "project": "EPC-DEMO-001",
                "boq_quantity": item["boq_quantity"],
                "unit": item["unit"],
                "unit_rate": item["unit_rate"],
                "total_value": item["boq_quantity"] * item["unit_rate"],
                "measurement_method": item["measurement_method"],
                "status": "Approved"
            })
            doc.insert()
            created += 1
    return {"created": created}

def create_mb_entries():
    """Create Measurement Book entries."""
    entries = [
        {"mb_no": "MB-001", "site_zone": "Foundation Works", "description": "Foundation concrete measurement", "measurement_date": datetime.now().date(), "quantity": 120},
        {"mb_no": "MB-002", "site_zone": "Structural Works", "description": "Structural concrete measurement", "measurement_date": (datetime.now() - timedelta(days=7)).date(), "quantity": 200}
    ]

    created = 0
    for entry in entries:
        if not frappe.db.exists("Measurement Book", entry["mb_no"]):
            doc = frappe.get_doc({
                "doctype": "Measurement Book",
                "mb_no": entry["mb_no"],
                "project": "EPC-DEMO-001",
                "site_zone": entry["site_zone"],
                "description": entry["description"],
                "measurement_date": entry["measurement_date"],
                "status": "Draft"
            })
            doc.insert()
            created += 1
    return {"created": created}

def create_ra_bills():
    """Create RA Bills."""
    bills = [
        {"name": "RA-001", "ra_bill_no": "RA-001", "bill_period": "May 2026", "gross_amount": 500000, "status": "Draft"},
        {"name": "RA-002", "ra_bill_no": "RA-002", "bill_period": "April 2026", "gross_amount": 450000, "status": "Submitted"}
    ]

    created = 0
    for bill in bills:
        if not frappe.db.exists("RA Bill", bill["name"]):
            doc = frappe.get_doc({
                "doctype": "RA Bill",
                "ra_bill_no": bill["ra_bill_no"],
                "project": "EPC-DEMO-001",
                "bill_period": bill["bill_period"],
                "gross_amount": bill["gross_amount"],
                "status": bill["status"]
            })
            doc.insert()
            created += 1
    return {"created": created}

def create_dpr_entries():
    """Create Daily Progress Reports."""
    created = 0
    for i in range(1, 4):
        dpr_no = f"DPR-{i:03d}"
        if not frappe.db.exists("Daily Progress Report", dpr_no):
            doc = frappe.get_doc({
                "doctype": "Daily Progress Report",
                "report_no": dpr_no,
                "project": "EPC-DEMO-001",
                "report_date": (datetime.now() - timedelta(days=i)).date(),
                "site_zone": ["Foundation Works", "Structural Works", "MEP Installation"][i-1],
                "weather_condition": random.choice(["Sunny", "Cloudy", "Rainy"]),
                "work_summary": f"Day {i} progress - Work proceeding as planned",
                "status": "Draft"
            })
            doc.insert()
            created += 1
    return {"created": created}

def create_ncr_entries():
    """Create Non-Conformance Reports."""
    ncrs = [
        {"ncr_no": "NCR-001", "description": "Concrete strength below specified grade", "category": "Material Non-Conformance", "priority": "High"},
        {"ncr_no": "NCR-002", "description": "Dimension variation in structural element", "category": "Workmanship", "priority": "Medium"}
    ]

    created = 0
    for ncr in ncrs:
        if not frappe.db.exists("Non-Conformance Report", ncr["ncr_no"]):
            doc = frappe.get_doc({
                "doctype": "Non-Conformance Report",
                "ncr_no": ncr["ncr_no"],
                "project": "EPC-DEMO-001",
                "description": ncr["description"],
                "category": ncr["category"],
                "priority": ncr["priority"],
                "status": "Open"
            })
            doc.insert()
            created += 1
    return {"created": created}

def create_equipment_register():
    """Create Equipment Register entries."""
    equipment = [
        {"equipment_id": "EXC-001", "equipment_name": "Excavator CAT 320", "equipment_type": "Earthwork", "status": "Available"},
        {"equipment_id": "CRN-001", "equipment_name": "Tower Crane 5T", "equipment_type": "Lifting", "status": "In Use"},
        {"equipment_id": "CEM-001", "equipment_name": "Concrete Mixer 500L", "equipment_type": "Concrete", "status": "Available"},
        {"equipment_id": "PMP-001", "equipment_name": "Concrete Pump 20M", "equipment_type": "Concrete", "status": "Under Maintenance"}
    ]

    created = 0
    for eq in equipment:
        if not frappe.db.exists("Equipment Register", eq["equipment_id"]):
            doc = frappe.get_doc({
                "doctype": "Equipment Register",
                "equipment_id": eq["equipment_id"],
                "equipment_name": eq["equipment_name"],
                "equipment_type": eq["equipment_type"],
                "project": "EPC-DEMO-001",
                "status": eq["status"]
            })
            doc.insert()
            created += 1
    return {"created": created}
