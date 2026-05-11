__version__ = "1.0.0"

from epc_modules.utils import get_epc_logger

def get_app_info():
    return {
        "app_name": "epc_modules",
        "version": __version__,
        "app_title": "EPC Project Management",
        "app_publisher": "EPC Development Team",
        "app_description": "Comprehensive EPC Module for ERPNext",
        "app_icon": "octicon octicon-project",
        "app_email": "dev@organization.com",
        "app_license": "MIT",
        "app_depends": ["erpnext"],
        "dashboard_version": "1.0.0"
    }


def get_supported_typologies():
    """Return list of supported project typologies."""
    return ["Electromechanical", "Civil", "Standard/Service"]


def get_billing_tracks():
    """Return supported billing tracks."""
    return {
        "RA-Billing": {
            "name": "RA Billing",
            "description": "Running Account billing per PPA 2011",
            "requires_measurement_book": True
        },
        "Milestone-Billing": {
            "name": "Milestone Billing",
            "description": "Milestone-based billing for services",
            "requires_measurement_book": False
        }
    }