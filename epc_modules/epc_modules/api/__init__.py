"""
EPC Module API

REST API endpoints for EPC module operations.
"""

import frappe
from frappe import _


@frappe.whitelist()
def get_epc_version():
    """Return the EPC module version."""
    from epc_modules import __version__
    return {"version": __version__}


# Import all API modules for easy access
from epc_modules.api import project_api
from epc_modules.api import typology_api
from epc_modules.api import boq_api
from epc_modules.api import wbs_api
from epc_modules.api import dpr_api
from epc_modules.api import mb_api
from epc_modules.api import quality_api
from epc_modules.api import concrete_api
from epc_modules.api import billing_api
from epc_modules.api import dashboard_api
from epc_modules.api import construction_api
from epc_modules.api import hse_api
from epc_modules.api import document_api
