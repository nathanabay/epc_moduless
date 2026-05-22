import frappe
from frappe import _


@frappe.whitelist()
def create_ipc(project, milestone_name, lines_data):
    """
    Create an Interim Payment Certificate for a project milestone.

    Args:
        project: Project name
        milestone_name: Name of the milestone
        lines_data: List of dicts with keys: description, wbs_item, planned_value, this_period_certified

    Returns:
        IPC document name
    """
    frappe.has_permission("Project", "write", docname=project, throw=True)
    frappe.has_permission("Interim Payment Certificate", "create", throw=True)

    # Validate required fields
    if not project:
        frappe.throw(_("Project is required"))
    if not milestone_name:
        frappe.throw(_("Milestone name is required"))
    if not lines_data:
        frappe.throw(_("Lines data is required"))

    ipc = frappe.get_doc({
        "doctype": "Interim Payment Certificate",
        "project": project,
        "milestone_name": milestone_name,
        "certification_date": frappe.utils.today(),
        "status": "Draft"
    })

    if isinstance(lines_data, str):
        lines_data = frappe.parse_json(lines_data)

    for line in lines_data:
        ipc.append("lines", {
            "description": line.get("description"),
            "wbs_item": line.get("wbs_item"),
            "planned_value": line.get("planned_value", 0),
            "this_period_certified": line.get("this_period_certified", 0)
        })

    try:
        ipc.insert()
        return {"name": ipc.name}
    except frappe.ValidationError:
        frappe.log_error(frappe.get_traceback(), "Contracts API Error")
        frappe.throw(_("Failed to create IPC record"))


@frappe.whitelist()
def create_machine_repair(machine, project, repair_type, description=None):
    """
    Create a Machine Repair record for equipment maintenance.

    Args:
        machine: Equipment name
        project: Project name (optional)
        repair_type: Type of repair (Preventive/Corrective/Emergency/Overhaul)
        description: Repair description

    Returns:
        Machine Repair document name
    """
    frappe.has_permission("Machine Repair", "create", throw=True)
    if project:
        frappe.has_permission("Project", "read", docname=project, throw=True)

    # Validate required fields
    if not machine:
        frappe.throw(_("Machine is required"))
    if not repair_type:
        frappe.throw(_("Repair type is required"))

    repair = frappe.get_doc({
        "doctype": "Machine Repair",
        "machine": machine,
        "project": project,
        "repair_type": repair_type,
        "description": description,
        "repair_date": frappe.utils.today(),
        "status": "Open"
    })

    try:
        repair.insert()
        return {"name": repair.name}
    except frappe.ValidationError:
        frappe.log_error(frappe.get_traceback(), "Contracts API Error")
        frappe.throw(_("Failed to create Machine Repair record"))


@frappe.whitelist()
def get_approval_route(contract_type, contract_value):
    """
    Get the applicable approval route for a contract.

    Args:
        contract_type: Type of contract (Supply/Service/Works/AMC/Consultancy)
        contract_value: Total contract value

    Returns:
        Contract Approval Route name or None
    """
    frappe.has_permission("Contract Approval Route", "read", throw=True)

    routes = frappe.get_all(
        "Contract Approval Route",
        filters={
            "contract_type": contract_type,
            "is_active": 1
        },
        fields=["name", "min_value", "max_value"],
        order_by="max_value asc"
    )

    for route in routes:
        if not route.max_value or contract_value <= route.max_value:
            if not route.min_value or contract_value >= route.min_value:
                return route.name

    return None


@frappe.whitelist()
def get_approval_authority(company, contract_type):
    """
    Get the current approval authority for a company contract.

    Args:
        company: Company name
        contract_type: Type of contract

    Returns:
        List of pending approvers with their levels
    """
    frappe.has_permission("Company Contract Limit", "read", throw=True)

    contract = frappe.get_all(
        "Company Contract Limit",
        filters={
            "company": company,
            "contract_type": contract_type,
            "current_status": ["in", ["Pending Approval", "Active"]]
        },
        order_by="contract_value desc"
    )

    if not contract:
        return None

    contract_doc = frappe.get_doc("Company Contract Limit", contract[0].name)
    pending = contract_doc.get_pending_approvers()

    return [{
        "level": p.approval_level,
        "role": p.approver_role,
        "user": p.approver,
        "limit": p.approval_limit
    } for p in pending]


@frappe.whitelist()
def check_contract_approval_authority(user, contract_type, amount):
    """
    Check if a user can approve a contract at the given amount.

    Args:
        user: User ID
        contract_type: Type of contract
        amount: Contract amount

    Returns:
        Dict with can_approve, level, limit
    """
    frappe.has_permission("Company Contract Limit", "read", throw=True)

    routes = frappe.get_all(
        "Contract Approval Route",
        filters={
            "contract_type": contract_type,
            "is_active": 1
        },
        fields=["name"],
        order_by="max_value asc"
    )

    route_names = [r.name for r in routes]
    if not route_names:
        return {"can_approve": False, "level": None, "limit": None}

    levels = frappe.get_all(
        "Contract Approval Route Level",
        filters=[["parent", "in", route_names]],
        fields=["parent", "approval_level", "approval_limit", "approver", "approver_role"]
    )

    for route in routes:
        for level in levels:
            if level.parent != route.name:
                continue
            if level.approval_limit and amount <= level.approval_limit:
                if level.approver == user or level.approver_role in frappe.get_roles(user):
                    return {
                        "can_approve": True,
                        "level": level.approval_level,
                        "limit": level.approval_limit
                    }

    return {
        "can_approve": False,
        "level": None,
        "limit": None
    }


@frappe.whitelist()
def log_repair_to_equipment(machine_repair):
    """
    Log a machine repair to the equipment maintenance history.

    Args:
        machine_repair: Machine Repair document name

    Returns:
        Success message
    """
    frappe.has_permission("Machine Repair", "read", throw=True)
    repair_doc = frappe.get_doc("Machine Repair", machine_repair)

    if repair_doc.machine:
        frappe.msgprint(f"Repair logged for equipment: {repair_doc.machine}")
        return "Repair logged successfully"

    return "No equipment linked"


@frappe.whitelist()
def get_ipc_summary(project):
    """
    Get IPC summary for a project including certified amounts.

    Args:
        project: Project name

    Returns:
        Dict with cumulative values per wbs_item
    """
    frappe.has_permission("Interim Payment Certificate", "read", throw=True)
    if project:
        frappe.has_permission("Project", "read", docname=project, throw=True)

    ipcs = frappe.get_list(
        "Interim Payment Certificate",
        filters={"project": project},
        fields=["name", "status", "certification_date"]
    )

    if not ipcs:
        return []

    ipc_names = [ipc.name for ipc in ipcs]
    lines = frappe.get_all(
        "IPC Line",
        filters={"parent": ["in", ipc_names]},
        fields=["parent", "wbs_item", "description", "this_period_certified", "cumulative_certified"]
    )

    lines_by_ipc = {}
    for line in lines:
        if line.parent not in lines_by_ipc:
            lines_by_ipc[line.parent] = []
        lines_by_ipc[line.parent].append(line)

    summary = []
    for ipc in ipcs:
        for line in lines_by_ipc.get(ipc.name, []):
            summary.append({
                "ipc": ipc.name,
                "date": ipc.certification_date,
                "status": ipc.status,
                "wbs_item": line.wbs_item,
                "description": line.description,
                "this_period": line.this_period_certified,
                "cumulative": line.cumulative_certified
            })

    return summary


@frappe.whitelist()
def submit_ipc(ipc_name):
    """
    Submit an IPC and update related records.

    Args:
        ipc_name: Interim Payment Certificate name

    Returns:
        Success message
    """
    frappe.has_permission("Interim Payment Certificate", "submit", throw=True)
    ipc_doc = frappe.get_doc("Interim Payment Certificate", ipc_name)
    frappe.has_permission("Interim Payment Certificate", "write", doc=ipc_doc, throw=True)

    if ipc_doc.docstatus == 0:
        try:
            ipc_doc.submit()
            return f"IPC {ipc_name} submitted successfully"
        except frappe.ValidationError:
            frappe.log_error(frappe.get_traceback(), "Contracts API Error")
            frappe.throw(_("Failed to submit IPC"))

    return f"IPC {ipc_name} is already submitted"


@frappe.whitelist()
def approve_contract(contract_name, comments=None):
    """
    Approve a company contract at the current level.

    Args:
        contract_name: Company Contract Limit name
        comments: Approval comments

    Returns:
        Updated contract status
    """
    frappe.has_permission("Company Contract Limit", "write", throw=True)
    contract = frappe.get_doc("Company Contract Limit", contract_name)
    route = contract.get_approval_route()

    if not route:
        frappe.throw(_("No approval route found for this contract"))

    approved_levels = [h.approval_level for h in (contract.approval_history or [])]
    current_level = None

    for level in route.approval_levels:
        if level.approval_level not in approved_levels:
            current_level = level
            break

    if not current_level:
        frappe.throw(_("Contract is already fully approved"))

    if current_level.approver and current_level.approver != frappe.session.user:
        frappe.throw(_("You are not authorized to approve at this level"))

    contract.append("approval_history", {
        "approval_level": current_level.approval_level,
        "approver": frappe.session.user,
        "approval_date": frappe.utils.now(),
        "status": "Approved",
        "comments": comments
    })

    if contract.is_fully_approved():
        contract.current_status = "Active"
    else:
        contract.current_status = "Pending Approval"

    try:
        contract.save()
        return {
            "status": "success",
            "level": current_level.approval_level,
            "overall_status": contract.current_status
        }
    except frappe.ValidationError:
        frappe.log_error(frappe.get_traceback(), "Contracts API Error")
        frappe.throw(_("Failed to save contract approval"))