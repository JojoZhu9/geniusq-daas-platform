# Chart, Dashboard Movement, and Share Fixes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make requirement 2.4-a render genuinely different line/bar charts and make requirement 2.6 provide visible persisted movement plus a working read-only share URL.

**Architecture:** Use the existing ECharts dependency with its SVG renderer inside `AnalysisChart`, map persisted dashboard coordinates directly to CSS Grid, and add a public React route that consumes the existing share API. No backend schema or endpoint changes are required.

**Tech Stack:** React 18, TypeScript 5.9, ECharts 5.6, React Router 6, Vitest/Testing Library, Playwright, FastAPI/SQLite.

## Global Constraints

- Preserve offline operation and the existing `ChartSpec`, `Dashboard`, and REST API contracts.
- Do not introduce new npm dependencies.
- Use test-first red-green cycles for each repaired behavior.
- Keep the public share page read-only; do not add production authentication semantics to the local Demo.

---

### Task 1: Real ECharts line and bar rendering

**Files:**
- Modify: `frontend/src/components/AnalysisChart.tsx`
- Modify: `frontend/src/styles.css`
- Create: `frontend/src/test/analysis-chart.test.tsx`

**Interfaces:**
- Consumes: `ChartSpec` and `Dataset[]` from `frontend/src/types.ts`.
- Produces: an SVG ECharts view with `role="img"` and `data-chart-type="line|bar"`; the table branch remains an HTML table.

- [ ] **Step 1: Write the failing chart behavior test**

Render `AnalysisChart` with two districts and assert that the initial line control exposes an SVG chart view, then switch to bar and assert the SVG markup and `data-chart-type` change.

- [ ] **Step 2: Run the focused test and verify RED**

Run: `npm.cmd run test:run -- src/test/analysis-chart.test.tsx`

Expected: FAIL because the current chart contains `.bar-track` rows and no ECharts SVG image.

- [ ] **Step 3: Implement the minimal ECharts renderer**

Register ECharts core modules and create options with a real series type:

```ts
series: seriesRows.map(({ name, data }) => ({
  name,
  type,
  data,
  smooth: type === "line",
  showSymbol: type === "line"
}))
```

Initialize with `{ renderer: "svg" }`, set the option, resize on container/window changes, and dispose on cleanup.

- [ ] **Step 4: Run focused and full frontend unit tests**

Run: `npm.cmd run test:run -- src/test/analysis-chart.test.tsx`

Expected: PASS with one real chart test.

- [ ] **Step 5: Commit**

```powershell
git add frontend/src/components/AnalysisChart.tsx frontend/src/styles.css frontend/src/test/analysis-chart.test.tsx
git commit -m "fix: render distinct analytical chart types"
```

### Task 2: Visible persisted dashboard movement

**Files:**
- Modify: `frontend/src/pages/DashboardWorkspace.tsx`
- Modify: `frontend/src/styles.css`
- Modify: `frontend/src/test/dashboard-workspace.test.tsx`

**Interfaces:**
- Consumes: `DashboardCard.layout` with `x`, `y`, `w`, and `h`.
- Produces: card styles where column start is `x + 1`, row start is `y + 1`, and right-edge movement uses `Math.max(0, 12 - w)`.

- [ ] **Step 1: Write the failing movement test**

Click “移动卡片”, return a PATCH response with `x: 6`, and assert the card style changes from grid column start 1 to 7.

- [ ] **Step 2: Run the focused test and verify RED**

Run: `npm.cmd run test:run -- src/test/dashboard-workspace.test.tsx`

Expected: FAIL because the card currently renders only `gridColumn: span 6`.

- [ ] **Step 3: Implement coordinate rendering and safe right-edge movement**

```ts
const rightX = Math.max(0, 12 - card.layout.w);
const nextX = card.layout.x === 0 ? rightX : 0;
```

Map all four layout values to CSS Grid and add an accessible card label.

- [ ] **Step 4: Run the focused test**

Run: `npm.cmd run test:run -- src/test/dashboard-workspace.test.tsx`

Expected: PASS for resize and movement behavior.

- [ ] **Step 5: Commit**

```powershell
git add frontend/src/pages/DashboardWorkspace.tsx frontend/src/styles.css frontend/src/test/dashboard-workspace.test.tsx
git commit -m "fix: render persisted dashboard positions"
```

### Task 3: Working read-only share page

**Files:**
- Create: `frontend/src/pages/SharedDashboardPage.tsx`
- Create: `frontend/src/test/shared-dashboard.test.tsx`
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/styles.css`
- Modify: `docs/需求追踪矩阵.md`
- Modify: `README.md`

**Interfaces:**
- Consumes: route parameter `shareId` and `GET /api/dashboards/share/{shareId}`.
- Produces: `/share/:shareId`, a read-only page containing dashboard name, share ID, and cards with no move/resize/remove controls.

- [ ] **Step 1: Write the failing route/page test**

Render `App` at `/share/share-1`, mock the complete dashboard response, and assert the app requests `/api/dashboards/share/share-1`, renders the title/card, and omits editing buttons.

- [ ] **Step 2: Run the focused test and verify RED**

Run: `npm.cmd run test:run -- src/test/shared-dashboard.test.tsx`

Expected: FAIL because the wildcard route redirects to `/query` and no share API request occurs.

- [ ] **Step 3: Implement the route and page**

Add the route outside `PlatformShell`:

```tsx
<Route path="share/:shareId" element={<SharedDashboardPage />} />
```

Fetch the existing API, show loading/error/empty states, and render read-only card previews.

- [ ] **Step 4: Update manual acceptance documentation and run focused tests**

Run: `npm.cmd run test:run -- src/test/shared-dashboard.test.tsx`

Expected: PASS and no edit controls in the share page.

- [ ] **Step 5: Commit**

```powershell
git add frontend/src/pages/SharedDashboardPage.tsx frontend/src/test/shared-dashboard.test.tsx frontend/src/App.tsx frontend/src/styles.css docs/需求追踪矩阵.md README.md
git commit -m "fix: add read-only dashboard sharing"
```

### Task 4: End-to-end regression and full verification

**Files:**
- Modify: `frontend/e2e/demo.spec.ts`

**Interfaces:**
- Consumes: the repaired line/bar control, dashboard layout, clipboard link, and share route.
- Produces: browser-level regression evidence for 2.4-a and 2.6.

- [ ] **Step 1: Extend the Playwright journey**

Compare the line and bar SVG markup, compare card bounding boxes before/after movement, reload to prove persistence, copy the share URL, open it, and assert the page is read-only.

- [ ] **Step 2: Run the targeted E2E journey and verify it detects the old behavior before the fixes or passes only after all three fixes**

Run: `npm.cmd run e2e -- --grep "问题到图表到仪表盘"`

Expected after implementation: 1 passed.

- [ ] **Step 3: Run complete verification**

```powershell
python -m pytest backend/tests -v --cov=app --cov-report=term-missing
Set-Location frontend
npm.cmd run test:run
npm.cmd run build
npm.cmd run e2e
```

Expected: all backend, frontend, build, and five Playwright journeys pass.

- [ ] **Step 4: Run source and launcher checks**

Run `git diff --check`, parse `start-demo.ps1` with Windows PowerShell, and launch on temporary ports to confirm backend status `ok` and frontend HTTP 200.

- [ ] **Step 5: Commit**

```powershell
git add frontend/e2e/demo.spec.ts
git commit -m "test: verify repaired chart and dashboard journeys"
```
