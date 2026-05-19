# SQL Issues Found in epc_modules

Generated: 2026-05-12

## Critical DocType and Field Mismatches

### 1. WBS Element → WBS Item
**Problem:** Code references "WBS Element" DocType which does not exist.

**Files Fixed:**
- `epc_modules/epc_modules/epc_modules/utils/wbs_generator.py` - All references
- `epc_modules/epc_modules/epc_modules/api/wbs_api.py` - All references

**Correction:** Changed all "WBS Element" to "WBS Item"

### 2. BOQ Item → Custom BOQ
**Problem:** Code references "BOQ Item" DocType which does not exist. Should be "Custom BOQ".

**Files Fixed:**
- `epc_modules/epc_modules/epc_modules/api/boq_api.py`

**Correction:** Changed all "BOQ Item" references to "Custom BOQ"

### 3. Field: level → wbs_level
**Problem:** Code references "level" field on WBS Item, but field is named "wbs_level".

**Files Fixed:**
- `epc_modules/epc_modules/epc_modules/utils/wbs_generator.py`
- `epc_modules/epc_modules/epc_modules/api/wbs_api.py`

**Correction:** Changed "level" to "wbs_level" in all field lists

### 4. Field: actual_quantity → quantity_executed
**Problem:** DPR API references "actual_quantity" but DPR Entry field is "quantity_executed".

**Files Fixed:**
- `epc_modules/epc_modules/epc_modules/api/dpr_api.py`

**Correction:** Changed "actual_quantity" to "quantity_executed"

### 5. Field: progress_percent → percent_complete
**Problem:** DPR API references "progress_percent" but DPR Entry field is "percent_complete".

**Files Fixed:**
- `epc_modules/epc_modules/epc_modules/api/dpr_api.py`

**Correction:** Changed "progress_percent" to "percent_complete"

## Permission Query Fixes

### 6. project_permission_query - %s Placeholder Error
**Problem:** Function returned SQL with `%s` placeholders which Frappe doesn't parameterize.

**Files Fixed:**
- `epc_modules/epc_modules/event_handlers.py`
- `epc_modules/epc_modules/epc_modules/event_handlers.py`

**Correction:** Use `frappe.db.escape(user)` with `.format()` instead of `%s`

### 7. project_manager Column Doesn't Exist
**Problem:** Permission query referenced `tabProject.project_manager` which doesn't exist in the database.

**Correction:** Changed to EXISTS subquery on `tabProject User` table to check for project team membership.

## Dashboard Fixes

### 8. Dashboard Chart Links Had NULL References
**Problem:** Dashboard fixture used wrong field name ("chart_name" instead of "chart") causing NULL references.

**Files Fixed:**
- `epc_modules/epc_modules/fixtures/dashboards.json`

**Correction:** Changed `"chart_name"` to `"chart"` with actual chart IDs

### 9. Dashboard Charts Not Standard
**Problem:** Charts were not marked as `is_standard: 1` causing validation errors.

**Files Fixed:**
- `epc_modules/epc_modules/fixtures/dashboard_charts.json`

**Correction:** Added `"is_standard": 1` to all chart fixtures

## Scheduler Fixes

### 10. project_manager Field in Scheduler Tasks
**Problem:** Scheduler referenced `project_manager` field which doesn't exist.

**Files Fixed:**
- `epc_modules/epc_modules/tasks/schedulers.py`

**Correction:** Removed `project_manager` from fields list, use `owner` instead
