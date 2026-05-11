// Module initialization
frappe.provide("epc_modules");

// Boot handler
frappe.pages['epc-reports'].on_page_load = function(wrapper) {
    var page = frappe.ui.make_app_page({
        parent: wrapper,
        title: 'EPC Reports',
        single_column: true
    });

    // Load reports
    frappe.call({
        method: "epc_modules.api.reports.get_epc_reports_list",
        callback: function(r) {
            if (r.message) {
                render_reports_list(page, r.message);
            }
        }
    });
};

function render_reports_list(page, reports) {
    var html = '<div class="row">';

    reports.forEach(function(report) {
        html += '<div class="col-md-4">';
        html += '<div class="card" style="margin-bottom: 15px;">';
        html += '<div class="card-body">';
        html += '<h5 class="card-title">' + report.title + '</h5>';
        html += '<p class="card-text">' + report.description + '</p>';
        html += '<button class="btn btn-primary btn-sm" onclick="open_report(\'' + report.name + '\')">';
        html += __('View Report') + '</button>';
        html += '</div></div></div>';
    });

    html += '</div>';

    page.main.html(html);
}

window.open_report = function(report_name) {
    frappe.set_route("query-report", report_name);
};