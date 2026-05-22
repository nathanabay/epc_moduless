frappe.ui.form.on("Work Permit", {
    refresh(frm) {
        if (frm.doc.status === "Draft") {
            frm.add_custom_button(__("Submit for Approval"), () => {
                frm.set_value("status", "Approved");
                frm.save();
            });
        }
        if (frm.doc.status === "Approved") {
            frm.add_custom_button(__("Start Work"), () => {
                frm.set_value("status", "In Progress");
                frm.save();
            });
        }
        if (frm.doc.status === "In Progress") {
            frm.add_custom_button(__("Complete Work"), () => {
                frm.set_value("status", "Completed");
                frm.save();
            });
        }
    }
});