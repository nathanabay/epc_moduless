frappe.ui.form.on("Work Package", {
    refresh(frm) {
        if (frm.doc.__islocal) return;

        if (frm.doc.status === "Draft") {
            frm.add_custom_button(__("Start Package"), () => {
                frm.set_value("status", "In Progress");
                frm.set_value("actual_start", frappe.datetime.now_date());
                frm.save();
            }, __("Actions"));
        }

        if (frm.doc.status === "In Progress") {
            frm.add_custom_button(__("Complete Package"), () => {
                frm.set_value("status", "Completed");
                frm.set_value("actual_end", frappe.datetime.now_date());
                frm.save();
            }, __("Actions"));

            frm.add_custom_button(__("Put On Hold"), () => {
                frm.set_value("status", "On Hold");
                frm.save();
            }, __("Actions"));
        }

        if (frm.doc.status === "Planned") {
            frm.add_custom_button(__("Begin Work"), () => {
                frm.set_value("status", "In Progress");
                frm.set_value("actual_start", frappe.datetime.now_date());
                frm.save();
            }, __("Actions"));
        }
    },

    project(frm) {
        if (frm.doc.project) {
            frappe.call({
                method: "epc_modules.api.wbs_api.get_project_wbs_items",
                args: { project: frm.doc.project },
                callback(r) {
                    if (r.message) {
                        frm.fields_dict.wbs_item.get_query = () => ({
                            filters: { "project": frm.doc.project }
                        });
                    }
                }
            });
        }
    }
});

frappe.ui.form.on("Work Package Task", {
    task_name(frm, cdt, cdn) {
        const row = locals[cdt][cdn];
        if (row.task_name && !row.task_id) {
            const today = frappe.datetime.now_date().replace(/-/g, "");
            frappe.model.set_value(cdt, cdn, "task_id", `T-${today}-${cdn.replace(/[^0-9]/g, "").substring(0, 4)}`);
        }
    }
});