frappe.ui.form.on("Safety Inspection", {
    refresh(frm) {
        if (frm.doc.status === "Draft") {
            frm.add_custom_button(__("Submit"), () => {
                frm.set_value("status", "Submitted");
                frm.save();
            });
        }
        frm.add_custom_button(__("Print Checklist"), () => {
            frappe.msgprint("Print checklist functionality");
        });
    },
    checklist_items(frm) {
        frm.fields_dict.checklist_items.grid.wrapper.find('.grid-add-row').on('click', () => {
            setTimeout(() => frm.trigger('calculate_compliance'), 500);
        });
    }
});