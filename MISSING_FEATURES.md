# EPC Modules Missing Features Audit

**Generated:** 2026-05-19
**Audited Features:** 14 (Projects & Core)

---

## Summary

| Status | Count |
|--------|-------|
| Fully Implemented | 6 |
| Partial | 3 |
| Missing | 6 |

---

## Implemented Features

### 1. Kanban Project Overview

**Status:** Fully Implemented

**Files:**
- `epc_modules/api/kanban_api.py`
- `epc_modules/www/epc_kanban.css`
- `epc_modules/www/epc_kanban.js`
- `epc_modules/www/kanban-project-overview.html`
- `epc_modules/hooks.py`

**Features:**
- 4 view modes: Typology, Health, Status, Date Status
- Project cards with progress, contract value, stats
- View switcher with localStorage persistence
- XSS protection on all user data

---

### 2. WIP Reports

**Status:** Fully Implemented

**Files:**
- `epc_modules/api/wip_api.py`
- `epc_modules/www/epc_wip.css`
- `epc_modules/www/epc_wip.js`
- `epc_modules/www/wip-report.html`
- `epc_modules/hooks.py`

**Features:**
- 3 tabs: Financial WIP, Progress WIP, Resource WIP
- Summary cards per tab
- XSS protection on all user data

**Files to Create:**
- `epc_modules/doctype/WIP Report/WIP Report.json`
- `epc_modules/api/wip_report_api.py`
- `epc_modules/www/wip-report.html`

---

### 3. Cost Line Breakdowns

**Priority:** High
**Status:** Not Found

**Description:**
No cost line breakdown implementation for granular cost structure.

**Gap:**
- No `cost_line` doctype
- No `CostLine` files
- No line-item cost structure

**Files to Create:**
- `epc_modules/doctype/Cost Line Breakdown/Cost Line Breakdown.json`
- `epc_modules/doctype/Cost Line Item/Cost Line Item.json`

---

### 4. Material Plans

**Priority:** High
**Status:** Not Found

**Description:**
No material planning/requirement system.

**Gap:**
- No `material_plan` doctype
- No `MaterialPlan` files
- No material requirement planning module

**Files to Create:**
- `epc_modules/doctype/Material Plan/Material Plan.json`
- `epc_modules/doctype/Material Plan Item/Material Plan Item.json`
- `epc_modules/api/material_plan_api.py`

---

### 5. Financial Report Wizard

**Priority:** Medium
**Status:** Not Found

**Description:**
No financial report wizard for generating financial reports.

**Gap:**
- No `financial_report` doctype
- No `report_wizard` files
- No financial reporting wizard UI/pages

**Files to Create:**
- `epc_modules/doctype/Financial Report Wizard/Financial Report Wizard.json`
- `epc_modules/www/financial-report-wizard.html`
- `epc_modules/api/financial_report_api.py`

---

### 6. Project Report Wizard

**Priority:** Medium
**Status:** Not Found

**Description:**
No project report wizard for generating project reports.

**Gap:**
- No project report wizard implementation
- No project report configuration

**Files to Create:**
- `epc_modules/doctype/Project Report Wizard/Project Report Wizard.json`
- `epc_modules/www/project-report-wizard.html`
- `epc_modules/api/project_report_api.py`

---

### 7. Job Types Configuration

**Priority:** Medium
**Status:** Not Found

**Description:**
No Job Type doctype or configuration for job type categorization.

**Gap:**
- No `job_type` doctype
- No `JobType` files
- No job type categorization system

**Files to Create:**
- `epc_modules/doctype/Job Type/Job Type.json`
- `epc_modules/fixtures/job_type.json`

---

### 8. Cost Sheet Reports

**Priority:** Medium
**Status:** Not Found

**Description:**
No report generation for cost sheets.

**Gap:**
- No `cost_sheet_report` files
- BOQ calculator exists but no report generation

**Files to Create:**
- `epc_modules/www/cost-sheet-report.html`
- `epc_modules/api/cost_sheet_report_api.py`

---

## Partial Implementations

### 1. Project Phase Tracking

**Status:** Partial

**Existing Files:**
- `epc_modules/doctype/Project Milestone/Project Milestone.json`

**Gap:**
- No phase-level tracking dashboard
- No phase completion metrics UI

**Enhancement:**
- `epc_modules/www/phase-tracking.html`

---

### 2. Team Member Management

**Status:** Partial

**Existing References:**
- `epc_modules/doctype/design_phase/design_phase.json` (team_members field)
- `epc_modules/utils/design_phase_generator.py` (references team_members)

**Gap:**
- No dedicated TeamMember doctype
- No Project Team doctype
- No management UI

**Files to Create:**
- `epc_modules/doctype/Project Team/Project Team.json`
- `epc_modules/doctype/Team Member/Team Member.json`

---

### 3. Cost Sheets

**Status:** Partial

**Existing Files:**
- `epc_modules/doctype/Custom BOQ/`
- `epc_modules/api/boq_api.py`
- `epc_modules/utils/boq_calculator.py`

**Gap:**
- No dedicated "Cost Sheet" doctype
- No cost line breakdown structure
- No Material/labor/equipment separation
- No rate calculation engine

**Files to Create:**
- `epc_modules/doctype/Cost Sheet/Cost Sheet.json`
- `epc_modules/doctype/Cost Sheet Item/Cost Sheet Item.json`
- `epc_modules/utils/cost_sheet_calculator.py`

---

## Existing DocTypes

### Project
- Project Typology
- Project Milestone
- WBS Item

### Billing
- RA Bill
- RA Bill MB Reference
- Measurement Book
- Claim Register

### Progress
- Daily Progress Report
- DPR Entry
- Site Zone

### Quality
- Non-Conformance Report
- Project Inspection Plan
- Inspection Record
- Master Inspection Template
- Inspection Hold Point

### Concrete
- Concrete Mix Design
- Cube Test Result
- Curing Record
- Curing Check Entry
- Formwork Inspection
- Steel Reinforcement Register

### Equipment
- Equipment Register
- Equipment Maintenance Schedule
- Equipment Movement
- Equipment Utilization Log

### Commercial
- Custom BOQ
- Subcontractor Profile
- Subcontractor Work Order

### Risk
- Risk Register
- Risk Response Action

---

## Implementation Priority

### High
1. Cost Line Breakdowns
2. Material Plans
3. Job Types Configuration

### Medium
1. Financial Report Wizard
2. Project Report Wizard
3. Cost Sheet Reports

### Low
1. Project Phase Tracking (enhancement)
2. Team Member Management (new doctype)
3. Cost Sheets (separate doctype)

---

## Site Operations Modules (Audit 2026-05-19)

### Summary

| Status | Count |
|--------|-------|
| Fully Implemented | 5 |
| Partial | 6 |
| Missing | 14 |

---

## Fully Implemented

### 1. Inspection Management

**Status:** Fully Implemented

**Existing Files:**
- `epc_modules/doctype/Inspection Record/` (istable)
- `epc_modules/doctype/Project Inspection Plan/`
- `epc_modules/api/quality_api.py` (get_inspection_templates, get_template_details, clone_templates_to_project, get_project_itps, get_itp_details, record_inspection)
- `epc_modules/utils/quality_gate.py` - ITPManager class

---

### 2. Inspection Types and Lines

**Status:** Fully Implemented

**Existing Files:**
- `epc_modules/doctype/Master Inspection Template/` (hold_points table)
- `epc_modules/doctype/Inspection Hold Point/`

---

### 3. NCR (Non-Conformance Reports)

**Status:** Fully Implemented

**Existing Files:**
- `epc_modules/doctype/Non-Conformance Report/Non-Conformance Report.json`
- `epc_modules/api/quality_api.py` (create_ncr, get_project_ncrs, get_ncr_details, update_ncr_status, close_ncr, verify_ncr, get_quality_summary, check_billing_eligibility)
- `epc_modules/utils/quality_gate.py` - NCRManager class

---

### 4. Daily Site Logs

**Status:** Fully Implemented

**Existing Files:**
- `epc_modules/doctype/Daily Progress Report/Daily Progress Report.json`
- `epc_modules/doctype/DPR Entry/DPR Entry.json`
- `epc_modules/api/dpr_api.py`

---

### 5. Subcontract Orders

**Status:** Fully Implemented

**Existing Files:**
- `epc_modules/doctype/Subcontractor Work Order/Subcontractor Work Order.json`
- `epc_modules/doctype/Subcontractor Profile/Subcontractor Profile.json`
- `epc_modules/api/construction_api.py` (create_subcontractor_profile, get_subcontractor_list, get_expiring_insurance, create_subcontractor_work_order, get_subcontractor_work_orders)

---

## Partial Implementations

### 1. RFI Management

**Status:** Partial

**Existing Files:**
- `epc_modules/api/document_api.py` (create_rfi, get_project_rfis, respond_to_rfi, close_rfi)

**Gap:**
- Missing DocType definition for RFI

**Files to Create:**
- `epc_modules/doctype/RFI/RFI.json`
- `epc_modules/doctype/RFI Item/RFI Item.json`

---

### 2. Transmittals and Lines

**Status:** Partial

**Existing Files:**
- `epc_modules/api/document_api.py` (create_submittal, get_project_submittals, review_submittal)

**Gap:**
- Missing Submittal doctype definition

**Files to Create:**
- `epc_modules/doctype/Submittal/Submittal.json`
- `epc_modules/doctype/Submittal Item/Submittal Item.json`

---

### 3. RFI Reports

**Status:** Partial

**Existing Files:**
- `epc_modules/api/document_api.py` (get_document_summary includes RFI stats, get_overdue_items includes RFIs)

**Gap:**
- No dedicated RFI report generation

**Files to Create:**
- `epc_modules/www/rfi-report.html`

---

### 4. Inspection Reports

**Status:** Partial

**Existing Files:**
- `epc_modules/api/quality_api.py` (get_itp_details, get_project_itps)

**Gap:**
- No dedicated inspection report UI

**Files to Create:**
- `epc_modules/www/inspection-report.html`

---

### 5. NCR Reports

**Status:** Partial

**Existing Files:**
- `epc_modules/api/quality_api.py` (get_ncr_details, get_project_ncrs, get_quality_summary)

**Gap:**
- No dedicated NCR report UI

**Files to Create:**
- `epc_modules/www/ncr-report.html`

---

### 6. Daily Log Reports

**Status:** Partial

**Existing Files:**
- `epc_modules/api/dpr_api.py`

**Gap:**
- No dedicated daily log report UI

**Files to Create:**
- `epc_modules/www/daily-log-report.html`

---

### 7. Transmittal Reports

**Status:** Partial

**Existing Files:**
- `epc_modules/api/document_api.py` (get_project_submittals, get_overdue_items)

**Gap:**
- No dedicated transmittal report UI

**Files to Create:**
- `epc_modules/www/transmittal-report.html`

---

## Missing Features

### 1. RFI Types Configuration

**Priority:** High
**Status:** Not Found

**Description:**
No RFI Types doctype for categorizing RFIs.

**Gap:**
- No `rfi_type` doctype
- No `RFITypes` fixture

**Files to Create:**
- `epc_modules/doctype/RFI Type/RFI Type.json`
- `epc_modules/fixtures/rfi_type.json`

---

### 2. Site Instructions

**Priority:** High
**Status:** Not Found

**Description:**
No Site Instruction doctype for issuing site instructions.

**Gap:**
- No `site_instruction` doctype
- No Site Instruction API

**Files to Create:**
- `epc_modules/doctype/Site Instruction/Site Instruction.json`
- `epc_modules/api/site_instruction_api.py`
- `epc_modules/www/site-instruction.html`

---

### 3. Shop Drawing Register

**Priority:** High
**Status:** Not Found

**Description:**
No Shop Drawing doctype for tracking shop drawings.

**Gap:**
- No `shop_drawing` doctype
- No Shop Drawing API

**Files to Create:**
- `epc_modules/doctype/Shop Drawing/Shop Drawing.json`
- `epc_modules/api/shop_drawing_api.py`
- `epc_modules/www/shop-drawing-register.html`

---

### 4. Shop Drawing Versioning

**Priority:** High
**Status:** Not Found

**Description:**
No Shop Drawing Versioning for tracking drawing revisions.

**Gap:**
- No version tracking in Shop Drawing

**Files to Create:**
- `epc_modules/doctype/Shop Drawing Version/Shop Drawing Version.json`

---

### 5. Work Packages

**Priority:** High
**Status:** Not Found

**Description:**
No Work Package doctype for package-based work management.

**Gap:**
- No `work_package` doctype
- No Work Package API

**Files to Create:**
- `epc_modules/doctype/Work Package/Work Package.json`
- `epc_modules/doctype/Work Package Item/Work Package Item.json`
- `epc_modules/api/work_package_api.py`
- `epc_modules/www/work-package.html`

---

### 6. Gate Passes

**Priority:** High
**Status:** Not Found

**Description:**
No Gate Pass doctype for material movement control.

**Gap:**
- No `gate_pass` doctype
- No Gate Pass API

**Files to Create:**
- `epc_modules/doctype/Gate Pass/Gate Pass.json`
- `epc_modules/doctype/Gate Pass Item/Gate Pass Item.json`
- `epc_modules/api/gate_pass_api.py`
- `epc_modules/www/gate-pass.html`

---

### 7. Item Requests

**Priority:** High
**Status:** Not Found

**Description:**
No Item Request doctype for requesting materials/items.

**Gap:**
- No `item_request` doctype
- No Item Request API

**Files to Create:**
- `epc_modules/doctype/Item Request/Item Request.json`
- `epc_modules/doctype/Item Request Item/Item Request Item.json`
- `epc_modules/api/item_request_api.py`
- `epc_modules/www/item-request.html`

---

### 8. Operations Teams

**Priority:** High
**Status:** Not Found

**Description:**
No Operations Teams doctype for team management.

**Gap:**
- No `operations_team` doctype
- No `Team Member` doctype (only design_phase_team exists)

**Files to Create:**
- `epc_modules/doctype/Operations Team/Operations Team.json`
- `epc_modules/doctype/Operations Team Member/Operations Team Member.json`
- `epc_modules/api/operations_team_api.py`

---

### 9. Waste Management

**Priority:** Medium
**Status:** Not Found

**Description:**
No Waste Management doctype for construction waste tracking.

**Gap:**
- No `waste_management` doctype
- No Waste Management API

**Files to Create:**
- `epc_modules/doctype/Waste Management/Waste Management.json`
- `epc_modules/api/waste_management_api.py`
- `epc_modules/www/waste-management.html`

---

### 10. Stock Picking Integration

**Priority:** Medium
**Status:** Not Found

**Description:**
No Stock Picking doctype for inventory integration.

**Gap:**
- No `stock_picking` doctype
- No Stock Picking API

**Files to Create:**
- `epc_modules/doctype/Stock Picking/Stock Picking.json`
- `epc_modules/doctype/Stock Picking Item/Stock Picking Item.json`
- `epc_modules/api/stock_picking_api.py`

---

### 11. Work Package Reports

**Priority:** Medium
**Status:** Not Found

**Description:**
No dedicated Work Package report generation.

**Gap:**
- No work package reporting API
- No Work Package report UI

**Files to Create:**
- `epc_modules/www/work-package-report.html`
- `epc_modules/api/work_package_report_api.py`

---

### 12. Item Request Reports

**Priority:** Medium
**Status:** Not Found

**Description:**
No dedicated Item Request report generation.

**Gap:**
- No item request reporting API
- No Item Request report UI

**Files to Create:**
- `epc_modules/www/item-request-report.html`
- `epc_modules/api/item_request_report_api.py`

---

### 13. Gate Pass Reports

**Priority:** Medium
**Status:** Not Found

**Description:**
No dedicated Gate Pass report generation.

**Gap:**
- No gate pass reporting API
- No Gate Pass report UI

**Files to Create:**
- `epc_modules/www/gate-pass-report.html`
- `epc_modules/api/gate_pass_report_api.py`

---

### 14. Transmittal Lines (Enhancement from Partial)

**Status:** Missing

**Description:**
Transmittals have API but no DocType definition.

**Files to Create:**
- `epc_modules/doctype/Submittal/Submittal.json`
- `epc_modules/doctype/Submittal Item/Submittal Item.json`

---

## Site Operations Implementation Priority

### High
1. RFI Types Configuration
2. Site Instructions
3. Shop Drawing Register
4. Shop Drawing Versioning
5. Work Packages
6. Gate Passes
7. Item Requests
8. Operations Teams

### Medium
1. Waste Management
2. Stock Picking Integration
3. Work Package Reports
4. Item Request Reports
5. Gate Pass Reports
6. Transmittal Lines (from Partial)

### Low
1. RFI Reports (enhancement)
2. Inspection Reports (enhancement)
3. NCR Reports (enhancement)
4. Daily Log Reports (enhancement)
5. Transmittal Reports (enhancement)

---

## Finance & Billing Modules (Audit 2026-05-19)

### Summary

| Status | Count |
|--------|-------|
| Fully Implemented | 1 |
| Partial | 2 |
| Missing | 3 |

---

### Fully Implemented

### 1. Progress Billing

**Status:** Fully Implemented

**Existing Files:**
- `epc_modules/doctype/RA Bill/RA Bill.json`
- `epc_modules/doctype/RA Bill MB Reference/`
- `epc_modules/doctype/Measurement Book/`
- `epc_modules/doctype/Project Milestone/`
- `epc_modules/api/billing_api.py` (17 API endpoints)
- `epc_modules/utils/billing_calculator.py` (RABillingCalculator, MilestoneBillingCalculator, BillingEngine)
- `epc_modules/fixtures/dashboard_charts.json` (billing charts)

**Workflow:** Draft → Submitted → Under Review → Certified → Invoiced → Paid

---

### Partial Implementations

### 1. Budget Management

**Status:** Partial

**Existing Files:**
- `epc_modules/utils/billing_calculator.py` (get_billing_summary with budget info)
- `epc_modules/api/dashboard_api.py` (billing_summary in project KPIs)

**Gap:**
- No dedicated Budget doctype
- No budget web pages

**Files to Create:**
- `epc_modules/doctype/Budget/Budget.json`
- `epc_modules/doctype/Budget Item/Budget Item.json`
- `epc_modules/www/budget-management.html`

---

### 2. Financial Reports

**Status:** Partial

**Existing Files:**
- `epc_modules/fixtures/dashboard_charts.json` (Billing by Typology, Monthly Billing Trend)
- `epc_modules/api/dashboard_api.py` (get_billing_trend, get_management_dashboard)
- `epc_modules/utils/billing_calculator.py` (BillingEngine for summaries)
- `epc_modules/www/epc-dashboard.html`, `epc-modules/www/epc-project-dashboard.html`

**Gap:**
- No dedicated Financial Report wizard
- No S-curve or variance reports

**Files to Create:**
- `epc_modules/doctype/Financial Report/Financial Report.json`
- `epc_modules/www/financial-report.html`

---

### Missing Features

### 1. Estimates

**Priority:** High
**Status:** Not Found

**Description:**
No dedicated Estimate or Cost Estimate doctype.

**Gap:**
- No estimate-related files
- Custom BOQ exists but is not an Estimate module

**Files to Create:**
- `epc_modules/doctype/Estimate/Estimate.json`
- `epc_modules/doctype/Estimate Item/Estimate Item.json`
- `epc_modules/api/estimate_api.py`
- `epc_modules/www/estimate.html`

---

### 2. Change Orders

**Priority:** High
**Status:** Not Found

**Description:**
No Change Order or Contract Amendment doctype.

**Gap:**
- No change order files
- Claim Register exists but is for claims, not change orders

**Files to Create:**
- `epc_modules/doctype/Change Order/Change Order.json`
- `epc_modules/doctype/Change Order Item/Change Order Item.json`
- `epc_modules/api/change_order_api.py`
- `epc_modules/www/change-order.html`

---

### 3. Estimate Reports

**Priority:** Medium
**Status:** Not Found

**Description:**
No dedicated Estimate report generation.

**Gap:**
- No estimate report API
- No estimate report UI

**Files to Create:**
- `epc_modules/www/estimate-report.html`
- `epc_modules/api/estimate_report_api.py`

---

## Finance & Billing Implementation Priority

### High
1. Estimates
2. Change Orders

### Medium
1. Financial Reports (enhancement)
2. Estimate Reports

### Low
1. Budget Management (enhancement)

---

## HSE & Safety Modules (Audit 2026-05-19)

### Summary

| Status | Count |
|--------|-------|
| Fully Implemented | 0 |
| Partial | 2 |
| Missing | 10 |

---

### Partial Implementations

### 1. Risk Register

**Status:** Partial

**Existing Files:**
- `epc_modules/doctype/Risk Register/`
- `epc_modules/doctype/Risk Response Action/`
- `epc_modules/hooks.py` (on_update event handler registered)

**Gap:**
- No API controller for CRUD operations
- No web pages for risk register UI

**Files to Create:**
- `epc_modules/api/risk_register_api.py`
- `epc_modules/www/risk-register.html`

---

### 2. Toolbox Talks

**Status:** Partial

**Existing Files:**
- `epc_modules/api/hse_api.py` (create_toolbox_talk, get_toolbox_talks)

**Gap:**
- No Toolbox Talk Record doctype definition
- No web pages for toolbox talk UI

**Files to Create:**
- `epc_modules/doctype/Toolbox Talk Record/Toolbox Talk Record.json`
- `epc_modules/www/toolbox-talk.html`

---

### Missing Features

### 1. Work Permits

**Priority:** High
**Status:** Not Found

**Files to Create:**
- `epc_modules/doctype/Work Permit/Work Permit.json`
- `epc_modules/doctype/Work Permit Item/Work Permit Item.json`
- `epc_modules/api/work_permit_api.py`
- `epc_modules/www/work-permit.html`

---

### 2. Permit Types Configuration

**Priority:** High
**Status:** Not Found

**Files to Create:**
- `epc_modules/doctype/Permit Type/Permit Type.json`
- `epc_modules/fixtures/permit_type.json`

---

### 3. PPE Types Configuration

**Priority:** High
**Status:** Not Found

**Files to Create:**
- `epc_modules/doctype/PPE Type/PPE Type.json`
- `epc_modules/fixtures/ppe_type.json`

---

### 4. Safety Observations

**Priority:** High
**Status:** Not Found

**Files to Create:**
- `epc_modules/doctype/Safety Observation/Safety Observation.json`
- `epc_modules/api/safety_observation_api.py`

---

### 5. Method Statements

**Priority:** High
**Status:** Not Found

**Files to Create:**
- `epc_modules/doctype/Method Statement/Method Statement.json`
- `epc_modules/api/method_statement_api.py`
- `epc_modules/www/method-statement.html`

---

### 6. Site Attendance

**Priority:** High
**Status:** Not Found

**Files to Create:**
- `epc_modules/doctype/Site Attendance/Site Attendance.json`
- `epc_modules/api/site_attendance_api.py`
- `epc_modules/www/site-attendance.html`

---

### 7. Visitor Management

**Priority:** High
**Status:** Not Found

**Files to Create:**
- `epc_modules/doctype/Visitor/Visitor.json`
- `epc_modules/api/visitor_api.py`
- `epc_modules/www/visitor-management.html`

---

### 8. Attendance Summary Reports

**Priority:** Medium
**Status:** Not Found

**Files to Create:**
- `epc_modules/doctype/Attendance Summary/Attendance Summary.json`
- `epc_modules/api/attendance_summary_api.py`
- `epc_modules/www/attendance-summary-report.html`

---

### 9. Visitor Log Reports

**Priority:** Medium
**Status:** Not Found

**Files to Create:**
- `epc_modules/doctype/Visitor Log/Visitor Log.json`
- `epc_modules/api/visitor_log_api.py`
- `epc_modules/www/visitor-log-report.html`

---

### 10. Automated Cron Jobs (HSE-specific)

**Priority:** Medium
**Status:** Not Found

**Description:**
Existing scheduler has general jobs but no HSE-specific safety jobs.

**Files to Create:**
- `epc_modules/tasks/hse_schedulers.py` (safety inspection reminders, toolbox talk frequency checks, work permit expiry alerts)

---

## HSE & Safety Implementation Priority

### High
1. Work Permits
2. Permit Types Configuration
3. PPE Types Configuration
4. Safety Observations
5. Method Statements
6. Site Attendance
7. Visitor Management

### Medium
1. Attendance Summary Reports
2. Visitor Log Reports
3. Automated Cron Jobs (HSE)

### Low
1. Risk Register (enhancement)
2. Toolbox Talks (enhancement)

---

## Plant, Docs & Contracts Modules (Audit 2026-05-19)

### Summary

| Status | Count |
|--------|-------|
| Fully Implemented | 0 |
| Partial | 5 |
| Missing | 4 |

---

### Partial Implementations

### 1. Equipment Registry

**Status:** Partial

**Existing Files:**
- `epc_modules/doctype/Equipment Register/Equipment Register.json` (30+ fields)

**Gap:**
- No dedicated API file
- No dedicated utility file

**Files to Create:**
- `epc_modules/api/equipment_registry_api.py`
- `epc_modules/utils/equipment_registry.py`

---

### 2. Maintenance Requests

**Status:** Partial

**Existing Files:**
- `epc_modules/doctype/Equipment Maintenance Schedule/Equipment Maintenance Schedule.json`

**Gap:**
- No dedicated maintenance request API

**Files to Create:**
- `epc_modules/doctype/Maintenance Request/Maintenance Request.json`
- `epc_modules/api/maintenance_request_api.py`

---

### 3. Document Register

**Status:** Partial

**Existing Files:**
- `epc_modules/api/document_api.py` (create_project_document, get_project_documents, update_document_status, supersede_document)

**Gap:**
- No dedicated Project Document doctype found
- document_api.py references doctypes not found in doctype directory

**Files to Create:**
- `epc_modules/doctype/Project Document/Project Document.json`
- `epc_modules/doctype/Project Document Item/Project Document Item.json`

---

### 4. Document Templates

**Status:** Partial

**Existing Files:**
- `epc_modules/doctype/Master Inspection Template/Master Inspection Template.json`

**Note:** This is for ITP purposes, not general document templates.

**Gap:**
- No general document template system

**Files to Create:**
- `epc_modules/doctype/Document Template/Document Template.json`
- `epc_modules/api/document_template_api.py`

---

### 5. Subcontractor Contracts

**Status:** Partial

**Existing Files:**
- `epc_modules/doctype/Subcontractor Work Order/Subcontractor Work Order.json`
- `epc_modules/doctype/Subcontractor Profile/Subcontractor Profile.json`

**Gap:**
- No dedicated API for subcontractor work orders

**Files to Create:**
- `epc_modules/api/subcontract_api.py`

---

### 6. Contract Approval Workflow

**Status:** Partial

**Existing Files:**
- `epc_modules/workflows.py` (EPC Project Approval, Measurement Book Approval, RA Bill Approval, NCR Workflow)

**Gap:**
- No specific Contract Approval Workflow for subcontractor work orders

**Files to Create:**
- `epc_modules/doctype/Contract Approval Workflow/Contract Approval Workflow.json`

---

### Missing Features

### 1. Machine Repair Tracking

**Priority:** High
**Status:** Not Found

**Files to Create:**
- `epc_modules/doctype/Machine Repair/Machine Repair.json`
- `epc_modules/doctype/Machine Repair Item/Machine Repair Item.json`
- `epc_modules/api/machine_repair_api.py`

---

### 2. IPC Management

**Priority:** High
**Status:** Not Found

**Description:**
No Inspection and Punch List (IPC) management.

**Files to Create:**
- `epc_modules/doctype/IPC/IPC.json`
- `epc_modules/doctype/IPC Item/IPC Item.json`
- `epc_modules/api/ipc_api.py`
- `epc_modules/www/ipc.html`

---

### 3. Company Contract Limits

**Priority:** Medium
**Status:** Not Found

**Files to Create:**
- `epc_modules/doctype/Company Contract Limit/Company Contract Limit.json`
- `epc_modules/api/contract_limits_api.py`

---

## Plant, Docs & Contracts Implementation Priority

### High
1. Machine Repair Tracking
2. IPC Management

### Medium
1. Company Contract Limits

### Low
1. Equipment Registry (enhancement)
2. Maintenance Requests (enhancement)
3. Document Register (enhancement)
4. Document Templates (enhancement)
5. Subcontractor Contracts (enhancement)
6. Contract Approval Workflow (enhancement)

---

## Overall Summary (All Modules)

| Category | Fully Implemented | Partial | Missing |
|----------|------------------|---------|---------|
| Projects & Core | 4 | 3 | 7 |
| Site Operations | 5 | 6 | 14 |
| Finance & Billing | 1 | 2 | 3 |
| HSE & Safety | 0 | 2 | 10 |
| Plant, Docs & Contracts | 0 | 5 | 4 |
| **Total** | **10** | **18** | **38** |

**Grand Total Features:** 66
- Fully Implemented: 10 (15%)
- Partial: 18 (27%)
- Missing: 38 (58%)