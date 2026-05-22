frappe.ui.form.on("Visitor Log", {
    refresh(frm) {
        if (frm.doc.status === "In Site") {
            frm.add_custom_button(__("Mark Exit"), () => {
                frm.set_value("status", "Exited");
                frm.set_value("exit_date", frappe.datetime.now_datetime());
                frm.save();
            });
        }
    }
});