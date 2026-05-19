"""Add demo Cost & Progress data to WBS items for PROJ-0004"""
import frappe

project_name = "PROJ-0004"

# Get project and total contract value
project = frappe.get_doc("Project", project_name)
total_contract_value = project.contract_value or project.total_contract_value or 439_500_000

# Section allocation based on BOQ import (approximate percentages)
section_allocation = {
    "DEMO": 0.02,      # 2%
    "EXCV": 0.05,      # 5%
    "CONS-SUB": 0.18,  # 18%
    "CONS-SUP": 0.35,  # 35%
    "BLKW": 0.25,      # 25%
    "THRM": 0.15,      # 15%
}

# Progress by section
section_progress = {
    "DEMO": 15.0,
    "EXCV": 10.0,
    "CONS-SUB": 5.0,
    "CONS-SUP": 0.0,
    "BLKW": 0.0,
    "THRM": 0.0,
}

# Get all WBS items for project
wbs_items = frappe.get_all(
    "WBS Item",
    filters={"project": project_name},
    fields=["name", "wbs_code", "parent_wbs"]
)

print(f"Found {len(wbs_items)} WBS items for {project_name}")
updated = 0

for item in wbs_items:
    wbs_code = item.wbs_code or ""
    parent_wbs = item.parent_wbs or ""

    # Determine section prefix
    if wbs_code in section_allocation:
        section_prefix = wbs_code
        is_leaf = False
    elif parent_wbs and parent_wbs in section_allocation:
        section_prefix = parent_wbs
        is_leaf = True
    else:
        # Try matching prefix from wbs_code
        section_prefix = None
        for sec in section_allocation:
            if wbs_code.startswith(sec) or wbs_code == sec:
                section_prefix = sec
                is_leaf = "-" in wbs_code
                break

    if section_prefix and section_prefix in section_allocation:
        alloc_pct = section_allocation[section_prefix]
        progress = section_progress.get(section_prefix, 0.0)
        budget = total_contract_value * alloc_pct
        earned = budget * (progress / 100)
        cost = earned * 0.95
        status = "In Progress" if progress > 0 else "Pending"
    else:
        # Default for misc items
        budget = 0
        progress = 0.0
        earned = 0
        cost = 0
        status = "Pending"

    frappe.db.set_value("WBS Item", item.name, {
        "budget_allocated": budget,
        "physical_progress": progress,
        "earned_value": earned,
        "cost_incurred": cost,
        "wbs_status": status
    })
    updated += 1

frappe.db.commit()
print(f"Updated {updated} WBS items")
print(f"Project: {project_name}")
print(f"Total Contract Value: {total_contract_value:,.0f} ETB")