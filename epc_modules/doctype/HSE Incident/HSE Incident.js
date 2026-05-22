frappe.ui.form.on("HSE Incident", {
    refresh(frm) {
        if (frm.doc.severity === "Fatal" || frm.doc.severity === "Major") {
            frappe.msgprint(__("This is a " + frm.doc.severity + " incident. Immediate action required!"), "Alert");
        }
        if (frm.doc.status === "Reported") {
            frm.add_custom_button(__("Start Investigation"), () => {
                frm.set_value("status", "Investigating");
                frm.save();
            });
        }
        if (frm.doc.status === "Investigating") {
            frm.add_custom_button(__("Mark Action Taken"), () => {
                frm.set_value("status", "Action Taken");
                frm.save();
            });
        }
        if (frm.doc.status === "Action Taken") {
            frm.add_custom_button(__("Close Incident"), () => {
                frm.set_value("status", "Closed");
                frm.set_value("closure_date", frappe.datetime.now_date());
                frm.save();
            });
        }
    }
});