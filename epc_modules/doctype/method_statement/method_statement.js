frappe.ui.form.on("Method Statement", {
    refresh(frm) {
        if (frm.doc.status === "Under Review") {
            frm.add_custom_button(__("Approve"), () => {
                frm.set_value("status", "Approved");
                frm.set_value("approved_by", frappe.session.user);
                frm.save();
            });
        }
    }
});