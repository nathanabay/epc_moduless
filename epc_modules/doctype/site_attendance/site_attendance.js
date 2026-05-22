frappe.ui.form.on("Site Attendance", {
    refresh(frm) {
        frm.add_custom_button(__("Import from HR"), () => {
            frappe.msgprint("HR integration pending");
        });
    }
});