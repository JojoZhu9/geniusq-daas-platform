import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { api } from "../api/client";
import { AnalysisChart } from "../components/AnalysisChart";
import type { Dashboard } from "../types";

export function SharedDashboardPage() {
  const { shareId = "" } = useParams();
  const [dashboard, setDashboard] = useState<Dashboard | null>(null);
  const [error, setError] = useState("");

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
        {dashboard.cards.length ? (
          <div className="shared-dashboard-grid">
            {dashboard.cards.map((card) => (
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
