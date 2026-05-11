/**
 * EPC Typology Handlers

Client-side form handlers for project typology functionality.
 */

frappe.ui.form.on('Project', {
    refresh: function(frm) {
        // Apply initial state based on EPC project flag
        if (frm.doc.is_epc_project) {
            frm.add_custom_button(__('View Dashboard'), function() {
                frappe.EPC.getDashboard(frm.doc.name, function(data) {
                    var dialog = new frappe.Dialog({
                        title: __('Project Dashboard'),
                        fields: [
                            {
                                fieldtype: "HTML",
                                fieldname: "dashboard_html",
                                options: frappe.EPC.utils.formatDashboard(data)
                            }
                        ],
                        primary_action: function() {
                            dialog.hide();
                        },
                        primary_action_label: __('Close')
                    });
                    dialog.show();
                });
            });
        }
    },

    is_epc_project: function(frm) {
        // Toggle EPC-specific fields visibility
        frm.toggle_display("project_typology", frm.doc.is_epc_project);
        frm.toggle_display("regulatory_context", frm.doc.is_epc_project);
        frm.toggle_display("vat_registration", frm.doc.is_epc_project);
        frm.toggle_display("billing_track", frm.doc.is_epc_project);
        frm.toggle_display("contract_value", frm.doc.is_epc_project);
        frm.toggle_display("retention_percentage", frm.doc.is_epc_project);
        frm.toggle_display("advance_recovery_threshold", frm.doc.is_epc_project);

        // Clear typology if switching off EPC
        if (!frm.doc.is_epc_project && frm.doc.project_typology) {
            frm.set_value("project_typology", null);
        }
    },

    project_typology: function(frm) {
        if (!frm.doc.project_typology) return;

        // Load and apply typology configuration
        frappe.call({
            method: "frappe.client.get",
            args: {
                doctype: "Project Typology",
                name: frm.doc.project_typology
            },
            callback: function(r) {
                if (r.message) {
                    var typology = r.message;
                    frappe.EPC.applyTypologyUI(frm, typology);

                    // Set billing track
                    if (typology.billing_track) {
                        frm.set_value("billing_track", typology.billing_track);
                    }

                    // Set retention percentage
                    if (typology.default_retention_percentage) {
                        frm.set_value("retention_percentage",
                            typology.default_retention_percentage);
                    }
                }
            }
        });
    },

    before_save: function(frm) {
        // Validate EPC project
        if (frm.doc.is_epc_project) {
            if (!frm.doc.project_typology) {
                frappe.msgprint({
                    title: __("Validation Error"),
                    message: __("Please select a Project Typology for EPC projects"),
                    indicator: "red"
                });
                frappe.validated = false;
            }
        }
    }
});

// Item DocType handlers
frappe.ui.form.on('Item', {
    is_epc_material: function(frm) {
        frm.toggle_display("is_equipment", frm.doc.is_epc_material);
        if (!frm.doc.is_epc_material) {
            frm.set_value("is_equipment", 0);
            frm.set_value("equipment_tag", null);
        }
    },

    is_equipment: function(frm) {
        frm.toggle_display("equipment_tag", frm.doc.is_equipment);
        if (!frm.doc.is_equipment) {
            frm.set_value("equipment_tag", null);
        }
    }
});

// Dashboard formatting utility
frappe.EPC.utils.formatDashboard = function(data) {
    if (!data) return "<p>No data available</p>";

    var html = '<div class="row">';

    // Status card
    html += '<div class="col-md-3">';
    html += '<div class="card">';
    html += '<div class="card-body">';
    html += '<h5 class="card-title">' + __("Status") + '</h5>';
    html += '<h2>' + (data.status || "-") + '</h2>';
    html += '</div></div></div>';

    // Typology card
    html += '<div class="col-md-3">';
    html += '<div class="card">';
    html += '<div class="card-body">';
    html += '<h5 class="card-title">' + __("Typology") + '</h5>';
    html += '<h2>' + (data.typology_type || "-") + '</h2>';
    html += '</div></div></div>';

    // Progress card
    html += '<div class="col-md-3">';
    html += '<div class="card">';
    html += '<div class="card-body">';
    html += '<h5 class="card-title">' + __("Progress") + '</h5>';
    html += '<h2>' + (data.percent_complete || 0).toFixed(1) + '%</h2>';
    html += '</div></div></div>';

    // Contract Value card
    html += '<div class="col-md-3">';
    html += '<div class="card">';
    html += '<div class="card-body">';
    html += '<h5 class="card-title">' + __("Contract Value") + '</h5>';
    html += '<h2>' + frappe.EPC.utils.formatCurrency(data.contract_value || 0) + '</h2>';
    html += '</div></div></div>';

    html += '</div>';

    // Billing section
    html += '<hr><div class="row">';
    html += '<div class="col-md-4">';
    html += '<h5>' + __("BOQ Value") + '</h5>';
    html += '<p>' + frappe.EPC.utils.formatCurrency(data.total_boq_value || 0) + '</p>';
    html += '</div>';
    html += '<div class="col-md-4">';
    html += '<h5>' + __("Certified Value") + '</h5>';
    html += '<p>' + frappe.EPC.utils.formatCurrency(data.certified_value || 0) + '</p>';
    html += '</div>';
    html += '<div class="col-md-4">';
    html += '<h5>' + __("Open NCRs") + '</h5>';
    html += '<p>' + (data.open_ncrs || 0) + '</p>';
    html += '</div>';
    html += '</div>';

    return html;
};