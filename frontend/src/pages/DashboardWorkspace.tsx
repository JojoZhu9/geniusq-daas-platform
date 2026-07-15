import { useEffect, useState } from "react";
import { api } from "../api/client";
import { RequirementBadge } from "../components/RequirementBadge";
import type { Dashboard, DashboardCard } from "../types";

export function DashboardWorkspace() {
  const [dashboard, setDashboard] = useState<Dashboard | null>(null);
  const [notice, setNotice] = useState("");

  async function load() {
    const dashboards = await api.get<Dashboard[]>("/api/dashboards");
    setDashboard(dashboards[0] ?? null);
  }
  useEffect(() => { void load(); }, []);

  async function create() {
    const next = await api.post<Dashboard>("/api/dashboards", { name: "房价分析看板" });
    setDashboard(next);
  }

  async function resize(card: DashboardCard) {
    if (!dashboard) return;
    const isLarge = card.layout.w >= 9;
    const nextWidth = isLarge ? 6 : 9;
    const next = await api.patch<Dashboard>(`/api/dashboards/${dashboard.id}/layout`, {
      cards: [{
        id: card.id,
        x: Math.min(card.layout.x, 12 - nextWidth),
        y: card.layout.y,
        w: nextWidth,
        h: isLarge ? 4 : 5
      }]
    });
    setDashboard(next);
    setNotice(isLarge ? "已恢复默认尺寸" : "布局已保存");
  }

  async function move(card: DashboardCard) {
    if (!dashboard) return;
    const rightX = Math.max(0, 12 - card.layout.w);
    const next = await api.patch<Dashboard>(`/api/dashboards/${dashboard.id}/layout`, {
      cards: [{ ...card.layout, id: card.id, x: card.layout.x === 0 ? rightX : 0 }]
    });
    setDashboard(next);
    setNotice("布局已保存");
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
      {notice && <div className="inline-alert">{notice}</div>}
      {!dashboard ? (
        <div className="panel dashboard-empty"><div className="empty-illustration">▦</div><h2>还没有仪表盘</h2><p>从智能问数结果添加图表，或先创建一个空白看板。</p><button className="primary-button" type="button" onClick={create}>创建房价分析看板</button></div>
      ) : (
        <>
          <div className="dashboard-summary panel"><div><small>卡片数量</small><strong>{dashboard.cards.length}</strong></div><div><small>布局规格</small><strong>12 列栅格</strong></div><div><small>分享标识</small><strong>{dashboard.share_id.slice(0, 8)}</strong></div><RequirementBadge id="2.6" /></div>
          <div className="dashboard-grid">
            {dashboard.cards.map((card) => (
              <article
                aria-label={`${card.title} 仪表盘卡片`}
                className="dashboard-card panel"
                data-grid-x={card.layout.x}
                data-grid-y={card.layout.y}
                key={card.id}
                style={{
                  gridColumnStart: card.layout.x + 1,
                  gridColumnEnd: `span ${card.layout.w}`,
                  gridRowStart: card.layout.y + 1,
                  gridRowEnd: `span ${card.layout.h}`
                }}
              >
                <div className="card-head"><div><small>{card.chart.type.toUpperCase()} · 智能问数</small><h2>{card.title}</h2></div><span className="drag-handle" aria-label="可移动卡片">⠿</span></div>
                <div className="card-chart-placeholder"><i /><i /><i /><i /><i /><i /></div>
                <div className="card-footer"><span>{card.layout.w} × {card.layout.h}</span><div><button type="button" onClick={() => move(card)}>移动卡片</button><button type="button" onClick={() => resize(card)}>{card.layout.w >= 9 ? "恢复尺寸" : "放大卡片"}</button><button type="button" onClick={() => remove(card)}>移除</button></div></div>
              </article>
            ))}
            {!dashboard.cards.length && <div className="panel dashboard-empty compact"><p>暂无卡片，请从智能问数页将图表加入此看板。</p></div>}
          </div>
        </>
      )}
    </section>
  );
}
