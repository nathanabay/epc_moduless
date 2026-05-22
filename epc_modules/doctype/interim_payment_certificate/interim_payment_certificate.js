frappe.ui.form.on("Interim Payment Certificate", {
    refresh: function(frm) {
        if (frm.doc.status === "Draft" && frm.doc.lines && frm.doc.lines.length) {
            frm.add_custom_button(__("Calculate Totals"), function() {
                frm.call({
                    method: "calculate_totals",
                    doc: frm.doc,
                    callback: function(r) {
                        if (!r.exc) {
                            frm.refresh_fields();
                        }
                    }
                });
            });
        }

        if (frm.doc.status === "Draft") {
            frm.add_custom_button(__("Submit IPC"), function() {
                frm.call("submit_ipc", { ipc_name: frm.doc.name });
            });
        }
    },

    retention_percentage: function(frm) {
        frm.trigger("calculate_totals");
    },

    vat_rate: function(frm) {
        frm.trigger("calculate_totals");
    }
});

frappe.ui.form.on("IPC Line", {
    this_period_certified: function(frm, cdt, cdn) {
        var row = locals[cdt][cdn];
        frappe.model.set_value(cdt, cdn, "cumulative_certified",
            (row.previous_certified || 0) + (row.this_period_certified || 0));
        frm.trigger("calculate_totals");
    }
});