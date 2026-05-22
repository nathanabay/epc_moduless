frappe.ui.form.on("Shop Drawing", {
    refresh(frm) {
        if (frm.doc.__islocal) return;

        frm.add_custom_button(__("Print Drawing Register"), () => {
            frappe.set_route("print", "Shop Drawing", frm.doc.name);
        }, __("Actions"));

        if (frm.doc.status === "Draft" || frm.doc.status === "Submitted") {
            frm.add_custom_button(__("Submit for Review"), () => {
                frm.set_value("status", "Under Review");
                frm.set_value("submitted_by", frappe.session.user);
                frm.set_value("submission_date", frappe.datetime.now_date());
                frm.save();
            }, __("Actions"));
        }

        if (frm.doc.status === "Under Review" && frappe.user.has_role("Project Manager")) {
            frm.add_custom_button(__("Approve"), () => {
                frm.set_value("status", "Approved");
                frm.set_value("reviewed_by", frappe.session.user);
                frm.set_value("review_date", frappe.datetime.now_date());
                frm.save();
            }, __("Actions"));

            frm.add_custom_button(__("Approve with Comments"), () => {
                frappe.prompt([{
                    fieldname: "comments",
                    fieldtype: "Small Text",
                    label: "Review Comments"
                }], (values) => {
                    frm.set_value("status", "Approved with Comments");
                    frm.set_value("review_comments", values.comments);
                    frm.set_value("reviewed_by", frappe.session.user);
                    frm.set_value("review_date", frappe.datetime.now_date());
                    frm.save();
                }, __("Enter Review Comments"), __("Submit"));
            }, __("Actions"));

            frm.add_custom_button(__("Reject"), () => {
                frappe.prompt([{
                    fieldname: "comments",
                    fieldtype: "Small Text",
                    label: "Rejection Reason"
                }], (values) => {
                    frm.set_value("status", "Rejected");
                    frm.set_value("review_comments", values.comments);
                    frm.set_value("reviewed_by", frappe.session.user);
                    frm.set_value("review_date", frappe.datetime.now_date());
                    frm.save();
                }, __("Enter Rejection Reason"), __("Reject"));
            }, __("Actions"));
        }
    }
});