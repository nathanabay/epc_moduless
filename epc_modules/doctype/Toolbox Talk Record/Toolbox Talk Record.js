frappe.ui.form.on("Toolbox Talk Record", {
    refresh(frm) {
        if (frm.doc.status === "Planned") {
            frm.add_custom_button(__("Mark Conducted"), () => {
                frm.set_value("status", "Conducted");
                frm.set_value("talk_presenter", frappe.session.user);
                frm.save();
            });
            frm.add_custom_button(__("Cancel"), () => {
                frm.set_value("status", "Cancelled");
                frm.save();
            });
        }
        frm.add_custom_button(__("Print Attendance"), () => {
            frappe.msgprint("Print attendance sheet");
        });
    }
});