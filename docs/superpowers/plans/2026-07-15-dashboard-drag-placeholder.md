# Dashboard Drag Placeholder Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove the old move-card button while keeping drag movement, and show a same-size blue dashed placeholder when a dragged dashboard card is over an empty grid area.

**Architecture:** Keep all behavior in `DashboardWorkspace.tsx` because dashboard drag state already lives there. Add a transient blank drop target state `{ x, y, w, h }`, compute preview and final drop coordinates through one helper, and render a pointer-transparent CSS Grid placeholder element.

**Tech Stack:** React + TypeScript, CSS Grid, Vitest + React Testing Library, Playwright.

## Global Constraints

- Work only in `C:\Users\iphon\Documents\智慧足迹-极智DAAS-实习\.worktrees\intelligent-query-demo`.
- Do not modify backend APIs, database schema, or shared dashboard API behavior.
- Preserve existing card swap, resize, remove, refresh, and share behavior.
- Use TDD: write failing tests before production code.
- Do not add new frontend dependencies.

---

### Task 1: Unit-Test Dashboard Drag Placeholder Behavior

**Files:**
- Modify: `frontend/src/test/dashboard-workspace.test.tsx`

**Interfaces:**
- Consumes: existing `DashboardWorkspace` rendered against mocked `/api/dashboards` and `/api/dashboards/d1/layout`.
- Produces: tests requiring no `移动卡片` button, requiring `role="status"` with `aria-label="卡片空白落点"`, and requiring blank drops to persist `{ id, x, y, w, h }`.

- [ ] **Step 1: Replace the old click-to-move test with a failing drag-to-blank test**

Add a test named `previews and saves a blank grid drop target while dragging` that:

```tsx
renderWorkspace(<DashboardWorkspace />);
const handle = await screen.findByRole("button", { name: "拖动卡片：2025年各区平均房价" });
const grid = document.querySelector(".dashboard-grid") as HTMLDivElement;
vi.spyOn(grid, "getBoundingClientRect").mockReturnValue({
  x: 0, y: 0, left: 0, top: 0, right: 1200, bottom: 600, width: 1200, height: 600,
  toJSON: () => ({})
});
fireEvent.pointerDown(handle, { button: 0 });
fireEvent.pointerMove(grid, { clientX: 900, clientY: 80 });
expect(screen.getByRole("status", { name: "卡片空白落点" })).toHaveStyle({
  gridColumnStart: "7",
  gridRowStart: "1"
});
fireEvent.pointerUp(grid, { clientX: 900, clientY: 80 });
await waitFor(() => expect(savedCards).toEqual([{ id: "card-1", x: 6, y: 0, w: 6, h: 4 }]));
```

- [ ] **Step 2: Add a failing assertion that the old button is gone**

In the same dashboard render path, assert:

```tsx
expect(screen.queryByRole("button", { name: "移动卡片" })).not.toBeInTheDocument();
```

- [ ] **Step 3: Add a failing test for card-target priority**

Add a test named `clears the blank placeholder when hovering another card` that starts dragging the left card, previews a blank target, then fires `pointerEnter` on the right card and expects the placeholder to be absent and the right card to have `drop-target`.

- [ ] **Step 4: Run focused unit tests and confirm RED**

Run:

```bash
cd frontend
npm test -- src/test/dashboard-workspace.test.tsx --run
```

Expected: FAIL because `移动卡片` still exists and `卡片空白落点` is not rendered.

### Task 2: Implement Blank Drop Target UI

**Files:**
- Modify: `frontend/src/pages/DashboardWorkspace.tsx`
- Modify: `frontend/src/styles.css`

**Interfaces:**
- Produces: `blankDropTarget: DashboardCard["layout"] | null`.
- Produces: helper `dropTargetFromPointer(source, bounds, clientX, clientY): DashboardCard["layout"]`.
- Produces: placeholder DOM `<div role="status" aria-label="卡片空白落点" className="dashboard-drop-placeholder" />`.

- [ ] **Step 1: Remove the click move function and footer button**

Delete `async function move(card: DashboardCard)` and remove:

```tsx
<button type="button" onClick={() => move(card)}>移动卡片</button>
```

- [ ] **Step 2: Add shared pointer-to-grid calculation**

Add a helper that uses the existing 12-column logic:

```tsx
function dropTargetFromPointer(
  source: DashboardCard,
  bounds: DOMRect,
  clientX: number,
  clientY: number
): DashboardCard["layout"] {
  const relativeX = clientX - bounds.left;
  const relativeY = Math.max(0, clientY - bounds.top);
  const targetX = source.layout.w > 6
    ? (relativeX < bounds.width / 2 ? 0 : 12 - source.layout.w)
    : (relativeX < bounds.width / 2 ? 0 : 6);
  const targetY = Math.max(0, Math.round(relativeY / 280) * 4);
  return { ...source.layout, x: targetX, y: targetY };
}
```

- [ ] **Step 3: Add preview state and event handling**

Add state:

```tsx
const [blankDropTarget, setBlankDropTarget] = useState<DashboardCard["layout"] | null>(null);
```

Update `finishDrag`, `startDrag`, and `markDropTarget` to clear or set state consistently. Add `previewBlankDrop(event)` on the grid `onPointerMove` that renders the placeholder only when the pointer target is not inside `[data-dashboard-card-id]` and the computed target does not overlap another card.

- [ ] **Step 4: Reuse helper in final drop**

Update `dropOnGrid` to call `dropTargetFromPointer(...)`, use `layoutsOverlap(...)` to detect an occupant, and call `saveLayout([layoutItem(source, { x: target.x, y: target.y })])` for blank drops.

- [ ] **Step 5: Render the placeholder**

Inside `.dashboard-grid`, after mapped cards, render:

```tsx
{blankDropTarget && (
  <div
    aria-label="卡片空白落点"
    className="dashboard-drop-placeholder"
    role="status"
    style={{
      gridColumnStart: blankDropTarget.x + 1,
      gridColumnEnd: `span ${blankDropTarget.w}`,
      gridRowStart: blankDropTarget.y + 1,
      gridRowEnd: `span ${blankDropTarget.h}`
    }}
  />
)}
```

- [ ] **Step 6: Style the placeholder**

Add:

```css
.dashboard-drop-placeholder {
  z-index: 1;
  min-height: 100%;
  border: 2px dashed #1682df;
  border-radius: 7px;
  background: rgba(22, 130, 223, .06);
  box-shadow: 0 8px 22px rgba(22, 130, 223, .14);
  pointer-events: none;
}
```

- [ ] **Step 7: Run focused unit tests and confirm GREEN**

Run:

```bash
cd frontend
npm test -- src/test/dashboard-workspace.test.tsx --run
```

Expected: PASS.

### Task 3: Extend E2E Coverage and Verify Locally

**Files:**
- Modify: `frontend/e2e/demo.spec.ts`

**Interfaces:**
- Consumes: visible dashboard page on Playwright dev server.
- Produces: end-to-end evidence that dashboard cards have no move button and blank drag preview appears before drop.

- [ ] **Step 1: Add E2E assertions**

On the dashboard card path, assert:

```ts
await expect(card.getByRole("button", { name: "移动卡片" })).toHaveCount(0);
```

Then drag the card handle into an empty grid row with `page.mouse` and assert:

```ts
await expect(page.getByRole("status", { name: "卡片空白落点" })).toBeVisible();
```

- [ ] **Step 2: Run all frontend verification**

Run:

```bash
cd frontend
npm test -- --run
npm run build
npm run e2e
```

Expected: all commands pass.

- [ ] **Step 3: Manual browser sanity check**

Open `http://127.0.0.1:5173/dashboards` and verify:

- No `移动卡片` button is visible.
- Dragging from the handle over an empty dashboard cell shows a same-size blue dashed placeholder.
- Dragging over another card still shows the solid blue card outline.
- Releasing over a blank cell persists the new card location.

- [ ] **Step 4: Commit**

Run:

```bash
git add frontend/src/pages/DashboardWorkspace.tsx frontend/src/styles.css frontend/src/test/dashboard-workspace.test.tsx frontend/e2e/demo.spec.ts docs/superpowers/plans/2026-07-15-dashboard-drag-placeholder.md
git commit -m "feat: add dashboard blank drop placeholder"
```

