frappe.ui.form.on("Budget", {
    refresh(frm) {
        if (frm.doc.__islocal) return;

        frm.add_custom_button(__("Sync Actual Costs"), () => {
            frappe.call({
                method: "frappe.client.set_value",
                args: {
                    doctype: "Budget",
                    name: frm.doc.name,
                    fieldname: "action",
                    value: "sync"
                },
                callback: () => {
                    frappe.msgprint(__("Actual costs synced"));
                    frm.reload_doc();
                }
            });
        }, __("Actions"));

        frm.add_custom_button(__("Print Budget"), () => {
            frappe.set_route("print", "Budget", frm.doc.name);
        }, __("Actions"));

        if (frm.doc.status === "Draft") {
            frm.add_custom_button(__("Submit"), () => frm.savesubmit(), __("Actions"));
        }
    },

    lines(frm) {
        frm.trigger("calculate_totals");
    }
});

frappe.ui.form.on("Budget Line", {
    planned_amount(frm, cdt, cdn) {
        const row = locals[cdt][cdn];
        const actual = row.actual_amount || 0;
        frappe.model.set_value(cdt, cdn, "variance", (row.planned_amount || 0) - actual);
        frm.trigger("calculate_totals");
    },
    actual_amount(frm, cdt, cdn) {
        const row = locals[cdt][cdn];
        frappe.model.set_value(cdt, cdn, "variance", (row.planned_amount || 0) - (row.actual_amount || 0));
        frm.trigger("calculate_totals");
    }
});