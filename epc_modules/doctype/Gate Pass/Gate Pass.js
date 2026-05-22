frappe.ui.form.on("Gate Pass", {
    refresh(frm) {
        if (frm.doc.__islocal) return;

        frm.add_custom_button(__("Print Gate Pass"), () => {
            frappe.route_options = { "gate_pass": frm.doc.name };
            frappe.set_route("print", "Gate Pass", frm.doc.name);
        }, __("Actions"));

        if (frm.doc.status === "Draft") {
            frm.add_custom_button(__("Submit"), () => frm.savesubmit(), __("Actions"));
        }

        if (frm.doc.status === "Approved" && frm.doc.gate_pass_type === "Outward") {
            frm.add_custom_button(__("Gate Out"), () => {
                frm.set_value("gate_out_date", frappe.datetime.now_datetime());
                frm.set_value("status", "In Transit");
                frm.save();
            }, __("Actions"));
        }

        if (frm.doc.status === "In Transit" && frm.doc.gate_pass_type === "Outward") {
            frm.add_custom_button(__("Gate In"), () => {
                frm.set_value("gate_in_date", frappe.datetime.now_datetime());
                frm.set_value("status", "Received");
                frm.save();
            }, __("Actions"));
        }

        if (frm.doc.status === "Received" || frm.doc.status === "Approved") {
            frm.add_custom_button(__("Close"), () => {
                frm.set_value("status", "Closed");
                frm.save();
            }, __("Actions"));
        }
    },

    gate_pass_type(frm) {
        if (frm.doc.gate_pass_type === "Inward") {
            frm.set_df_property("vehicle_number", "reqd", 0);
            frm.set_df_property("expected_return_date", "reqd", 0);
        } else if (frm.doc.gate_pass_type === "Outward") {
            frm.set_df_property("vehicle_number", "reqd", 1);
            frm.set_df_property("expected_return_date", "reqd", 1);
        }
    },

    project(frm) {
        if (frm.doc.project) {
            frappe.call({
                method: "frappe.client.get",
                args: { doctype: "Project", name: frm.doc.project },
                callback(r) {
                    if (r.message && r.message.workspace) {
                        frm.set_query("warehouse", () => ({
                            filters: { "project": frm.doc.project }
                        }));
                    }
                }
            });
        }
    }
});