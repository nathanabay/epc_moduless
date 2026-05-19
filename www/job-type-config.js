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
        const me = this;
        frappe.prompt([
            { fieldname: "job_type", fieldtype: "Data", label: "Job Type", reqd: 1 },
            { fieldname: "job_category", fieldtype: "Select", label: "Category",
              options: "Labor\nEquipment\nMaterial\nProfessional Services\nOther", reqd: 1 },
            { fieldname: "default_rate", fieldtype: "Currency", label: "Default Rate" },
            { fieldname: "uom", fieldtype: "Link", label: "UOM", options: "UOM" }
        ], function(values) {
            frappe.call({
                method: "epc_modules.api.job_type_api.create_job_type",
                args: {
                    job_type: values.job_type,
                    job_category: values.job_category,
                    default_rate: values.default_rate || 0,
                    uom: values.uom || "Hour"
                },
                callback: async function() {
                    await me.loadJobTypes();
                    me.render();
                }
            });
        }, "Add Job Type", "Create");
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