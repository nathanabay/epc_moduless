import frappe
import json
import os
from pathlib import Path


def install_workspace_fixtures(site=None):
    site = site or frappe.local.site
    os.chdir(frappe.get_site_path("sites"))
    frappe.init(site=site)
    frappe.connect()

    fixtures_path = Path(frappe.get_app_path("epc_bespo")) / "fixtures"

    # Install workspaces
    workspaces_file = fixtures_path / "workspaces.json"
    if workspaces_file.exists():
        with open(workspaces_file) as f:
            workspaces = json.load(f)

        for ws in workspaces:
            try:
                if frappe.db.exists("Workspace", ws["name"]):
                    existing = frappe.get_doc("Workspace", ws["name"])
                    existing.delete()
                    frappe.db.commit()
                    print(f"Deleted existing: {ws['name']}")

                doc = frappe.get_doc({"doctype": "Workspace", **ws})
                doc.insert(ignore_if_duplicate=True)
                frappe.db.commit()
                print(f"Created workspace: {ws['name']}")
            except Exception as e:
                print(f"Error {ws['name']}: {e}")
                frappe.db.rollback()

    # Install workspace shortcuts
    shortcuts_file = fixtures_path / "workspace_shortcuts.json"
    if shortcuts_file.exists():
        with open(shortcuts_file) as f:
            shortcuts = json.load(f)

        for sc in shortcuts:
            try:
                parent_ws = sc["parent"]

                # Ensure workspace exists
                if not frappe.db.exists("Workspace", parent_ws):
                    print(f"Workspace not found: {parent_ws}")
                    continue

                # Delete existing shortcut if any
                existing = frappe.db.exists("Workspace Shortcut", {"parent": parent_ws, "link_to": sc["link_to"]})
                if existing:
                    frappe.db.delete("Workspace Shortcut", existing)
                    frappe.db.commit()

                doc = frappe.get_doc({"doctype": "Workspace Shortcut", **sc})
                doc.insert(ignore_if_duplicate=True)
                frappe.db.commit()
                print(f"Created shortcut: {sc['link_to']} in {parent_ws}")
            except Exception as e:
                print(f"Error {sc['link_to']}: {e}")
                frappe.db.rollback()

    print("\nWorkspace fixtures installed!")


if __name__ == "__main__":
    install_workspace_fixtures()
