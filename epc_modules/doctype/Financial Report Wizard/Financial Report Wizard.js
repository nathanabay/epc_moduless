// Financial Report Wizard - Form Client Script

frappe.ui.form.on('Financial Report Wizard', {
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

        // Show download if report exists
        if (frm.doc.generated_report) {
            frm.add_custom_button(__('View Report'), () => {
                frm.events.view_report(frm);
            });
        }
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
        // Toggle required on date fields based on report type
        frm.toggle_reqd('from_date', frm.doc.report_type === 'Cash Flow');
        frm.toggle_reqd('to_date', frm.doc.report_type === 'Cash Flow');

        // Show/hide project filter based on report type
        if (frm.doc.report_type === 'Change Order Summary') {
            frm.set_df_property('project', 'reqd', 1);
        } else {
            frm.set_df_property('project', 'reqd', 0);
        }

        // Update group_by options based on report type
        if (frm.doc.report_type === 'Budget vs Actual') {
            frm.set_df_property('group_by', 'options', 'WBS\nCost Line\nJob Type\nNone');
        }
    },

    project(frm) {
        // Filter WBS items based on selected project
        if (frm.doc.project) {
            frappe.call({
                method: 'frappe.client.get_list',
                args: {
                    doctype: 'WBS Item',
                    filters: { project: frm.doc.project },
                    fields: ['name', 'wbs_code', 'item_name'],
                    limit: 200
                },
                callback: function(r) {
                    if (r.message) {
                        let options = [''];
                        r.message.forEach(item => {
                            options.push(item.name);
                        });
                        frm.set_df_property('wbs_item', 'options', options.join('\n'));
                    }
                }
            });
        }
    },

    generate_report(frm) {
        if (!frm.doc.report_type) {
            frappe.msgprint(__('Please select a Report Type first'));
            return;
        }

        if (!frm.doc.project && frm.doc.report_type !== 'Budget vs Actual') {
            frappe.msgprint(__('Please select a Project'));
            return;
        }

        // Validate date range for Cash Flow
        if (frm.doc.report_type === 'Cash Flow') {
            if (!frm.doc.from_date || !frm.doc.to_date) {
                frappe.msgprint(__('Cash Flow report requires From Date and To Date'));
                return;
            }
        }

        // Save and trigger generation
        frm.save().then(() => {
            frappe.call({
                method: 'epc_modules.api.reports_api.generate_financial_report',
                args: {
                    data: {
                        wizard_name: frm.doc.name,
                        report_type: frm.doc.report_type,
                        project: frm.doc.project,
                        wbs_item: frm.doc.wbs_item,
                        from_date: frm.doc.from_date,
                        to_date: frm.doc.to_date,
                        include_archived: frm.doc.include_archived,
                        group_by: frm.doc.group_by,
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
            let data = JSON.parse(frm.doc.report_data);
            let filename = frm.doc.report_name || 'Financial_Report';

            if (frm.doc.output_format === 'Excel') {
                // Trigger Excel download
                frappe.call({
                    method: 'epc_modules.api.reports_api.export_to_excel',
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
                let reportWindow = window.open('', '_blank');
                if (reportWindow) {
                    let parser = new DOMParser();
                    let doc = parser.parseFromString(data.html || '<pre>' + JSON.stringify(data, null, 2) + '</pre>', 'text/html');
                    let bodyContent = doc.body.innerHTML;
                    reportWindow.document.write('<html><body>' + bodyContent + '</body></html>');
                    reportWindow.document.close();
                }
            }
        }
    }
});