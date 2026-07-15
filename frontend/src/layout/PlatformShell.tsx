import { NavLink, Outlet } from "react-router-dom";

const workspaceLinks = [
  { to: "/query", icon: "✦", label: "智能问数" },
  { to: "/knowledge", icon: "▤", label: "知识库管理" },
  { to: "/dashboards", icon: "▦", label: "我的仪表盘" },
  { to: "/requirements", icon: "✓", label: "需求映射" }
];

export function PlatformShell() {
  return (
    <div className="app-shell">
      <header className="topbar">
        <div className="brand-mark"><span>G</span><strong>GeniusQ DaaS</strong></div>
        <nav className="product-nav" aria-label="平台模块">
          <span>数据建模</span>
          <span>数据呈现</span>
          <span className="is-active">智慧问数</span>
          <span>数据管理</span>
        </nav>
        <div className="topbar-actions">
          <span className="status-dot" /> 离线演示
          <button type="button" aria-label="帮助">?</button>
          <div className="avatar">实</div>
        </div>
      </header>
      <div className="platform-body">
        <aside className="sidebar">
          <div className="sidebar-title">智慧问数</div>
          <nav aria-label="工作台导航">
            {workspaceLinks.map((item) => (
              <NavLink key={item.to} to={item.to}>
                <span aria-hidden="true">{item.icon}</span>{item.label}
              </NavLink>
            ))}
          </nav>
          <div className="sidebar-footer">
            <small>模型模式</small>
            <strong>LLM_MODE=offline</strong>
          </div>
        </aside>
        <div className="page-canvas">
          <Outlet />
        </div>
      </div>
    </div>
  );
}
