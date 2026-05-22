frappe.ui.form.on("Change Order", {
    refresh(frm) {
        if (frm.doc.__islocal) return;

        frm.add_custom_button(__("Print Change Order"), () => {
            frappe.set_route("print", "Change Order", frm.doc.name);
        }, __("Actions"));

        if (frm.doc.status === "Draft") {
            frm.add_custom_button(__("Submit"), () => frm.savesubmit(), __("Actions"));
        }

        if (frm.doc.status === "Submitted") {
            frm.add_custom_button(__("Approve"), () => {
                frm.set_value("is_approved", 1);
                frm.set_value("status", "Approved");
                frm.set_value("approved_by", frappe.session.user);
                frm.set_value("approval_date", frappe.datetime.now_date());
                frm.save();
            }, __("Actions"));

            frm.add_custom_button(__("Reject"), () => {
                frm.set_value("status", "Rejected");
                frm.save();
            }, __("Actions"));
        }

        if (frm.doc.status === "Approved" && !frm.doc.is_approved) {
            frm.add_custom_button(__("Mark Approved"), () => {
                frm.set_value("is_approved", 1);
                frm.set_value("status", "Approved");
                frm.set_value("approved_by", frappe.session.user);
                frm.set_value("approval_date", frappe.datetime.now_date());
                frm.save();
            }, __("Actions"));
        }

        if (frm.doc.cost_impact && (frm.doc.status === "Approved" || frm.doc.is_approved)) {
            frm.add_custom_button(__("Incorporate in BOQ"), () => {
                frappe.msgprint(__("Incorporate cost impact of {0} into BOQ").replace("{0}", frm.doc.cost_impact));
                frm.set_value("status", "Incorporated");
                frm.save();
            }, __("Actions"));
        }
    }
});