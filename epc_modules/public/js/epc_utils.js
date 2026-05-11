"""
EPC Utilities JavaScript

Client-side utilities for EPC module.
"""

frappe.EPC = {
    utils: {},
    typology: {}
};

/**
 * Get typology configuration for current project
 */
frappe.EPC.getTypologyConfig = function(project) {
    return frappe.call({
        method: "epc_modules.api.project_api.get_typology_config",
        args: {
            project: project
        },
        callback: function(r) {
            return r.message;
        }
    });
};

/**
 * Apply typology-specific UI settings
 */
frappe.EPC.applyTypologyUI = function(frm, typology) {
    if (!typology) return;

    var typology_type = typology.typology_type;

    // Hide/show sections based on typology
    if (typology_type === "Standard/Service") {
        // Hide civil/electromechanical specific fields
        frm.toggle_display("measurement_book", false);
        frm.toggle_display("site_zones", false);
    } else {
        frm.toggle_display("measurement_book", true);
        frm.toggle_display("site_zones", true);
    }

    // Apply billing track
    if (typology.billing_track) {
        frm.set_value("billing_track", typology.billing_track);
    }
};

/**
 * Validate EPC project before save
 */
frappe.EPC.validateProject = function(frm) {
    if (frm.doc.is_epc_project && !frm.doc.project_typology) {
        frappe.msgprint({
            title: __("Validation"),
            message: __("EPC Project must have a Project Typology"),
            indicator: "red"
        });
        return false;
    }
    return true;
};

/**
 * Calculate project progress
 */
frappe.EPC.calculateProgress = function(project, callback) {
    return frappe.call({
        method: "epc_modules.api.project_api.calculate_project_progress",
        args: {
            project: project
        },
        callback: function(r) {
            if (callback) callback(r.message);
        }
    });
};

/**
 * Get project dashboard data
 */
frappe.EPC.getDashboard = function(project, callback) {
    return frappe.call({
        method: "epc_modules.api.project_api.get_project_dashboard",
        args: {
            project: project
        },
        callback: function(r) {
            if (callback) callback(r.message);
        }
    });
};

/**
 * Format currency for display
 */
frappe.EPC.utils.formatCurrency = function(value, currency) {
    if (!currency) currency = frappe.boot.sysdefaults.currency || "USD";
    return format_currency(value, currency);
};

/**
 * Format percentage with sign
 */
frappe.EPC.utils.formatPercentage = function(value) {
    if (value === undefined || value === null) return "0%";
    return value.toFixed(2) + "%";
};

/**
 * Get status color for project
 */
frappe.EPC.utils.getStatusColor = function(status) {
    var colors = {
        "Draft": "gray",
        "Open": "blue",
        "Active": "green",
        "On Hold": "orange",
        "Completed": "darkgreen",
        "Cancelled": "red"
    };
    return colors[status] || "gray";
};