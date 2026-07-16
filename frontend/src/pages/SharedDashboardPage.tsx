import { useEffect, useMemo, useState } from "react";
import { useParams } from "react-router-dom";
import { api } from "../api/client";
import { AnalysisChart } from "../components/AnalysisChart";
import type { Dashboard } from "../types";
import { dashboardFilterOptions, filterDashboardCards } from "../utils/dashboardFilters";

export function SharedDashboardPage() {
  const { shareId = "" } = useParams();
  const [dashboard, setDashboard] = useState<Dashboard | null>(null);
  const [error, setError] = useState("");
  const [filters, setFilters] = useState({ year: "", district: "", metric: "" });
  const filterOptions = useMemo(() => dashboardFilterOptions(dashboard?.cards ?? []), [dashboard]);
  const visibleCards = useMemo(() => filterDashboardCards(dashboard?.cards ?? [], filters), [dashboard, filters]);

  async function loadShare(active = true) {
    try {
      const result = await api.get<Dashboard>(`/api/dashboards/share/${shareId}`);
      if (active) {
        setDashboard(result);
        setError("");
      }
    } catch {
      if (active) setError("分享链接无效或已失效");
    }
  }

  useEffect(() => {
    let active = true;
    api.get<Dashboard>(`/api/dashboards/share/${shareId}`)
      .then((result) => { if (active) setDashboard(result); })
      .catch(() => { if (active) setError("分享链接无效或已失效"); });
    return () => { active = false; };
  }, [shareId]);

  if (error) {
    return <main className="shared-dashboard-page"><section className="shared-state"><strong>无法打开仪表盘</strong><p>{error}</p></section></main>;
  }
  if (!dashboard) {
    return <main className="shared-dashboard-page"><section className="shared-state">正在加载只读仪表盘…</section></main>;
  }

  return (
    <main className="shared-dashboard-page">
      <header className="shared-topbar">
        <div className="brand-mark"><span>G</span><strong>GeniusQ DaaS</strong></div>
        <span className="readonly-chip">只读分享</span>
      </header>
      <section className="shared-dashboard-content">
        <div className="shared-heading">
          <div><small>智慧问数 / 分享仪表盘</small><h1>{dashboard.name}</h1></div>
          <div><small>分享标识</small><strong>{dashboard.share_id}</strong></div>
        </div>
        <button type="button" className="secondary-button" onClick={() => { void loadShare(); }}>刷新数据</button>
        <div className="dashboard-filters panel" aria-label="分享页筛选器">
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
        {dashboard.cards.length ? (
          <div className="shared-dashboard-grid">
            {visibleCards.map((card) => (
              <article
                aria-label={`${card.title} 只读卡片`}
                className="shared-dashboard-card panel"
                key={card.id}
                style={{
                  gridColumnStart: card.layout.x + 1,
                  gridColumnEnd: `span ${card.layout.w}`,
                  gridRowStart: card.layout.y + 1,
                  gridRowEnd: `span ${card.layout.h}`
                }}
              >
                <div className="shared-chart-shell">
                  <AnalysisChart chart={{ ...card.chart, title: card.title }} datasets={card.datasets} />
                </div>
                <div className="shared-card-meta">只读视图 · 来源分析 {card.analysis_id.slice(0, 8)}</div>
              </article>
            ))}
          </div>
        ) : (
          <section className="shared-state">该仪表盘暂无卡片</section>
        )}
        <p className="shared-footnote">本页面为本地 Demo 只读分享视图，可切换折线、柱状和表格，不提供移动、缩放或删除操作。</p>
      </section>
    </main>
  );
}
