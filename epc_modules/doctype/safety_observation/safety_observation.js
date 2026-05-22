frappe.ui.form.on("Safety Observation", {
    refresh(frm) {
        if (frm.doc.severity === "Critical" && frm.doc.status === "Open") {
            frappe.msgprint("Critical observation requires immediate action!");
        }
    }
});