/* EPC WIP Report JavaScript */

frappe.provide("epc_modules.wip");

epc_modules.wip.Report = class WIPReport {
    constructor() {
        this.data = { financial: [], progress: [], resource: [] };
        this.currentTab = "financial";
        this.init();
    }

    async init() {
        this.tabEls = document.querySelectorAll(".wip-tab");
        this.contentEls = document.querySelectorAll(".wip-content");

        this.tabEls.forEach(tab => {
            tab.addEventListener("click", () => {
                this.switchTab(tab.dataset.tab);
            });
        });

        await this.loadData();
        this.render();
    }

    async loadData() {
        try {
            const response = await frappe.call({
                method: "epc_modules.api.wip_api.get_wip_report"
            });
            this.data = response.message;
        } catch (error) {
            console.error("Failed to load WIP data:", error);
        }
    }

    switchTab(tab) {
        this.currentTab = tab;
        this.tabEls.forEach(el => {
            el.classList.toggle("active", el.dataset.tab === tab);
        });
        this.contentEls.forEach(el => {
            el.classList.toggle("active", el.id === "wip-" + tab);
        });
        this.render();
    }

    formatCurrency(value) {
        if (value == null) return "ETB 0.00";
        return "ETB " + Number(value).toLocaleString("en-US", {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2
        });
    }

    formatNumber(value) {
        if (value == null) return "0";
        return Number(value).toLocaleString("en-US", {
            minimumFractionDigits: 0,
            maximumFractionDigits: 2
        });
    }

    render() {
        this.renderFinancial();
        this.renderProgress();
        this.renderResource();
    }

    renderFinancial() {
        const data = this.data.financial || [];
        const container = document.getElementById("wip-financial-table");
        if (!container) return;

        // Summary cards
        const totalWip = data.reduce((sum, d) => sum + (d.wip_value || 0), 0);
        const totalRetention = data.reduce((sum, d) => sum + (d.retention || 0), 0);
        document.getElementById("wip-financial-summary").innerHTML = `
            <div class="wip-summary-card">
                <div class="label">Total WIP Value</div>
                <div class="value">${this.formatCurrency(totalWip)}</div>
            </div>
            <div class="wip-summary-card warning">
                <div class="label">Total Retention</div>
                <div class="value">${this.formatCurrency(totalRetention)}</div>
            </div>
            <div class="wip-summary-card">
                <div class="label">Projects</div>
                <div class="value">${data.length}</div>
            </div>
        `;

        if (data.length === 0) {
            container.innerHTML = '<tr><td colspan="8" class="wip-loading">No financial data</td></tr>';
            return;
        }

        container.innerHTML = data.map(d => `
            <tr>
                <td>${this.escapeHtml(d.project_name)}</td>
                <td>${this.formatCurrency(d.contract_value)}</td>
                <td>${this.formatCurrency(d.certified_value)}</td>
                <td>${this.formatCurrency(d.invoiced_value)}</td>
                <td><strong>${this.formatCurrency(d.wip_value)}</strong></td>
                <td>${this.formatCurrency(d.retention)}</td>
                <td>${this.formatCurrency(d.retention_recoverable)}</td>
            </tr>
        `).join("");
    }

    renderProgress() {
        const data = this.data.progress || [];
        const container = document.getElementById("wip-progress-table");
        if (!container) return;

        if (data.length === 0) {
            container.innerHTML = '<tr><td colspan="7" class="wip-loading">No progress data</td></tr>';
            return;
        }

        container.innerHTML = data.map(d => {
            const badgeClass = d.status === "Critical" ? "critical" : d.status === "Behind" ? "behind" : "on-track";
            return `
                <tr>
                    <td>${this.escapeHtml(d.project_name)}</td>
                    <td>${this.escapeHtml(d.wbs_item)}</td>
                    <td>${this.escapeHtml(d.wbs_code)}</td>
                    <td>${(d.planned_progress || 0).toFixed(1)}%</td>
                    <td>${(d.actual_progress || 0).toFixed(1)}%</td>
                    <td class="${d.variance < 0 ? 'wip-danger' : ''}">${d.variance > 0 ? '+' : ''}${(d.variance || 0).toFixed(1)}%</td>
                    <td><span class="wip-badge ${badgeClass}">${this.escapeHtml(d.status)}</span></td>
                </tr>
            `;
        }).join("");
    }

    renderResource() {
        const data = this.data.resource || [];
        const container = document.getElementById("wip-resource-table");
        if (!container) return;

        const totalHours = data.reduce((sum, d) => sum + (d.total_hours || 0), 0);
        const totalCost = data.reduce((sum, d) => sum + (d.labor_cost || 0), 0);
        document.getElementById("wip-resource-summary").innerHTML = `
            <div class="wip-summary-card">
                <div class="label">Total Labor Hours</div>
                <div class="value">${this.formatNumber(totalHours)}</div>
            </div>
            <div class="wip-summary-card">
                <div class="label">Total Labor Cost</div>
                <div class="value">${this.formatCurrency(totalCost)}</div>
            </div>
            <div class="wip-summary-card warning">
                <div class="label">Unbilled Hours</div>
                <div class="value">${this.formatNumber(data.reduce((sum, d) => sum + (d.unbilled_hours || 0), 0))}</div>
            </div>
        `;

        if (data.length === 0) {
            container.innerHTML = '<tr><td colspan="6" class="wip-loading">No resource data</td></tr>';
            return;
        }

        container.innerHTML = data.map(d => {
            const badgeClass = d.billing_status === "Billed" ? "billed" : "unbilled";
            return `
                <tr>
                    <td>${this.escapeHtml(d.project_name)}</td>
                    <td>${this.formatNumber(d.total_hours)}</td>
                    <td>${this.formatCurrency(d.labor_cost)}</td>
                    <td>${this.formatNumber(d.billed_hours)}</td>
                    <td>${this.formatNumber(d.unbilled_hours)}</td>
                    <td><span class="wip-badge ${badgeClass}">${this.escapeHtml(d.billing_status)}</span></td>
                </tr>
            `;
        }).join("");
    }

    escapeHtml(str) {
        if (str == null) return "";
        const div = document.createElement("div");
        div.textContent = String(str);
        return div.innerHTML;
    }
};

document.addEventListener("DOMContentLoaded", () => {
    if (document.getElementById("wip-container")) {
        new epc_modules.wip.Report();
    }
});