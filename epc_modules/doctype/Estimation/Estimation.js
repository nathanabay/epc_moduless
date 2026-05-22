frappe.ui.form.on("Estimation", {
    refresh(frm) {
        if (frm.doc.__islocal) return;

        frm.add_custom_button(__("Print Estimation"), () => {
            frappe.set_route("print", "Estimation", frm.doc.name);
        }, __("Actions"));

        if (frm.doc.status === "Approved" && !frm.doc.converted_to_boq) {
            frm.add_custom_button(__("Convert to BOQ"), () => {
                frappe.call({
                    method: "frappe.client.set_value",
                    args: {
                        doctype: "Estimation",
                        name: frm.doc.name,
                        fieldname: "action",
                        value: "convert"
                    },
                    callback: () => {
                        frappe.msgprint(__("Converted to BOQ"));
                        frm.reload_doc();
                    }
                });
            }, __("Actions"));
        }

        if (frm.doc.status === "Draft") {
            frm.add_custom_button(__("Submit"), () => frm.savesubmit(), __("Actions"));
        }

        if (frm.doc.status === "Submitted") {
            frm.add_custom_button(__("Approve"), () => {
                frm.set_value("status", "Approved");
                frm.save();
            }, __("Actions"));

            frm.add_custom_button(__("Reject"), () => {
                frm.set_value("status", "Rejected");
                frm.save();
            }, __("Actions"));
        }
    },

    markup_percentage(frm) {
        frm.trigger("calculate_totals");
    },

    vat_percentage(frm) {
        frm.trigger("calculate_totals");
    },

    items(frm) {
        frm.fields_dict.items.grid.wrapper.on("blur", ".grid-row", () => {
            frm.trigger("calculate_totals");
        });
    }
});

frappe.ui.form.on("Estimation Item", {
    qty(frm, cdt, cdn) {
        const row = locals[cdt][cdn];
        if (row.qty && row.rate) {
            frappe.model.set_value(cdt, cdn, "amount", row.qty * row.rate);
        }
    },
    rate(frm, cdt, cdn) {
        const row = locals[cdt][cdn];
        if (row.qty && row.rate) {
            frappe.model.set_value(cdt, cdn, "amount", row.qty * row.rate);
        }
    },
    item_code(frm, cdt, cdn) {
        const row = locals[cdt][cdn];
        if (row.item_code) {
            frappe.call({
                method: "frappe.client.get_value",
                args: {
                    doctype: "Item",
                    filters: { name: row.item_code },
                    fieldname: ["item_name", "stock_uom", "standard_rate"]
                },
                callback(r) {
                    if (r.message) {
                        frappe.model.set_value(cdt, cdn, "item_name", r.message.item_name);
                        frappe.model.set_value(cdt, cdn, "uom", r.message.stock_uom);
                        if (r.message.standard_rate && !row.rate) {
                            frappe.model.set_value(cdt, cdn, "rate", r.message.standard_rate);
                        }
                    }
                }
            });
        }
    }
});