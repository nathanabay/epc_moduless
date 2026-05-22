frappe.ui.form.on("Machine Repair", {
    refresh: function(frm) {
        if (frm.doc.status === "Completed" && !frm.doc.verified_by) {
            frm.add_custom_button(__("Verify Repair"), function() {
                frappe.call({
                    method: "epc_modules.epc_modules.doctype.machine_repair.machine_repair.verify_repair",
                    args: { docname: frm.doc.name },
                    callback: function(r) {
                        if (!r.exc) {
                            frappe.msgprint(__("Repair verified successfully"));
                            frm.reload_doc();
                        }
                    }
                });
            });
        }

        if (frm.doc.repair_cost > 0) {
            frm.add_custom_button(__("Log to Equipment"), function() {
                frappe.call({
                    method: "epc_modules.epc_modules.api.contracts_api.log_repair_to_equipment",
                    args: { machine_repair: frm.doc.name },
                    callback: function(r) {
                        if (!r.exc) {
                            frappe.msgprint(__("Repair logged to equipment maintenance"));
                        }
                    }
                });
            });
        }
    }
});