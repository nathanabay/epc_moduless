frappe.ui.form.on("PPE Type", {
    refresh(frm) {
        frm.add_custom_button(__("Check Compliance"), () => {
            frappe.msgprint(__("Compliance check for {0}", [frm.doc.ppe_type_name]));
        });
    }
});