from frappe.boot import get_bootinfo


def get_data():
    return [
        {
            "module_name": "EPC Modules",
            "color": "blue",
            "icon": "octicon octicon-project",
            "type": "module",
            "label": "EPC Project Management",
            "links": [
                {
                    "label": "Projects",
                    "icon": "octicon octicon-project",
                    "type": "doctype",
                    "name": "Project",
                    "description": "Manage EPC projects"
                },
                {
                    "label": "Project Typologies",
                    "icon": "octicon octicon-settings",
                    "type": "doctype",
                    "name": "Project Typology",
                    "description": "Configure project typologies"
                },
                {
                    "label": "Site Zones",
                    "icon": "octicon octicon-location",
                    "type": "doctype",
                    "name": "Site Zone",
                    "description": "Manage site zones"
                },
                {
                    "label": "Custom BOQ",
                    "icon": "octicon octicon-list-ordered",
                    "type": "doctype",
                    "name": "Custom BOQ Item",
                    "description": "Bill of Quantities"
                },
                {
                    "label": "RA Bills",
                    "icon": "octicon octicon-credit-card",
                    "type": "doctype",
                    "name": "RA Bill",
                    "description": "Running Account Bills"
                },
                {
                    "label": "Reports",
                    "icon": "octicon octicon-graph",
                    "type": "page",
                    "name": "epc-reports",
                    "description": "EPC Reports and Analytics"
                }
            ]
        }
    ]