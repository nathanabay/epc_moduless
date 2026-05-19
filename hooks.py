"""
EPC Modules App Hooks

App-level hooks configuration for Frappe.
"""

app_name = "epc_modules"
app_title = "EPC Project Management"
app_publisher = "EPC Development Team"
app_description = "Comprehensive EPC Module for ERPNext"
app_email = "dev@organization.com"
app_icon = "octicon octicon-project"
app_color = "#3498db"
app_license = "MIT"
app_version = "1.0.0"

# App hooks
after_install = "epc_modules.event_handlers.after_install"

# doctype event hooks
doc_events = {
    "Project": {
        "after_insert": "epc_modules.event_handlers.on_project_created",
        "on_update": "epc_modules.event_handlers.on_project_updated",
        "validate": [
            "epc_modules.event_handlers.validate_project_typology",
            "epc_modules.event_handlers.validate_project",
        ]
    },
    "Purchase Order": {
        "validate": "epc_modules.event_handlers.on_po_validate"
    },
    "Purchase Receipt": {
        "validate": "epc_modules.event_handlers.validate_site_zone_allocation"
    },
    "Stock Entry": {
        "validate": "epc_modules.event_handlers.validate_stock_entry_project"
    },
    "Sales Invoice": {
        "validate": "epc_modules.event_handlers.validate_ra_bill_integration"
    }
}

# Scheduler events
scheduler_events = {
    "daily": [
        "epc_modules.tasks.schedulers.process_pending_ra_bills",
        "epc_modules.tasks.schedulers.update_project_progress",
        "epc_modules.tasks.schedulers.check_overdue_milestones",
    ],
    "weekly": [
        "epc_modules.tasks.schedulers.generate_project_reports",
    ],
    "monthly": [
        "epc_modules.tasks.schedulers.archive_completed_projects",
        "epc_modules.tasks.schedulers.calculate_retention_summary",
    ]
}

# Permissions
has_web_permission = {
    "Project": "epc_modules.event_handlers.web_permission_for_project"
}

permission_query_conditions = {
    "Project": "epc_modules.event_handlers.project_permission_query"
}

get_match_filters = {
    "Project": "epc_modules.event_handlers.get_project_match_conditions"
}

# Fixtures to load (data records only; DocType schemas are in doctype/ directory)
fixtures = [
    # Custom fields on standard DocTypes (Project, Item, NCR, Equipment Register)
    {"dt": "Custom Field", "filters": [["dt", "in", ["Project", "Item", "Non-Conformance Report", "Equipment Register"]]]},
    # Property setters for Project form customization
    {"dt": "Property Setter", "filters": [["doc_type", "=", "Project"]]},
    # Default typology data records
    {"dt": "Project Typology", "filters": []},
    # Dashboard configurations
    {"dt": "Dashboard", "filters": [["module", "=", "EPC Modules"]]},
    {"dt": "Dashboard Chart", "filters": [["module", "=", "EPC Modules"]]},
]
