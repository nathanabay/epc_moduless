frappe.provide("epc_modules.jobtype");

epc_modules.jobtype.Config = class JobTypeConfig {
    constructor() {
        this.jobTypes = [];
        this.init();
    }

    async init() {
        document.getElementById("new-job-type-btn").addEventListener("click", () => this.showModal());
        await this.loadJobTypes();
        this.render();
    }

    async loadJobTypes() {
        try {
            const response = await frappe.call({
                method: "epc_modules.api.job_type_api.get_job_types"
            });
            this.jobTypes = response.message?.job_types || [];
        } catch (error) {
            console.error("Failed to load job types:", error);
        }
    }

    render() {
        const tbody = document.getElementById("job-type-list");
        if (!tbody) return;

        if (this.jobTypes.length === 0) {
            tbody.innerHTML = '<tr><td colspan="6" style="text-align:center;color:#666;">No job types configured</td></tr>';
            return;
        }

        tbody.innerHTML = this.jobTypes.map(jt => `
            <tr data-name="${this.escapeHtml(jt.name)}">
                <td>${this.escapeHtml(jt.job_type)}</td>
                <td>${this.escapeHtml(jt.job_category)}</td>
                <td>${this.formatCurrency(jt.default_rate)}</td>
                <td>${this.escapeHtml(jt.uom || "Hour")}</td>
                <td>
                    <span class="${jt.is_active ? 'status-active' : 'status-inactive'}">
                        ${jt.is_active ? "Active" : "Inactive"}
                    </span>
                </td>
                <td>
                    <button class="btn-sm ${jt.is_active ? 'btn-disable' : 'btn-enable'}"
                            data-action="toggle" data-name="${this.escapeHtml(jt.name)}">
                        ${jt.is_active ? "Disable" : "Enable"}
                    </button>
                </td>
            </tr>
        `).join("");

        tbody.querySelectorAll("[data-action='toggle']").forEach(btn => {
            btn.addEventListener("click", (e) => {
                e.stopPropagation();
                this.toggleJobType(btn.dataset.name);
            });
        });
    }

    async toggleJobType(name) {
        const jt = this.jobTypes.find(j => j.name === name);
        if (!jt) return;

        try {
            await frappe.call({
                method: "epc_modules.api.job_type_api.toggle_job_type",
                args: { name: name, is_active: !jt.is_active }
            });
            await this.loadJobTypes();
            this.render();
        } catch (error) {
            console.error("Failed to toggle job type:", error);
        }
    }

    showModal() {
        const jobType = prompt("Enter job type name:");
        if (!jobType) return;

        const category = prompt("Enter category (Labor/Equipment/Material/Professional Services/Other):");
        if (!category) return;

        const rate = prompt("Enter default rate:", "0");
        const uom = prompt("Enter UOM:", "Hour");

        frappe.call({
            method: "epc_modules.api.job_type_api.create_job_type",
            args: {
                job_type: jobType,
                job_category: category,
                default_rate: parseFloat(rate) || 0,
                uom: uom || "Hour"
            },
            callback: async () => {
                await this.loadJobTypes();
                this.render();
            }
        });
    }

    formatCurrency(value) {
        if (value == null) return "$ 0.00";
        return "$ " + Number(value).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    }

    escapeHtml(str) {
        if (str == null) return "";
        const div = document.createElement("div");
        div.textContent = String(str);
        return div.innerHTML;
    }
};

document.addEventListener("DOMContentLoaded", () => {
    if (document.querySelector(".job-type-container")) {
        new epc_modules.jobtype.Config();
    }
});