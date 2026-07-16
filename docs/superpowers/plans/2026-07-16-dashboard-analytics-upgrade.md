# Dashboard Analytics Upgrade Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Upgrade the demo from basic charts to a lightweight analysis dashboard with richer chart types, chart recommendation metadata, dashboard filters, multiple-dashboard management, and an enhanced read-only share page.

**Architecture:** Keep the current FastAPI + SQLite + React shape. Extend the existing `ChartSpec` and frontend chart renderer, then add dashboard-only client-side filtering so saved card datasets can be sliced without re-running SQL or calling DeepSeek.

**Tech Stack:** FastAPI, Pydantic, SQLite, React, TypeScript, ECharts, Vitest, Pytest.

## Global Constraints

- Do not call real DeepSeek from automated tests.
- Keep saved dashboard cards compatible with existing data.
- Dashboard filters operate on saved card datasets first; no SQL refresh in this stage.
- Do not add PNG/PDF export, multi-chart brushing, or full heatmap data modeling in this stage.

---

### Task 1: Chart Spec and Renderer Upgrade

**Files:**
- Modify: `backend/app/schemas.py`
- Modify: `backend/app/services/text_to_sql.py`
- Modify: `frontend/src/types.ts`
- Modify: `frontend/src/components/AnalysisChart.tsx`
- Test: `frontend/src/test/analysis-chart.test.tsx`
- Test: `backend/tests/test_text_to_sql.py`

**Interfaces:**
- Produces: `ChartSpec.type` supports `line | bar | pie | table | scatter | stacked_bar`.
- Produces: optional chart metadata fields `x_axis_name`, `y_axis_name`, `unit`, `series_mode`, `recommended_reason`.

- [ ] Write failing tests for pie, scatter, and stacked bar rendering.
- [ ] Write failing backend parser test that accepts `scatter` chart suggestions and metadata.
- [ ] Extend schemas and frontend types.
- [ ] Register required ECharts chart modules and map the new chart types.
- [ ] Run targeted tests.

### Task 2: Auto Chart Recommendation Metadata

**Files:**
- Modify: `backend/app/services/conversation.py`
- Modify: `backend/app/services/analysis.py`
- Test: `backend/tests/test_deepseek_chat.py`

**Interfaces:**
- Produces: repaired/enriched chart specs with title, axis names, unit, and `recommended_reason`.

- [ ] Write failing tests that a time-series chart receives axis/unit/reason metadata.
- [ ] Add deterministic metadata enrichment after chart repair.
- [ ] Keep model-supplied chart suggestions but fill missing metadata from datasets.
- [ ] Run targeted backend tests.

### Task 3: Dashboard Filters

**Files:**
- Modify: `frontend/src/pages/DashboardWorkspace.tsx`
- Create: `frontend/src/utils/dashboardFilters.ts`
- Test: `frontend/src/test/dashboard-workspace.test.tsx`

**Interfaces:**
- Produces: `filterDashboardCards(cards, filters)` that filters saved datasets by `year`, `district`, and metric/y-field.

- [ ] Write failing tests for filtering cards by year and district.
- [ ] Implement pure filter helper.
- [ ] Add dashboard filter controls to the workspace.
- [ ] Apply filters before rendering `AnalysisChart`.
- [ ] Run targeted frontend tests.

### Task 4: Multiple Dashboard Management

**Files:**
- Modify: `frontend/src/pages/DashboardWorkspace.tsx`
- Modify: `backend/app/api/dashboards.py`
- Modify: `backend/app/services/dashboards.py`
- Test: `frontend/src/test/dashboard-workspace.test.tsx`
- Test: `backend/tests/test_dashboards_api.py`

**Interfaces:**
- Produces: front-end dashboard selector and create flow.
- Produces: optional dashboard rename/delete API if not already present.

- [ ] Write failing tests for selecting and creating dashboards.
- [ ] Implement selector and create button.
- [ ] Add rename/delete only if backend support is already straightforward.
- [ ] Run targeted tests.

### Task 5: Share Page Enhancement

**Files:**
- Modify: `frontend/src/pages/SharedDashboardPage.tsx`
- Test: `frontend/src/test/shared-dashboard.test.tsx`

**Interfaces:**
- Produces: read-only share page with dashboard filters, chart type switching, and refresh button.

- [ ] Write failing tests that share page has read-only filters and refresh button.
- [ ] Implement local filters on shared card datasets.
- [ ] Implement refresh by re-fetching `/api/dashboards/share/{shareId}`.
- [ ] Run targeted tests.

### Task 6: Verification and Commit

**Files:**
- No production files expected beyond previous tasks.

- [ ] Run `python -m pytest backend/tests -q --tb=short`.
- [ ] Run `cd frontend; npm.cmd run test:run`.
- [ ] Run `cd frontend; npm.cmd run build`.
- [ ] Commit with message `feat: upgrade dashboard analytics`.
