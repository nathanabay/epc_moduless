frappe.ui.form.on("Company Contract Limit", {
    refresh: function(frm) {
        if (frm.doc.__islocal) return;

        frappe.call({
            method: "epc_modules.epc_modules.api.contracts_api.get_approval_authority",
            args: { company: frm.doc.company, contract_type: frm.doc.contract_type },
            callback: function(r) {
                if (r.message) {
                    frm.add_custom_button(__("Check Approval Authority"), function() {
                        frappe.msgprint(__("Current approver: {0}").format(r.message));
                    });
                }
            }
        });
    },

    contract_value: function(frm) {
        if (frm.doc.contract_value && frm.doc.contract_type) {
            frappe.call({
                method: "epc_modules.epc_modules.api.contracts_api.get_approval_route",
                args: {
                    contract_type: frm.doc.contract_type,
                    contract_value: frm.doc.contract_value
                },
                callback: function(r) {
                    if (r.message) {
                        frm.set_value("approval_route", r.message);
                    }
                }
            });
        }
    }
});