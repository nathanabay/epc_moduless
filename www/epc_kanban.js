/* EPC Kanban Board JavaScript */

frappe.provide("epc_modules.kanban");

epc_modules.kanban.Board = class KanbanBoard {
    constructor() {
        this.projects = [];
        this.currentView = localStorage.getItem("kanban_view_mode") || "typology";
        this.init();
    }

    async init() {
        this.viewSelector = document.getElementById("view-selector");
        this.boardEl = document.getElementById("kanban-board");

        if (this.viewSelector) {
            this.viewSelector.value = this.currentView;
            this.viewSelector.addEventListener("change", (e) => {
                this.currentView = e.target.value;
                localStorage.setItem("kanban_view_mode", this.currentView);
                this.render();
            });
        }

        await this.loadProjects();
        this.render();
    }

    async loadProjects() {
        try {
            const response = await frappe.call({
                method: "epc_modules.api.kanban_api.get_projects"
            });
            this.projects = response.message.projects || [];
        } catch (error) {
            console.error("Failed to load projects:", error);
            this.projects = [];
        }
    }

    getColumnConfig() {
        const configs = {
            typology: {
                key: "typology",
                label: (val) => val || "Uncategorized",
                order: ["Electromechanical", "Civil", "Standard/Service", "Uncategorized"]
            },
            health: {
                key: "health",
                label: (val) => val || "Unknown",
                order: ["Healthy", "At Risk", "Critical"]
            },
            status: {
                key: "status",
                label: (val) => val || "Unknown",
                order: ["Active", "Planning", "On Hold", "Completed", "Closed"]
            },
            date_status: {
                key: "date_status",
                label: (val) => val || "Unknown",
                order: ["Upcoming Start", "In Progress", "Near Deadline", "Overdue"]
            }
        };
        return configs[this.currentView] || configs.typology;
    }

    groupProjects() {
        const config = this.getColumnConfig();
        const groups = {};

        // Initialize all columns
        config.order.forEach(col => {
            groups[col] = [];
        });

        // Group projects
        this.projects.forEach(project => {
            const key = project[config.key] || "Uncategorized";
            if (!groups[key]) {
                groups[key] = [];
            }
            groups[key].push(project);
        });

        // Remove empty columns in date_status view
        if (this.currentView === "date_status") {
            Object.keys(groups).forEach(key => {
                if (groups[key].length === 0) {
                    delete groups[key];
                }
            });
        }

        return groups;
    }

    formatCurrency(value) {
        if (!value) return "$ 0.00";
        return "$ " + Number(value).toLocaleString("en-US", {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2
        });
    }

    formatDateRange(start, end) {
        if (!start && !end) return "";
        const fmt = (d) => {
            if (!d) return "";
            const date = new Date(d);
            return date.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "2-digit" });
        };
        return `${fmt(start)} — ${fmt(end)}`;
    }

    getTypologyClass(typology) {
        if (!typology) return "";
        const map = {
            "Electromechanical": "electromechanical",
            "Civil": "civil",
            "Standard/Service": "standard"
        };
        return map[typology] || "";
    }

    escapeHtml(str) {
        if (str == null) return "";
        const div = document.createElement("div");
        div.textContent = String(str);
        return div.innerHTML;
    }

    renderCard(project) {
        const typologyClass = this.escapeHtml(this.getTypologyClass(project.typology));
        const typologyDisplay = this.escapeHtml(project.typology || "Unknown");
        const projectName = this.escapeHtml(project.project_name || "");
        const customer = this.escapeHtml(project.customer || "");
        const location = this.escapeHtml(project.location || "");

        return `
            <div class="kanban-card" data-project="${this.escapeHtml(project.name)}">
                <div class="kanban-card-title">${projectName}</div>
                <div class="kanban-card-subtitle">${customer} · ${location}</div>
                <span class="kanban-badge ${typologyClass}">${typologyDisplay}</span>
                <div class="kanban-card-dates">${this.formatDateRange(project.expected_start, project.expected_end)}</div>
                <div class="kanban-progress">
                    <div class="kanban-progress-bar">
                        <div class="kanban-progress-fill" style="width: ${Math.min(project.percent_complete, 100)}%"></div>
                    </div>
                    <span class="kanban-progress-label">${project.percent_complete}% Complete</span>
                </div>
                <div class="kanban-card-value">${this.formatCurrency(project.contract_value)}</div>
                <div class="kanban-card-stats">
                    <span>NCRs: <span class="stat-value">${project.open_ncrs}</span></span>
                    <span>WOs: <span class="stat-value">${project.work_orders}</span></span>
                    <span>CS: <span class="stat-value">${project.cost_sheets}</span></span>
                </div>
            </div>
        `;
    }

    escapeAttr(str) {
        if (str == null) return "";
        return String(str).replace(/"/g, "&quot;").replace(/'/g, "&#39;");
    }

    renderColumn(columnKey, projects) {
        const config = this.getColumnConfig();
        const label = config.label(columnKey);
        const attrKey = this.currentView === "typology" ? "typology" :
                       this.currentView === "health" ? "health" : this.currentView === "status" ? "status" : "date_status";

        const cardsHtml = projects.length > 0
            ? projects.map(p => this.renderCard(p)).join("")
            : `<div class="kanban-empty-column">No projects</div>`;

        return `
            <div class="kanban-column" data-group="${this.escapeAttr(this.currentView)}">
                <div class="kanban-column-header" data-${attrKey}="${this.escapeAttr(columnKey)}">
                    <h3>${this.escapeHtml(label)}</h3>
                    <span class="kanban-column-count">${projects.length}</span>
                </div>
                <div class="kanban-cards">
                    ${cardsHtml}
                </div>
            </div>
        `;
    }

    render() {
        if (!this.boardEl) return;

        this.boardEl.innerHTML = '<div class="kanban-loading">Loading projects...</div>';

        const groups = this.groupProjects();
        let html = "";

        Object.keys(groups).forEach(key => {
            html += this.renderColumn(key, groups[key]);
        });

        this.boardEl.innerHTML = html;

        // Add click handlers to cards
        this.boardEl.querySelectorAll(".kanban-card").forEach(card => {
            card.addEventListener("click", () => {
                const projectName = card.dataset.project;
                window.location.href = `/epc-project-dashboard?project=${encodeURIComponent(projectName)}`;
            });
        });
    }
};

// Initialize on page load
document.addEventListener("DOMContentLoaded", () => {
    if (document.getElementById("kanban-board")) {
        new epc_modules.kanban.Board();
    }
});