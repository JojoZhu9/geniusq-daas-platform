import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { api } from "../api/client";
import type { ChartSpec, Dashboard } from "../types";

function SharedChartPreview({ chart }: { chart: ChartSpec }) {
  const isLine = chart.type === "line";
  return (
    <div className="shared-chart-preview">
      <svg viewBox="0 0 600 170" role="img" aria-label={`${chart.title}，只读图表规格预览`}>
        <line x1="42" y1="140" x2="574" y2="140" className="preview-axis" />
        <line x1="42" y1="18" x2="42" y2="140" className="preview-axis" />
        {isLine ? (
          <>
            <polyline points="50,118 145,94 240,103 335,58 430,76 555,32" className="preview-line" />
            {["50,118", "145,94", "240,103", "335,58", "430,76", "555,32"].map((point) => {
              const [cx, cy] = point.split(",");
              return <circle key={point} cx={cx} cy={cy} r="5" className="preview-point" />;
            })}
          </>
        ) : (
          <>
            <rect x="64" y="94" width="54" height="46" className="preview-bar" />
            <rect x="150" y="70" width="54" height="70" className="preview-bar" />
            <rect x="236" y="84" width="54" height="56" className="preview-bar" />
            <rect x="322" y="42" width="54" height="98" className="preview-bar" />
            <rect x="408" y="60" width="54" height="80" className="preview-bar" />
            <rect x="494" y="26" width="54" height="114" className="preview-bar" />
          </>
        )}
      </svg>
      <span>{isLine ? "LINE" : chart.type === "bar" ? "BAR" : chart.type.toUpperCase()}</span>
    </div>
  );
}

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
        <div className="brand-mark"><span>J</span><strong>极智 DAAS</strong></div>
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
                <div className="card-head"><div><small>{card.chart.type.toUpperCase()} · 智能问数</small><h2>{card.title}</h2></div></div>
                <SharedChartPreview chart={card.chart} />
                <div className="shared-card-meta">只读视图 · 来源分析 {card.analysis_id.slice(0, 8)}</div>
              </article>
            ))}
          </div>
        ) : (
          <section className="shared-state">该仪表盘暂无卡片</section>
        )}
        <p className="shared-footnote">本页面为本地 Demo 只读分享视图，不提供移动、缩放或删除操作。</p>
      </section>
    </main>
  );
}
