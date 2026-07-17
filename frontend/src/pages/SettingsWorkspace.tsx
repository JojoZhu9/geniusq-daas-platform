import { FormEvent, useEffect, useState } from "react";
import { api } from "../api/client";
import type { DeepSeekConnectionTest, ModelSettings } from "../types";

export function SettingsWorkspace() {
  const [settings, setSettings] = useState<ModelSettings | null>(null);
  const [apiKey, setApiKey] = useState("");
  const [baseUrl, setBaseUrl] = useState("https://api.deepseek.com");
  const [model, setModel] = useState("deepseek-chat");
  const [notice, setNotice] = useState("");
  const [noticeKind, setNoticeKind] = useState<"success" | "error">("success");
  const [testing, setTesting] = useState(false);

  async function load() {
    const next = await api.get<ModelSettings>("/api/model-settings");
    setSettings(next);
    setBaseUrl(next.deepseek_base_url || "https://api.deepseek.com");
    setModel(next.deepseek_model || "deepseek-chat");
  }

  useEffect(() => { void load(); }, []);

  async function save(event: FormEvent) {
    event.preventDefault();
    const updated = await api.post<ModelSettings>("/api/model-settings/deepseek", {
      api_key: apiKey,
      base_url: baseUrl,
      model
    });
    setSettings(updated);
    setApiKey("");
    setNoticeKind("success");
    setNotice("DeepSeek 配置已更新，后续问数会优先使用在线模型。");
  }

  async function testConnection() {
    setTesting(true);
    try {
      const result = await api.post<DeepSeekConnectionTest>("/api/model-settings/deepseek/test");
      setNoticeKind(result.ok ? "success" : "error");
      setNotice(result.message);
    } finally {
      setTesting(false);
    }
  }

  const isDeepSeek = settings?.llm_mode === "deepseek";

  return (
    <section className="page-section settings-page">
      <div className="page-heading">
        <div>
          <small>智能问数 / 系统运行</small>
          <h1>运行配置</h1>
        </div>
      </div>

      {notice && <div className={noticeKind === "error" ? "inline-alert error" : "inline-alert"}>{notice}</div>}

      <div className="settings-grid">
        <article className="panel settings-status-card">
          <div className="panel-header">
            <div>
              <small>当前模式</small>
              <h2>{isDeepSeek ? "DeepSeek 在线模式" : "离线演示模式"}</h2>
            </div>
            <span className={isDeepSeek ? "mode-pill online" : "mode-pill offline"}>
              {settings?.llm_mode ?? "loading"}
            </span>
          </div>
          <dl className="settings-list">
            <div><dt>Base URL</dt><dd>{settings?.deepseek_base_url ?? "—"}</dd></div>
            <div><dt>Model</dt><dd>{settings?.deepseek_model ?? "—"}</dd></div>
            <div>
              <dt>API Key</dt>
              <dd>{settings?.deepseek_api_key_configured ? settings.deepseek_api_key_masked : "未配置"}</dd>
            </div>
          </dl>
          <button className="secondary-button" type="button" onClick={testConnection} disabled={testing}>
            {testing ? "测试中..." : "测试连接"}
          </button>
        </article>

        <form className="panel settings-form" onSubmit={save}>
          <div className="panel-header">
            <div>
              <small>DeepSeek API</small>
              <h2>配置在线 Text-to-SQL 模型</h2>
              <p>API Key 只提交给本地后端运行时使用，页面不会回显完整密钥。</p>
            </div>
          </div>
          <label>
            API Key
            <input
              type="password"
              placeholder="sk-..."
              value={apiKey}
              onChange={(event) => setApiKey(event.target.value)}
              required
            />
          </label>
          <label>
            Base URL
            <input value={baseUrl} onChange={(event) => setBaseUrl(event.target.value)} />
          </label>
          <label>
            Model
            <input value={model} onChange={(event) => setModel(event.target.value)} />
          </label>
          <button className="primary-button" type="submit">保存配置</button>
          <p className="settings-note">如果不配置 DeepSeek，系统仍可使用本地离线规则完成演示。</p>
        </form>
      </div>
    </section>
  );
}
