frappe.provide("epc_modules.costline");

epc_modules.costline.Breakdown = class CostLineBreakdown {
    constructor() {
        this.data = { project_level: {}, wbs_level: [] };
        this.currentTab = "project";
        this.init();
    }

    async init() {
        this.tabEls = document.querySelectorAll(".tab");
        this.tabEls.forEach(tab => {
            tab.addEventListener("click", () => this.switchTab(tab.dataset.tab));
        });

        await this.loadData();
        this.render();
    }

    async loadData() {
        try {
            const response = await frappe.call({
                method: "epc_modules.api.cost_line_api.get_cost_breakdown"
            });
            this.data = response.message || { project_level: {}, wbs_level: [] };
        } catch (error) {
            console.error("Failed to load cost breakdown:", error);
        }
    }

    switchTab(tab) {
        this.currentTab = tab;
        this.tabEls.forEach(el => el.classList.toggle("active", el.dataset.tab === tab));
        document.getElementById("tab-project").classList.toggle("active", tab === "project");
        document.getElementById("tab-wbs").classList.toggle("active", tab === "wbs");
    }

    formatCurrency(value) {
        if (value == null) return "$ 0.00";
        return "$ " + Number(value).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    }

    render() {
        this.renderProjectSummary();
        this.renderWBSBreakdown();
    }

    renderProjectSummary() {
        const pl = this.data.project_level || {};
        const totalEl = document.getElementById("cost-project-table");
        if (!totalEl) return;

        document.querySelector(".summary-cards").innerHTML = `
            <div class="summary-card">
                <div class="label">Total Estimated</div>
                <div class="value">${this.formatCurrency(pl.total_estimated)}</div>
            </div>
            <div class="summary-card">
                <div class="label">Total Actual</div>
                <div class="value">${this.formatCurrency(pl.total_actual)}</div>
            </div>
            <div class="summary-card ${(pl.variance || 0) < 0 ? 'warning' : ''}">
                <div class="label">Variance</div>
                <div class="value">${this.formatCurrency(pl.variance)}</div>
            </div>
        `;

        const categories = pl.by_category || {};
        totalEl.innerHTML = Object.entries(categories).map(([cat, data]) => `
            <tr>
                <td>${this.escapeHtml(cat)}</td>
                <td>${this.formatCurrency(data.estimated)}</td>
                <td>${this.formatCurrency(data.actual)}</td>
                <td class="${data.variance < 0 ? 'wip-danger' : 'wip-success'}">${this.formatCurrency(data.variance)}</td>
            </tr>
        `).join("");
    }

    renderWBSBreakdown() {
        const container = document.getElementById("wbs-breakdown-list");
        if (!container) return;

        const wbsList = this.data.wbs_level || [];
        if (wbsList.length === 0) {
            container.innerHTML = "<p>No WBS cost breakdowns found.</p>";
            return;
        }

        container.innerHTML = wbsList.map(wbs => `
            <div class="wbs-item">
                <h3>${this.escapeHtml(wbs.wbs_item || 'Unknown')} (${this.escapeHtml(wbs.wbs_code || 'N/A')})</h3>
                <table class="cost-table">
                    <thead>
                        <tr><th>Category</th><th>Estimated</th><th>Actual</th><th>Variance</th></tr>
                    </thead>
                    <tbody>
                        ${(wbs.cost_lines || []).map(line => `
                            <tr>
                                <td>${this.escapeHtml(line.category || 'Other')}</td>
                                <td>${this.formatCurrency(line.estimated)}</td>
                                <td>${this.formatCurrency(line.actual)}</td>
                                <td class="${(line.variance || 0) < 0 ? 'wip-danger' : 'wip-success'}">${this.formatCurrency(line.variance)}</td>
                            </tr>
                        `).join("")}
                    </tbody>
                </table>
                <div class="wbs-totals">
                    Totals: Est ${this.formatCurrency(wbs.totals?.estimated)} |
                    Act ${this.formatCurrency(wbs.totals?.actual)} |
                    Var ${this.formatCurrency(wbs.totals?.variance)}
                </div>
            </div>
        `).join("");
    }

    escapeHtml(str) {
        if (str == null) return "";
        const div = document.createElement("div");
        div.textContent = String(str);
        return div.innerHTML;
    }
};

document.addEventListener("DOMContentLoaded", () => {
    if (document.querySelector(".cost-line-container")) {
        new epc_modules.costline.Breakdown();
    }
});