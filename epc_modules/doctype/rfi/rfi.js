frappe.ui.form.on("RFI", {
    refresh(frm) {
        if (frm.doc.__islocal) return;

        frm.add_custom_button(__("Print RFI"), () => {
            frappe.route_options = { "rfi": frm.docname };
            frappe.set_route("print", "RFI", frm.docname);
        });

        if (frm.doc.status === "Draft") {
            frm.add_custom_button(__("Submit"), () => {
                frm.savesubmit();
            }, __("Actions"));
        }

        if (frm.doc.status === "Open" && frm.doc.response) {
            frm.add_custom_button(__("Close"), () => {
                frm.set_value("status", "Closed");
                frm.save();
            }, __("Actions"));
        }

        if (frm.doc.status === "Pending Review") {
            frm.add_custom_button(__("Close RFI"), () => {
                frm.set_value("status", "Closed");
                frm.save();
            }, __("Actions"));
        }

        if (frm.doc.due_date) {
            const today = frappe.datetime.now_date();
            if (frm.doc.due_date < today && !["Closed", "Rejected"].includes(frm.doc.status)) {
                frm.add_css_class("duedate-alert");
            }
        }
    },

    project(frm) {
        if (frm.doc.project) {
            frappe.call({
                method: "epc_modules.api.site_operations_api.get_project_rfi_count",
                args: { project: frm.doc.project },
                callback(r) {
                    if (r.message !== undefined) {
                        frm.set_value("rfi_number", `RFI-${frm.doc.project.substring(0, 4).toUpperCase()}-${(r.message + 1).toString().padStart(4, "0")}`);
                    }
                }
            });
        }
    },

    rfi_type(frm) {
        if (frm.doc.rfi_type && !frm.doc.due_date) {
            frappe.call({
                method: "frappe.client.get_value",
                args: {
                    doctype: "RFI Type",
                    filters: { name: frm.doc.rfi_type },
                    fieldname: ["response_days", "default_priority"]
                },
                callback(r) {
                    if (r.message) {
                        if (r.message.default_priority) {
                            frm.set_value("priority", r.message.default_priority);
                        }
                    }
                }
            });
        }
    },

    raised_date(frm) {
        if (frm.doc.raised_date && frm.doc.rfi_type) {
            frappe.call({
                method: "frappe.client.get_value",
                args: {
                    doctype: "RFI Type",
                    filters: { name: frm.doc.rfi_type },
                    fieldname: "response_days"
                },
                callback(r) {
                    if (r.message && r.message.response_days) {
                        const due = frappe.datetime.add_days(frm.doc.raised_date, r.message.response_days);
                        frm.set_value("due_date", due);
                    }
                }
            });
        }
    }
});
