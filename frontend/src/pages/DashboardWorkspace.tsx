import { useEffect, useMemo, useRef, useState, type PointerEvent as ReactPointerEvent } from "react";
import { api } from "../api/client";
import { AnalysisChart } from "../components/AnalysisChart";
import { RequirementBadge } from "../components/RequirementBadge";
import type { Dashboard, DashboardCard } from "../types";
import { dashboardFilterOptions, filterDashboardCards } from "../utils/dashboardFilters";

type LayoutItem = DashboardCard["layout"] & { id: string };

function layoutItem(card: DashboardCard, position: Partial<DashboardCard["layout"]> = {}): LayoutItem {
  return { id: card.id, ...card.layout, ...position };
}

function isLegacySingleColumn(cards: DashboardCard[]) {
  if (cards.length < 2) return false;
  return cards.every((card) => card.layout.x === 0 && card.layout.w === 6);
}

function compactIntoTwoColumns(cards: DashboardCard[]): LayoutItem[] {
  const result: LayoutItem[] = [];
  let y = 0;
  for (let index = 0; index < cards.length; index += 2) {
    const left = cards[index];
    const right = cards[index + 1];
    result.push(layoutItem(left, { x: 0, y }));
    if (right) result.push(layoutItem(right, { x: 6, y }));
    y += Math.max(left.layout.h, right?.layout.h ?? 0);
  }
  return result;
}

function layoutsOverlap(left: DashboardCard["layout"], right: DashboardCard["layout"]) {
  return left.x < right.x + right.w
    && left.x + left.w > right.x
    && left.y < right.y + right.h
    && left.y + left.h > right.y;
}

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
  const targetY = Math.max(0, Math.floor(relativeY / 280) * 4);
  return { ...source.layout, x: targetX, y: targetY };
}

function firstOpenPosition(card: DashboardCard, occupied: LayoutItem[]): LayoutItem {
  const rightX = Math.max(0, 12 - card.layout.w);
  const candidateXs = card.layout.w <= 6 ? [0, 6] : [0, rightX];
  for (let row = 0; row <= occupied.length * 3 + 3; row += 1) {
    for (const x of [...new Set(candidateXs)]) {
      const candidate = layoutItem(card, { x, y: row * 4 });
      if (!occupied.some((item) => layoutsOverlap(candidate, item))) return candidate;
    }
  }
  return layoutItem(card, { x: 0, y: (occupied.length + 1) * 4 });
}

function reflowAroundCard(cards: DashboardCard[], fixed: LayoutItem): LayoutItem[] {
  const occupied = [fixed];
  const remaining = cards
    .filter((card) => card.id !== fixed.id)
    .sort((left, right) => left.layout.y - right.layout.y || left.layout.x - right.layout.x);
  for (const card of remaining) occupied.push(firstOpenPosition(card, occupied));
  return occupied;
}

export function DashboardWorkspace() {
  const [dashboards, setDashboards] = useState<Dashboard[]>([]);
  const [dashboard, setDashboard] = useState<Dashboard | null>(null);
  const [notice, setNotice] = useState("");
  const [draggedCardId, setDraggedCardId] = useState<string | null>(null);
  const [dropTargetId, setDropTargetId] = useState<string | null>(null);
  const [blankDropTarget, setBlankDropTarget] = useState<DashboardCard["layout"] | null>(null);
  const [filters, setFilters] = useState({ year: "", district: "", metric: "" });
  const dragSession = useRef<string | null>(null);
  const gridRef = useRef<HTMLDivElement | null>(null);
  const filterOptions = useMemo(
    () => dashboardFilterOptions(dashboard?.cards ?? []),
    [dashboard]
  );
  const visibleCards = useMemo(
    () => filterDashboardCards(dashboard?.cards ?? [], filters),
    [dashboard, filters]
  );

  async function load() {
    const loadedDashboards = await api.get<Dashboard[]>("/api/dashboards");
    setDashboards(loadedDashboards);
    const loaded = dashboard
      ? loadedDashboards.find((item) => item.id === dashboard.id) ?? loadedDashboards[0] ?? null
      : loadedDashboards[0] ?? null;
    if (loaded && isLegacySingleColumn(loaded.cards)) {
      const compacted = await api.patch<Dashboard>(`/api/dashboards/${loaded.id}/layout`, {
        cards: compactIntoTwoColumns(loaded.cards)
      });
      setDashboard(compacted);
      setNotice("已自动整理为两列");
      return;
    }
    setDashboard(loaded);
  }
  useEffect(() => { void load(); }, []);
  useEffect(() => {
    if (!draggedCardId) return undefined;
    const releaseOutsideGrid = () => finishDrag();
    const previewOutsideGrid = (event: PointerEvent) => previewBlankDropAt(event.clientX, event.clientY, event.target);
    window.addEventListener("pointermove", previewOutsideGrid);
    window.addEventListener("pointerup", releaseOutsideGrid);
    window.addEventListener("pointercancel", releaseOutsideGrid);
    return () => {
      window.removeEventListener("pointermove", previewOutsideGrid);
      window.removeEventListener("pointerup", releaseOutsideGrid);
      window.removeEventListener("pointercancel", releaseOutsideGrid);
    };
  }, [dashboard, draggedCardId]);

  async function create() {
    const next = await api.post<Dashboard>("/api/dashboards", { name: "房价分析看板" });
    setDashboards((items) => [...items, next]);
    setDashboard(next);
  }

  async function resize(card: DashboardCard) {
    if (!dashboard) return;
    const isLarge = card.layout.w >= 9;
    const nextWidth = isLarge ? 6 : 9;
    await saveLayout(reflowAroundCard(dashboard.cards, layoutItem(card, {
      x: Math.min(card.layout.x, 12 - nextWidth),
      y: card.layout.y,
      w: nextWidth,
      h: isLarge ? 4 : 5
    })));
    setNotice(isLarge ? "已恢复默认尺寸" : "布局已保存");
  }

  async function saveLayout(cards: LayoutItem[]) {
    if (!dashboard) return;
    const next = await api.patch<Dashboard>(`/api/dashboards/${dashboard.id}/layout`, { cards });
    setDashboard(next);
    setNotice("布局已保存");
  }

  async function swapCards(source: DashboardCard, target: DashboardCard) {
    await saveLayout([
      layoutItem(source, {
        x: Math.min(target.layout.x, 12 - source.layout.w),
        y: target.layout.y
      }),
      layoutItem(target, {
        x: Math.min(source.layout.x, 12 - target.layout.w),
        y: source.layout.y
      })
    ]);
  }

  function startDrag(event: ReactPointerEvent<HTMLButtonElement>, card: DashboardCard) {
    if (event.button != null && event.button !== 0) return;
    event.preventDefault();
    dragSession.current = card.id;
    setDraggedCardId(card.id);
    setDropTargetId(null);
    setBlankDropTarget(null);
    setNotice("拖到另一张卡片可交换位置，拖到空白区域可移动");
  }

  function finishDrag() {
    dragSession.current = null;
    setDraggedCardId(null);
    setDropTargetId(null);
    setBlankDropTarget(null);
  }

  function markDropTarget(target: DashboardCard) {
    const sourceId = dragSession.current;
    if (sourceId && sourceId !== target.id) {
      setBlankDropTarget(null);
      setDropTargetId(target.id);
    }
  }

  function previewBlankDropAt(clientX: number, clientY: number, target: EventTarget | null) {
    if (!dashboard || !dragSession.current || !gridRef.current) return;
    const eventTarget = target instanceof Element ? target : null;
    if (eventTarget?.closest("[data-dashboard-card-id]")) {
      setBlankDropTarget(null);
      return;
    }
    const source = dashboard.cards.find((item) => item.id === dragSession.current);
    if (!source) return;
    const nextTarget = dropTargetFromPointer(source, gridRef.current.getBoundingClientRect(), clientX, clientY);
    const occupant = dashboard.cards.find((item) => item.id !== source.id && layoutsOverlap(nextTarget, item.layout));
    if (occupant) {
      setBlankDropTarget(null);
      return;
    }
    setDropTargetId(null);
    setBlankDropTarget(nextTarget);
  }

  function previewBlankDrop(event: ReactPointerEvent<HTMLDivElement>) {
    previewBlankDropAt(event.clientX, event.clientY, event.target);
  }

  async function dropOnCard(event: ReactPointerEvent<HTMLElement>, target: DashboardCard) {
    event.preventDefault();
    event.stopPropagation();
    if (!dashboard) return;
    const sourceId = dragSession.current || draggedCardId;
    const source = dashboard.cards.find((item) => item.id === sourceId);
    finishDrag();
    if (!source || source.id === target.id) return;
    await swapCards(source, target);
  }

  async function dropOnGrid(event: ReactPointerEvent<HTMLDivElement>) {
    if (!dragSession.current) return;
    event.preventDefault();
    if (!dashboard) return;
    const sourceId = dragSession.current || draggedCardId;
    const source = dashboard.cards.find((item) => item.id === sourceId);
    finishDrag();
    if (!source) return;

    const target = dropTargetFromPointer(source, event.currentTarget.getBoundingClientRect(), event.clientX, event.clientY);
    const occupant = dashboard.cards.find((item) => item.id !== source.id && layoutsOverlap(target, item.layout));
    if (occupant) return;
    await saveLayout([layoutItem(source, { x: target.x, y: target.y })]);
  }

  async function remove(card: DashboardCard) {
    if (!dashboard) return;
    await api.delete(`/api/dashboards/${dashboard.id}/cards/${card.id}`);
    setDashboard({ ...dashboard, cards: dashboard.cards.filter((item) => item.id !== card.id) });
    setNotice("卡片已移除");
  }

  async function copyShare() {
    if (!dashboard) return;
    const url = `${window.location.origin}${dashboard.share_url}`;
    if (navigator.clipboard) await navigator.clipboard.writeText(url);
    setNotice("本地分享链接已复制");
  }

  return (
    <section className="page-section dashboard-page">
      <div className="page-heading">
        <div><small>智慧问数 / 我的仪表盘</small><h1>{dashboard?.name ?? "我的仪表盘"}</h1></div>
        <div className="heading-actions"><button type="button" className="secondary-button" onClick={load}>刷新数据</button>{dashboard && <button type="button" className="primary-button" onClick={copyShare}>复制分享链接</button>}</div>
      </div>
      <div className="dashboard-management panel">
        {dashboards.length > 0 && (
          <label>当前仪表盘
            <select
              aria-label="选择仪表盘"
              className="dashboard-selector"
              value={dashboard?.id ?? ""}
              onChange={(event) => setDashboard(dashboards.find((item) => item.id === event.target.value) ?? null)}
            >
              {dashboards.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}
            </select>
          </label>
        )}
        <button type="button" className="secondary-button" onClick={create}>新建仪表盘</button>
      </div>
      {notice && <div className="inline-alert">{notice}</div>}
      {!dashboard ? (
        <div className="panel dashboard-empty"><div className="empty-illustration">▦</div><h2>还没有仪表盘</h2><p>从智能问数结果添加图表，或先创建一个空白看板。</p><button className="primary-button" type="button" onClick={create}>创建房价分析看板</button></div>
      ) : (
        <>
          <div className="dashboard-summary panel"><div><small>卡片数量</small><strong>{dashboard.cards.length}</strong></div><div><small>布局规格</small><strong>两列 · 12 列栅格</strong></div><div><small>分享标识</small><strong>{dashboard.share_id.slice(0, 8)}</strong></div><RequirementBadge id="2.6" /></div>
          <div className="dashboard-filters panel" aria-label="仪表盘筛选器">
            <label>年份
              <select value={filters.year} onChange={(event) => setFilters((value) => ({ ...value, year: event.target.value }))}>
                <option value="">全部年份</option>
                {filterOptions.years.map((year) => <option key={year} value={year}>{year}</option>)}
              </select>
            </label>
            <label>区域
              <select value={filters.district} onChange={(event) => setFilters((value) => ({ ...value, district: event.target.value }))}>
                <option value="">全部区域</option>
                {filterOptions.districts.map((district) => <option key={district} value={district}>{district}</option>)}
              </select>
            </label>
            <label>指标
              <select value={filters.metric} onChange={(event) => setFilters((value) => ({ ...value, metric: event.target.value }))}>
                <option value="">全部指标</option>
                {filterOptions.metrics.map((metric) => <option key={metric} value={metric}>{metric}</option>)}
              </select>
            </label>
          </div>
          <div
            className="dashboard-grid"
            ref={gridRef}
            onPointerMove={previewBlankDrop}
            onPointerUp={(event) => { void dropOnGrid(event); }}
            onPointerCancel={finishDrag}
          >
            {visibleCards.map((card) => (
              <article
                aria-label={`${card.title} 仪表盘卡片`}
                className={`dashboard-card panel${draggedCardId === card.id ? " dragging" : ""}${dropTargetId === card.id ? " drop-target" : ""}`}
                data-grid-x={card.layout.x}
                data-grid-y={card.layout.y}
                data-dashboard-card-id={card.id}
                key={card.id}
                onPointerEnter={() => markDropTarget(card)}
                onPointerLeave={() => { if (dropTargetId === card.id) setDropTargetId(null); }}
                onPointerUp={(event) => { void dropOnCard(event, card); }}
                style={{
                  gridColumnStart: card.layout.x + 1,
                  gridColumnEnd: `span ${card.layout.w}`,
                  gridRowStart: card.layout.y + 1,
                  gridRowEnd: `span ${card.layout.h}`
                }}
              >
                <div className="dashboard-chart-shell">
                  <AnalysisChart chart={{ ...card.chart, title: card.title }} datasets={card.datasets} />
                </div>
                <div className="card-footer">
                  <button
                    type="button"
                    className="drag-handle-button"
                    aria-label={`拖动卡片：${card.title}`}
                    onPointerDown={(event) => startDrag(event, card)}
                  >⠿ 拖动 · {card.layout.w} × {card.layout.h}</button>
                  <div><button type="button" onClick={() => resize(card)}>{card.layout.w >= 9 ? "恢复尺寸" : "放大卡片"}</button><button type="button" onClick={() => remove(card)}>移除</button></div>
                </div>
              </article>
            ))}
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
            {!dashboard.cards.length && <div className="panel dashboard-empty compact"><p>暂无卡片，请从智能问数页将图表加入此看板。</p></div>}
          </div>
        </>
      )}
    </section>
  );
}
