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
    }

    # Parent doctypes
    parent_doctypes = {
        "Cost Line Breakdown": base_path / "Cost Line Breakdown" / "Cost Line Breakdown.json",
        "Job Type": base_path / "Job Type" / "Job Type.json",
        "Material Plan": base_path / "Material Plan" / "Material Plan.json",
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