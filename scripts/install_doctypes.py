import frappe
import json
import os
from pathlib import Path


def install_doctypes():
    # Set site path
    os.chdir("/home/frappe/frappe-bench/sites")
    frappe.init(site="erp.bespo.et")
    frappe.connect()

    base_path = Path("/home/frappe/frappe-bench/apps/epc_bespo/epc_modules/epc_modules/doctype")

    # Child doctypes - stored in parent folders
    child_doctypes = {
        "Cost Line Item": base_path / "Cost Line Breakdown" / "Cost Line Item.json",
        "Job Type Breakdown Rate": base_path / "Job Type" / "Job Type Breakdown Rate.json",
        "Material Plan Item": base_path / "Material Plan" / "Material Plan Item.json",
        "Gate Pass Item": base_path / "Gate Pass" / "Gate Pass Item.json",
        "Item Request Item": base_path / "Item Request" / "Item Request Item.json",
        "Transmittal Item": base_path / "Transmittal" / "Transmittal Item.json",
        "Work Package Task": base_path / "Work Package" / "Work Package Task.json",
        "Shop Drawing Item": base_path / "Shop Drawing" / "Shop Drawing Item.json",
        "Estimation Item": base_path / "Estimation" / "Estimation Item.json",
        "Budget Line": base_path / "Budget" / "Budget Line.json",
        "Inspection Checklist Item": base_path / "Inspection Checklist Item" / "Inspection Checklist Item.json",
        "Toolbox Talk Attendee": base_path / "Toolbox Talk Attendee" / "Toolbox Talk Attendee.json",
    }

    # Parent doctypes
    parent_doctypes = {
        "Cost Line Breakdown": base_path / "Cost Line Breakdown" / "Cost Line Breakdown.json",
        "Job Type": base_path / "Job Type" / "Job Type.json",
        "Material Plan": base_path / "Material Plan" / "Material Plan.json",
        "RFI Type": base_path / "rfi_type" / "rfi_type.json",
        "RFI": base_path / "rfi" / "rfi.json",
        "Gate Pass": base_path / "Gate Pass" / "Gate Pass.json",
        "Item Request": base_path / "Item Request" / "Item Request.json",
        "Transmittal": base_path / "Transmittal" / "Transmittal.json",
        "Work Package": base_path / "Work Package" / "Work Package.json",
        "Shop Drawing": base_path / "Shop Drawing" / "Shop Drawing.json",
        "Site Instruction": base_path / "Site Instruction" / "Site Instruction.json",
        "Waste Record": base_path / "Waste Record" / "Waste Record.json",
        "Estimation": base_path / "Estimation" / "Estimation.json",
        "Change Order": base_path / "Change Order" / "Change Order.json",
        "Budget": base_path / "Budget" / "Budget.json",
        "Safety Inspection": base_path / "Safety Inspection" / "Safety Inspection.json",
        "HSE Incident": base_path / "HSE Incident" / "HSE Incident.json",
        "Toolbox Talk Record": base_path / "Toolbox Talk Record" / "Toolbox Talk Record.json",
    }

    def install_dt(name, json_path):
        if json_path.exists():
            if frappe.db.exists("DocType", name):
                print(f"Already exists: {name}")
                return True

            with open(json_path) as f:
                dt = json.load(f)

            try:
                doc = frappe.get_doc({"doctype": "DocType", **dt})
                doc.insert()
                frappe.db.commit()
                print(f"Created: {name}")
                return True
            except Exception as e:
                print(f"Error {name}: {e}")
                frappe.db.rollback()
                return False
        else:
            print(f"Not found: {json_path}")
            return False

    # Install child doctypes first
    print("\nInstalling child doctypes...")
    for name, path in child_doctypes.items():
        install_dt(name, path)

    # Install parent doctypes
    print("\nInstalling parent doctypes...")
    for name, path in parent_doctypes.items():
        install_dt(name, path)

    print("\nDone!")


if __name__ == "__main__":
    install_doctypes()