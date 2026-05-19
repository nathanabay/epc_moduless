# Codebase Audit Report: `epc_modules`

**Date**: 2026-05-19
**Auditor**: Claude Code (using Frappe Claude Skill Package)
**Skills Applied**: frappe-agent-architect, frappe-agent-validator, frappe-core-database, frappe-core-api, frappe-syntax-hooks

---

## Executive Summary

| Area | Status | Critical Issues |
|------|--------|-----------------|
| Architecture | Bug | Missing `required_apps`, triply-nested module, duplicate files |
| Hooks/DocEvents | Major Gap | 17 handlers not registered, `frappe.db.commit()` in hook |
| Fixtures | Bug | Missing `dt` field, 20 duplicate definitions |
| Database | Major | Missing transactions, N+1 queries, raw SQL |
| API | Bug | Missing permission checks, no method restrictions |

---

## Skills Reference

| Skill | What Was Audited |
|-------|-----------------|
| `frappe-agent-architect` | App structure, module organization, cross-app patterns, `required_apps` |
| `frappe-agent-validator` | DocType JSON, fixture validation, duplicate field detection |
| `frappe-core-database` | Transaction safety, query patterns, SQL injection, N+1 detection |
| `frappe-core-api` | API security, permission checks, REST patterns, `@frappe.whitelist()` usage |
| `frappe-syntax-hooks` | DocEvents registration, hooks.py compliance, module-level imports |

---

## Architecture (frappe-agent-architect)

### CRITICAL ERRORS

| # | Issue | Fix |
|---|-------|-----|
| 1 | **Missing `required_apps`** — `hooks.py` does not declare `required_apps = ["erpnext"]`. The app extends ERPNext DocTypes (Project, PO, Stock Entry) but doesn't declare the dependency | Add `required_apps = ["erpnext"]` to `hooks.py` |
| 2 | **Triply-nested module directory** — `/epc_modules/epc_modules/epc_modules/` creates anomalous import paths (`epc_modules.epc_modules.epc_modules.utils`) | Remove the nested duplicate at `epc_modules/epc_modules/epc_modules/` |
| 3 | **Duplicate `event_handlers.py`** — Two copies exist at `epc_modules/event_handlers.py` and `epc_modules/epc_modules/epc_modules/event_handlers.py`. Only the first is referenced in hooks | Remove the nested duplicate |
| 4 | **Duplicate `hooks.py` re-export** — `epc_modules/epc_modules/hooks.py` uses `importlib` to re-export from root `hooks.py`, creating circular delegation | Remove the re-export wrapper |

### WARNINGS

| # | Issue | Recommendation |
|---|-------|----------------|
| 1 | Typology type string uses slash — `"Standard/Service"` can cause URL routing issues | Consider `"Standard Service"` for consistency with `"Electromechanical"` and `"Civil"` |
| 2 | `typology_defaults.json` duplicates `custom_field.json` — 20 duplicate field definitions | Deduplicate or remove `typology_defaults.json` |
| 3 | 17 handlers defined in `event_handlers.py` but NOT registered in `hooks.py` doc_events | Register in hooks.py or remove dead code |

---

## Hooks (frappe-syntax-hooks)

### CRITICAL ERRORS

| # | Line | Issue | Fix |
|---|------|-------|-----|
| 1 | `event_handlers.py:76` | **`frappe.db.commit()` inside hook handler** — violates rule "never commit in hook handlers" | Remove. Frappe auto-commits on successful completion |
| 2 | `event_handlers.py:7-9` | **Module-level `import frappe`** — causes circular loading issues | Use lazy/function-level imports |

### WARNINGS

| # | Handler | Doctype | Status |
|---|---------|---------|--------|
| 1 | `on_project_save` | Project after_save | Not registered |
| 2 | `validate_tbe_for_electromechanical` | Purchase Order validate | Not registered |
| 3 | `validate_wbs_completion` | WBS Item validate | Not registered |
| 4 | `on_ncr_status_change` | Non-Conformance Report on_update | Not registered |
| 5 | `validate_concrete_pour` | Daily Progress Report / Concrete Pour Record validate | Not registered |
| 6 | `on_cube_test_submit` | Cube Test Result on_update | Not registered |
| 7 | `on_mix_design_approval` | Concrete Mix Design on_update | Not registered |
| 8 | `on_formwork_inspection_cleared` | Formwork Inspection on_update | Not registered |
| 9 | `on_curing_record_check` | Curing Record validate | Not registered |
| 10 | `on_itp_inspection_record_update` | ITP Inspection Record | Not registered |
| 11 | `on_risk_materialized` | Risk Register on_update | Not registered |
| 12 | `on_equipment_status_change` | Equipment Register on_update | Not registered |
| 13 | `on_maintenance_due` | Equipment Maintenance Schedule on_update | Not registered |
| 14 | `on_hse_incident_reported` | HSE Incident on_update | Not registered |
| 15 | `on_safety_inspection_completed` | Safety Inspection on_update | Not registered |
| 16 | `on_document_review_required` | Project Document on_update | Not registered |
| 17 | `on_rfi_overdue` | RFI on_update | Not registered |
| 18 | `on_subcontractor_insurance_expiry` | Subcontractor Profile on_update | Not registered |

### Items Verified as Correct

- Scheduler events syntax — uses dotted paths correctly
- Fixtures configuration — proper filter syntax
- `permission_query_conditions` — uses dotted path
- `has_web_permission` — uses dotted path
- `get_match_filters` — uses dotted path

---

## Database (frappe-core-database)

### CRITICAL ERRORS

| # | File:Line | Issue | Fix |
|---|-----------|-------|-----|
| 1 | `billing_calculator.py:418-428` | **Multi-doc op without transaction** — `si.insert()` + `si.submit()` then `frappe.db.set_value()` on milestone, no transaction wrapper | Wrap in `frappe.db.savepoint()` + try/except + commit/rollback |
| 2 | `boq_calculator.py:153-159` | **N+1 query** — `frappe.get_all("DPR Line Item", ...)` inside `for item in boq_items:` loop | Fetch all DPR entries upfront with `IN` clause, group in Python |
| 3 | `billing_calculator.py:226-230` | **Raw SQL with `%s` tuple params** — inconsistent with frappe.qb patterns | Use `frappe.qb` or `frappe.db.get_value` |
| 4 | `wbs_generator.py:246` | **Insert without transaction** — `doc.insert(ignore_permissions=True)` with no rollback protection | Wrap in transaction |

### WARNINGS

| # | File:Line | Issue | Recommendation |
|---|-----------|-------|----------------|
| 1 | `boq_calculator.py:146` | No pagination on `get_all("Custom BOQ")` | Add `page_length=100` limit |
| 2 | `boq_calculator.py:157` | No pagination on `get_all("DPR Line Item")` | Add `page_length` limit |
| 3 | `boq_calculator.py:167,184` | Multiple `frappe.db.set_value` in loop | Batch using `bulk_update` [v15+] |
| 4 | `quality_gate.py:178` | Uses `frappe.db.count()` then compares > 0 | Replace with `frappe.db.exists()` |
| 5 | `quality_gate.py:203` | `frappe.db.set_value` after NCR insert without transaction | Wrap entire NCR creation flow in transaction |
| 6 | `wbs_generator.py:212` | Unguarded `frappe.get_doc()` call — throws if parent not found | Check `frappe.db.exists()` first |
| 7 | `wbs_generator.py:261-266` | `get_all("WBS Item")` for entire project hierarchy without pagination | Add `page_length` for large projects |
| 8 | `billing_calculator.py:411` | `frappe.db.get_value` with `["like", ...]` fuzzy match | Use exact match or cache the VAT account |

---

## API (frappe-core-api)

### CRITICAL ERRORS

| # | File:Line | Issue | Fix |
|---|-----------|-------|-----|
| 1 | `demo_api.py:5` | **Missing permission checks** — `@frappe.whitelist()` creates documents across 9 doctypes without any `frappe.has_permission()` | Add `frappe.has_permission("Project", "create")` before creating |
| 2 | `demo_api.py:5` | **Missing `methods=["POST"]`** — state-changing endpoint accepts GET requests | Change to `@frappe.whitelist(methods=["POST"])` |
| 3 | `demo_api.py:88` | **Bare `except Exception`** — masks programming errors and security issues | Catch specific exceptions or re-raise after logging |

### WARNINGS

| # | File:Line | Issue | Recommendation |
|---|-----------|-------|----------------|
| 1 | `demo_api.py:21,86` | Manual `frappe.db.commit()` calls | Remove — Frappe auto-commits |
| 2 | `demo_api.py:88` | Error returned as dict instead of `frappe.throw()` | Use `frappe.throw()` for consistent API error format |
| 3 | `demo_api.py:5` | No rate limiting | Consider adding rate limiting |

---

## Fixtures (frappe-agent-validator)

### CRITICAL ERRORS

| # | File | Issue | Fix |
|---|------|-------|-----|
| 1 | `typology_defaults.json` | **Missing `dt` (DocType) field** on all 20 custom field entries — fixture installation will fail | Add `"dt": "Project"` or `"dt": "Item"` to each entry |
| 2 | `typology_defaults.json` vs `custom_field.json` | **20 duplicate field definitions** — same fields defined in both files | Remove `typology_defaults.json` entirely OR add missing fields |
| 3 | `project_typology.json` | **Missing `autoname`** — mandatory field for DocType | Add `"autoname": "field:typology_name"` |

### Duplicate Field Definitions

| fieldname | In custom_field.json | In typology_defaults.json | Status |
|-----------|---------------------|-------------------------|--------|
| project_typology | Yes (dt=Project) | Yes (NO dt) | DUPLICATE |
| is_epc_project | Yes (dt=Project) | Yes (NO dt) | DUPLICATE |
| regulatory_context | Yes (dt=Project) | Yes (NO dt) | DUPLICATE |
| vat_registration | Yes (dt=Project) | Yes (NO dt) | DUPLICATE |
| billing_track | Yes (dt=Project) | Yes (NO dt) | DUPLICATE |
| contract_value | Yes (dt=Project) | Yes (NO dt) | DUPLICATE |
| retention_percentage | Yes (dt=Project) | Yes (NO dt) | DUPLICATE |
| advance_recovery_threshold | Yes (dt=Project) | Yes (NO dt) | DUPLICATE |
| is_epc_material | Yes (dt=Item) | Yes (NO dt) | DUPLICATE |
| is_equipment | Yes (dt=Item) | Yes (NO dt) | DUPLICATE |
| equipment_tag | Yes (dt=Item) | Yes (NO dt) | DUPLICATE |
| dashboard_priority | Yes (dt=Project) | Yes (NO dt) | DUPLICATE |
| health_score_override | Yes (dt=Project) | Yes (NO dt) | DUPLICATE |
| dashboard_color | Yes (dt=Project) | Yes (NO dt) | DUPLICATE |
| target_close_date | Yes (dt=Project) | Yes (NO dt) | DUPLICATE |
| overdue_alert_sent | Yes (dt=Project) | Yes (NO dt) | DUPLICATE |
| equipment_status | Yes (dt=Item) | Yes (NO dt) | DUPLICATE |
| current_project | Yes (dt=Item) | Yes (NO dt) | DUPLICATE |
| next_service_date | Yes (dt=Item) | Yes (NO dt) | DUPLICATE |
| equipment_utilization_hours | Yes (dt=Item) | Yes (NO dt) | DUPLICATE |

### WARNINGS

| # | File | Issue | Recommendation |
|---|------|-------|----------------|
| 1 | `typology_defaults.json` | Missing `name` field on all entries | Add unique `name` field |
| 2 | `project_typology.json` | No permissions defined | Add `permissions` array |
| 3 | `form_workflow.json` | RA Bill workflow self-loop transition | Verify if intentional |
| 4 | `form_workflow.json` | NCR `Closed` state has `docstatus: 1` | Verify if should be `docstatus: 2` |

---

## Priority Fix Sequence

| Priority | Issue | Skill Reference |
|----------|-------|-----------------|
| 1 | Remove triply-nested module + duplicate files | frappe-agent-architect |
| 2 | Add `required_apps = ["erpnext"]` | frappe-agent-architect |
| 3 | Fix `typology_defaults.json` missing `dt` field | frappe-agent-validator |
| 4 | Remove duplicate custom field definitions | frappe-agent-validator |
| 5 | Register 17 missing doc_events handlers | frappe-syntax-hooks |
| 6 | Remove `frappe.db.commit()` from hook handler | frappe-syntax-hooks |
| 7 | Fix module-level `import frappe` | frappe-syntax-hooks |
| 8 | Wrap multi-doc ops in `frappe.db.transaction` | frappe-core-database |
| 9 | Fix N+1 query in `boq_calculator.py` | frappe-core-database |
| 10 | Add permission checks to `demo_api.py` | frappe-core-api |
| 11 | Add `methods=["POST"]` to `demo_api.py` | frappe-core-api |
| 12 | Add `autoname` to `project_typology.json` | frappe-agent-validator |

---

## Referenced Skills

- `frappe-agent-architect`: App structure, required_apps, module organization
- `frappe-agent-validator`: DocType JSON validation, fixture validation
- `frappe-core-database`: Transaction patterns, query optimization, SQL injection prevention
- `frappe-core-api`: API security, permission checks, REST patterns
- `frappe-syntax-hooks`: Hooks configuration, doc_events registration