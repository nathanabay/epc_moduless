frappe.ui.form.on("Waste Record", {
    refresh(frm) {
        if (frm.doc.__islocal) return;

        if (frm.doc.is_hazardous) {
            frm.add_css_class("[data-fieldname='manifest_attachment']", "error");
        }

        if (frm.doc.status === "Draft") {
            frm.add_custom_button(__("Submit Record"), () => frm.savesubmit(), __("Actions"));
        }

        if (frm.doc.status === "Generated") {
            frm.add_custom_button(__("Mark Segregated"), () => {
                frm.set_value("status", "Segregated");
                frm.save();
            }, __("Actions"));
        }

        if (frm.doc.status === "Segregated") {
            frm.add_custom_button(__("Transport"), () => {
                frm.set_value("status", "Transported");
                frm.set_value("transport_date", frappe.datetime.now_date());
                frm.save();
            }, __("Actions"));
        }

        if (frm.doc.status === "Transported") {
            frm.add_custom_button(__("Mark Disposed"), () => {
                frm.set_value("status", "Disposed");
                frm.save();
            }, __("Actions"));

            frm.add_custom_button(__("Mark Recycled"), () => {
                frm.set_value("status", "Recycled");
                frm.save();
            }, __("Actions"));
        }
    },

    waste_type(frm) {
        if (frm.doc.waste_type === "Hazardous") {
            frm.set_value("is_hazardous", 1);
            frappe.msgprint(__("This waste is marked as Hazardous. Ensure proper documentation is attached."));
        } else {
            frm.set_value("is_hazardous", 0);
        }
    }
});