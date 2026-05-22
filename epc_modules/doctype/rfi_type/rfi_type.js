frappe.ui.form.on("RFI Type", {
    refresh(frm) {
        if (!frm.doc.is_active) {
            frm.add_inner_button(__("Reactivate"), () => {
                frm.set_value("is_active", 1);
                frm.save();
            }, __("Actions"));
        }
    },
    validate(frm) {
        if (frm.doc.response_days < 1) {
            frappe.msgprint(__("Response Days must be at least 1"));
            frappe.validated = false;
        }
    }
});
