frappe.provide("epc_modules.materialplan");

epc_modules.materialplan.App = class MaterialPlanApp {
    constructor() {
        this.plans = [];
        this.currentPlan = null;
        this.init();
    }

    async init() {
        document.getElementById("new-plan-btn").addEventListener("click", () => this.showNewPlanModal());
        document.getElementById("close-detail-btn").addEventListener("click", () => this.hideDetail());
        document.getElementById("generate-boq-btn").addEventListener("click", () => this.generateFromBOQ());
        document.getElementById("generate-wbs-btn").addEventListener("click", () => this.generateFromWBS());
        document.getElementById("add-item-btn").addEventListener("click", () => this.showAddItemModal());

        await this.loadPlans();
        this.render();
    }

    async loadPlans() {
        try {
            const response = await frappe.call({
                method: "epc_modules.api.material_plan_api.get_material_plan"
            });
            this.plans = response.message?.plans || [];
        } catch (error) {
            console.error("Failed to load plans:", error);
        }
    }

    render() {
        const tbody = document.getElementById("plan-list");
        if (!tbody) return;

        if (this.plans.length === 0) {
            tbody.innerHTML = '<tr><td colspan="5" style="text-align:center;color:#666;">No material plans found</td></tr>';
            return;
        }

        tbody.innerHTML = this.plans.map(plan => `
            <tr data-name="${this.escapeHtml(plan.name)}">
                <td>${this.escapeHtml(plan.name)}</td>
                <td>${this.escapeHtml(plan.plan_date || "")}</td>
                <td><span class="status-badge status-${(plan.status || "draft").toLowerCase()}">${this.escapeHtml(plan.status || "Draft")}</span></td>
                <td>${this.formatCurrency(plan.estimated_total)}</td>
                <td>${plan.item_count || 0}</td>
            </tr>
        `).join("");

        tbody.querySelectorAll("tr[data-name]").forEach(row => {
            row.addEventListener("click", () => this.showPlanDetails(row.dataset.name));
        });
    }

    async showPlanDetails(name) {
        try {
            const response = await frappe.call({
                method: "epc_modules.api.material_plan_api.get_material_plan_details",
                args: { name: name }
            });
            this.currentPlan = response.message;
            this.renderPlanDetails();
            document.getElementById("plan-detail").style.display = "block";
        } catch (error) {
            console.error("Failed to load plan details:", error);
        }
    }

    renderPlanDetails() {
        const data = this.currentPlan;
        if (!data || !data.plan) return;

        document.getElementById("detail-title").textContent = data.plan.name;

        const tbody = document.getElementById("plan-items");
        const items = data.items || [];

        if (items.length === 0) {
            tbody.innerHTML = '<tr><td colspan="8" style="text-align:center;color:#666;">No items in this plan</td></tr>';
            return;
        }

        tbody.innerHTML = items.map(item => `
            <tr>
                <td>${this.escapeHtml(item.item_code || "")}</td>
                <td>${this.escapeHtml(item.item_name || "")}</td>
                <td>${this.escapeHtml(item.uom || "")}</td>
                <td>${item.required_quantity || 0}</td>
                <td>${item.ordered_quantity || 0}</td>
                <td>${this.formatCurrency(item.unit_rate)}</td>
                <td>${this.formatCurrency(item.estimated_cost)}</td>
                <td><span class="status-badge status-${(item.procurement_status || "pending").toLowerCase().replace(" ", "-")}">${this.escapeHtml(item.procurement_status || "Pending")}</span></td>
            </tr>
        `).join("");
    }

    hideDetail() {
        document.getElementById("plan-detail").style.display = "none";
        this.currentPlan = null;
    }

    async generateFromBOQ() {
        if (!this.currentPlan || !this.currentPlan.plan) return;
        try {
            const items = await frappe.call({
                method: "epc_modules.api.material_plan_api.generate_from_boq",
                args: { project: this.currentPlan.plan.project }
            });
            console.log("Generated from BOQ:", items.message);
            await this.showPlanDetails(this.currentPlan.plan.name);
        } catch (error) {
            console.error("Failed to generate from BOQ:", error);
        }
    }

    async generateFromWBS() {
        if (!this.currentPlan || !this.currentPlan.plan) return;
        try {
            const items = await frappe.call({
                method: "epc_modules.api.material_plan_api.generate_from_wbs",
                args: { project: this.currentPlan.plan.project }
            });
            console.log("Generated from WBS:", items.message);
            await this.showPlanDetails(this.currentPlan.plan.name);
        } catch (error) {
            console.error("Failed to generate from WBS:", error);
        }
    }

    showNewPlanModal() {
        const me = this;
        frappe.prompt([
            { fieldname: "project", fieldtype: "Link", label: "Project", options: "Project", reqd: 1 }
        ], function(values) {
            frappe.call({
                method: "epc_modules.api.material_plan_api.create_material_plan",
                args: { project: values.project },
                callback: async function() {
                    await me.loadPlans();
                    me.render();
                }
            });
        }, "Create Material Plan", "Create");
    }

    showAddItemModal() {
        // Placeholder for add item functionality
        console.log("Add item clicked");
    }

    formatCurrency(value) {
        if (value == null) return "ETB 0.00";
        return "ETB " + Number(value).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    }

    escapeHtml(str) {
        if (str == null) return "";
        const div = document.createElement("div");
        div.textContent = String(str);
        return div.innerHTML;
    }
};

document.addEventListener("DOMContentLoaded", () => {
    if (document.querySelector(".material-plan-container")) {
        new epc_modules.materialplan.App();
    }
});