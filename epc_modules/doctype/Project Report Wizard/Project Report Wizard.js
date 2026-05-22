// Project Report Wizard - Form Client Script

frappe.ui.form.on('Project Report Wizard', {
    refresh(frm) {
        // Add "Generate Report" custom button
        if (frm.doc.status !== 'Generating') {
            frm.add_custom_button(__('Generate Report'), () => {
                frm.events.generate_report(frm);
            }, __('Actions'));
        }

        // When status == "Generated": add "Download" button
        if (frm.doc.status === 'Generated') {
            frm.add_custom_button(__('Download Report'), () => {
                frm.events.download_report(frm);
            }, __('Actions'));
        }

        // Show view report if file exists
        if (frm.doc.generated_report) {
            frm.add_custom_button(__('View Report'), () => {
                frm.events.view_report(frm);
            });
        }

        // Set up field visibility based on report type
        frm.events.setup_field_visibility(frm);
    },

    validate_url(url) {
        // Prevent javascript: URI XSS attacks
        if (url && url.toLowerCase().startsWith('javascript:')) {
            frappe.msgprint({
                title: __('Security Warning'),
                message: __('Invalid URL scheme'),
                indicator: 'red'
            });
            return false;
        }
        return true;
    },

    view_report(frm) {
        if (frm.doc.generated_report) {
            if (frm.events.validate_url(frm.doc.generated_report)) {
                window.open(frm.doc.generated_report, '_blank');
            }
        }
    },

    report_type(frm) {
        // Toggle visibility of relevant filter fields based on report type
        frm.events.setup_field_visibility(frm);
    },

    project(frm) {
        // Filter typology options based on selected project
        if (frm.doc.project) {
            frappe.call({
                method: 'frappe.client.get',
                args: {
                    doctype: 'Project',
                    name: frm.doc.project
                },
                callback: function(r) {
                    if (r.message && r.message.project_typology) {
                        // Pre-select typology based on project
                        frm.set_value('typology_filter', r.message.project_typology);
                    }
                }
            });
        }
    },

    setup_field_visibility(frm) {
        // Hide date range fields for report types that don't need them
        var no_date_report_types = ['Project Status', 'Equipment Utilization'];
        var show_wbs_types = ['WIP Report', 'Project Status'];
        var show_ncr_types = ['NCR Summary', 'Inspection Status'];

        // Date range visibility
        if (no_date_report_types.includes(frm.doc.report_type)) {
            frm.toggle_display(['from_date', 'to_date'], false);
        } else {
            frm.toggle_display(['from_date', 'to_date'], true);
        }

        // WBS visibility
        if (show_wbs_types.includes(frm.doc.report_type)) {
            frm.toggle_display('include_wbs', true);
        } else {
            frm.set_value('include_wbs', 0);
            frm.toggle_display('include_wbs', false);
        }

        // NCR visibility
        if (show_ncr_types.includes(frm.doc.report_type)) {
            frm.toggle_display('include_ncrs', true);
        } else {
            frm.set_value('include_ncrs', 0);
            frm.toggle_display('include_ncrs', false);
        }
    },

    generate_report(frm) {
        if (!frm.doc.report_type) {
            frappe.msgprint(__('Please select a Report Type first'));
            return;
        }

        if (!frm.doc.project) {
            frappe.msgprint(__('Please select a Project'));
            return;
        }

        // Validate date range if applicable
        var no_date_report_types = ['Project Status', 'Equipment Utilization'];
        if (!no_date_report_types.includes(frm.doc.report_type)) {
            if (frm.doc.from_date && frm.doc.to_date) {
                if (frm.doc.from_date > frm.doc.to_date) {
                    frappe.msgprint(__('From Date must be before or equal to To Date'));
                    return;
                }
            }
        }

        // Save and trigger generation
        frm.save().then(() => {
            frappe.call({
                method: 'epc_modules.api.reports_api.generate_project_report',
                args: {
                    data: {
                        wizard_name: frm.doc.name,
                        report_name: frm.doc.report_name,
                        report_type: frm.doc.report_type,
                        project: frm.doc.project,
                        typology_filter: frm.doc.typology_filter,
                        from_date: frm.doc.from_date,
                        to_date: frm.doc.to_date,
                        include_wbs: frm.doc.include_wbs,
                        include_ncrs: frm.doc.include_ncrs,
                        output_format: frm.doc.output_format
                    }
                },
                callback: function(r) {
                    if (r.message && r.message.success) {
                        frappe.msgprint({
                            title: __('Report Generated'),
                            message: __('Report has been generated successfully'),
                            indicator: 'green'
                        });
                        frm.reload();
                    } else if (r.message && r.message.error) {
                        frappe.msgprint({
                            title: __('Error'),
                            message: r.message.error,
                            indicator: 'red'
                        });
                    }
                },
                error: function(r) {
                    frappe.msgprint({
                        title: __('Error'),
                        message: __('Failed to generate report'),
                        indicator: 'red'
                    });
                }
            });
        });
    },

    download_report(frm) {
        if (frm.doc.generated_report) {
            if (frm.events.validate_url(frm.doc.generated_report)) {
                window.open(frm.doc.generated_report, '_blank');
            }
        } else if (frm.doc.report_data) {
            // Download as JSON/Excel if no file attached
            var data = JSON.parse(frm.doc.report_data);
            var filename = frm.doc.report_name || 'Project_Report';

            if (frm.doc.output_format === 'Excel') {
                // Trigger Excel download
                frappe.call({
                    method: 'epc_modules.api.reports_api.export_project_report_to_excel',
                    args: {
                        data: data,
                        filename: filename
                    },
                    callback: function(r) {
                        if (r.message && r.message.file_url) {
                            if (frm.events.validate_url(r.message.file_url)) {
                                window.open(r.message.file_url, '_blank');
                            }
                        }
                    }
                });
            } else {
                // For HTML/PDF, open in new window using DOMParser to prevent XSS
                var reportWindow = window.open('', '_blank');
                if (reportWindow) {
                    var parser = new DOMParser();
                    var doc = parser.parseFromString(data.html || '<pre>' + JSON.stringify(data, null, 2) + '</pre>', 'text/html');
                    var bodyContent = doc.body.innerHTML;
                    reportWindow.document.write('<html><body>' + bodyContent + '</body></html>');
                    reportWindow.document.close();
                }
            }
        }
    }
});