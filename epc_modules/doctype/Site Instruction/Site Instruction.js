frappe.ui.form.on("Site Instruction", {
    refresh(frm) {
        if (frm.doc.__islocal) return;

        if (frm.doc.status === "Draft") {
            frm.add_custom_button(__("Issue Instruction"), () => {
                frm.set_value("status", "Issued");
                frm.savesubmit();
            }, __("Actions"));
        }

        if (frm.doc.status === "Issued") {
            frm.add_custom_button(__("Acknowledge"), () => {
                frm.set_value("status", "Acknowledged");
                frm.set_value("acknowledged_by", frappe.session.user);
                frm.set_value("acknowledged_date", frappe.datetime.now_date());
                frm.save();
            }, __("Actions"));
        }

        if (frm.doc.status === "Acknowledged") {
            frm.add_custom_button(__("Mark In Progress"), () => {
                frm.set_value("status", "In Progress");
                frm.save();
            }, __("Actions"));
        }

        if (frm.doc.status === "In Progress") {
            frm.add_custom_button(__("Complete"), () => {
                frm.set_value("status", "Completed");
                frm.set_value("completed_by", frappe.session.user);
                frm.set_value("completion_date", frappe.datetime.now_date());
                frm.save();
            }, __("Actions"));
        }

        if (frm.doc.cost_impact) {
            frm.add_custom_button(__("Create Variation Order"), () => {
                frappe.msgprint(__("Variation Order creation would be triggered here"));
            }, __("Actions"));
        }
    },

    work_package(frm) {
        if (frm.doc.work_package) {
            frappe.call({
                method: "frappe.client.get",
                args: { doctype: "Work Package", name: frm.doc.work_package },
                callback(r) {
                    if (r.message && !frm.doc.project) {
                        frm.set_value("project", r.message.project);
                    }
                }
            });
        }
    }
});