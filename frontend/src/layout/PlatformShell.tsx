import { useEffect, useState } from "react";
import { NavLink, Outlet } from "react-router-dom";
import { api } from "../api/client";

const workspaceLinks = [
  { to: "/query", icon: "✦", label: "智能问数" },
  { to: "/knowledge", icon: "▤", label: "知识库管理" },
  { to: "/dashboards", icon: "▦", label: "我的仪表盘" }
];

type ModelSettings = {
  llm_mode: string;
  deepseek_api_key_configured: boolean;
};

function modeText(settings: ModelSettings | null) {
  if (!settings) return "模型模式检测中";
  if (settings.llm_mode === "deepseek") {
    return settings.deepseek_api_key_configured
      ? "LLM_MODE=deepseek"
      : "LLM_MODE=deepseek（未配置 Key）";
  }
  return `LLM_MODE=${settings.llm_mode || "offline"}`;
}

export function PlatformShell() {
  const [settings, setSettings] = useState<ModelSettings | null>(null);

  useEffect(() => {
    api.get<ModelSettings>("/api/model-settings")
      .then(setSettings)
      .catch(() => setSettings({ llm_mode: "offline", deepseek_api_key_configured: false }));
  }, []);

  return (
    <div className="app-shell">
      <header className="topbar">
        <div className="brand-mark"><span>G</span><strong>GeniusQ DaaS</strong></div>
        <nav className="product-nav" aria-label="平台模块">
          <span className="is-active">智慧问数</span>
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
            <strong>{modeText(settings)}</strong>
          </div>
        </aside>
        <div className="page-canvas">
          <Outlet />
        </div>
      </div>
    </div>
  );
}
