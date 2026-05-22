frappe.ui.form.on("Transmittal", {
    refresh(frm) {
        if (frm.doc.__islocal) return;

        frm.add_custom_button(__("Print Transmittal"), () => {
            frappe.set_route("print", "Transmittal", frm.doc.name);
        }, __("Actions"));

        if (frm.doc.status === "Draft") {
            frm.add_custom_button(__("Issue"), () => {
                frm.set_value("status", "Issued");
                frm.savesubmit();
            }, __("Actions"));
        }

        if (frm.doc.status === "Issued") {
            frm.add_custom_button(__("Mark Received"), () => {
                frm.set_value("received_date", frappe.datetime.now_date());
                frm.set_value("status", "Received");
                frm.save();
            }, __("Actions"));
        }
    }
});

frappe.ui.form.on("Transmittal Item", {
    document_number(frm, cdt, cdn) {
        const row = locals[cdt][cdn];
        if (row.document_number && !row.document_title) {
            frappe.call({
                method: "frappe.client.get_value",
                args: { doctype: "File", filters: { name: row.document_number }, fieldname: "file_name" },
                callback(r) {
                    if (r.message && r.message.file_name) {
                        frappe.model.set_value(cdt, cdn, "document_title", r.message.file_name);
                    }
                }
            });
        }
    }
});