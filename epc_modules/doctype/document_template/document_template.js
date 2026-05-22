frappe.ui.form.on("Document Template", {
    refresh(frm) {
        frm.add_custom_button(__("Preview"), () => {
            if (frm.doc.content) {
                frappe.msgprint(frm.doc.content);
            }
        });
    }
});
