frappe.ui.form.on("Item Request", {
    refresh(frm) {
        if (frm.doc.__islocal) return;

        frm.add_custom_button(__("Create Purchase Order"), () => {
            frappe.call({
                method: "epc_modules.api.site_operations_api.create_po_from_item_request",
                args: { item_request: frm.doc.name },
                callback(r) {
                    if (r.message) {
                        frappe.msgprint(__("Purchase Order {0} created").replace("{0}", r.message.name));
                        frappe.set_route("Form", "Purchase Order", r.message.name);
                    }
                }
            });
        }, __("Actions"));

        if (frm.doc.status === "Draft") {
            frm.add_custom_button(__("Submit"), () => frm.savesubmit(), __("Actions"));
        }

        if (frm.doc.status === "Pending" && frappe.user.has_role("Project Manager")) {
            frm.add_custom_button(__("Approve"), () => {
                frm.set_value("status", "Approved");
                frm.set_value("approved_by", frappe.session.user);
                frm.set_value("approved_date", frappe.datetime.now_date());
                frm.save();
            }, __("Actions"));
        }
    },

    request_type(frm) {
        if (frm.doc.request_type) {
            frm.fields_dict.items.grid.get_field("item_code").get_query = () => ({
                filters: { "item_group": frm.doc.request_type }
            });
        }
    }
});

frappe.ui.form.on("Item Request Item", {
    item_code(frm, cdt, cdn) {
        const row = locals[cdt][cdn];
        if (row.item_code) {
            frappe.call({
                method: "frappe.client.get_value",
                args: { doctype: "Item", filters: { name: row.item_code }, fieldname: ["item_name", "stock_uom"] },
                callback(r) {
                    if (r.message) {
                        frappe.model.set_value(cdt, cdn, "item_name", r.message.item_name);
                        frappe.model.set_value(cdt, cdn, "uom", r.message.stock_uom);
                    }
                }
            });
        }
    }
});