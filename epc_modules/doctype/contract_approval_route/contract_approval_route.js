frappe.ui.form.on("Contract Approval Route", {
    refresh: function(frm) {
        if (frm.doc.is_active) {
            frm.add_custom_button(__("Create Contract"), function() {
                frappe.set_route("Form", "Company Contract Limit", "new-company-contract-limit-" + frappe.session.user);
            });
        }
    }
});