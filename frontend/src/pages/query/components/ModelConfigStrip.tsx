import type { FormEvent } from "react";

export type ModelSettings = {
  llm_mode: string;
  deepseek_base_url: string;
  deepseek_model: string;
  deepseek_api_key_configured: boolean;
};

type ModelConfigStripProps = {
  modelSettings: ModelSettings | null;
  showModelSettings: boolean;
  apiKeyInput: string;
  modelInput: string;
  onOpen: () => void;
  onCancel: () => void;
  onApiKeyChange: (value: string) => void;
  onModelChange: (value: string) => void;
  onSave: (event: FormEvent) => void;
};

export function ModelConfigStrip({
  modelSettings,
  showModelSettings,
  apiKeyInput,
  modelInput,
  onOpen,
  onCancel,
  onApiKeyChange,
  onModelChange,
  onSave,
}: ModelConfigStripProps) {
  return (
    <>
      <div className="model-config-strip panel">
        <span className={`offline-chip ${modelSettings?.llm_mode === "deepseek" ? "online" : ""}`}>
          <i />{modelSettings?.llm_mode === "deepseek" ? "DeepSeek 已启用" : "离线规则引擎"}
        </span>
        <button className="secondary-button" type="button" onClick={onOpen}>配置 DeepSeek API</button>
        <small>{modelSettings?.deepseek_api_key_configured ? "API Key 已配置，可覆盖更新" : "未配置 API Key 时使用离线演示规则"}</small>
      </div>
      {showModelSettings && (
        <div className="model-settings-panel panel" role="dialog" aria-label="DeepSeek API 配置">
          <div>
            <strong>DeepSeek API 配置</strong>
            <p>给演示平台填入 API Key 后，本次本地后端会切换到真实 DeepSeek Text-to-SQL。Key 不会显示在页面，也不会写入仓库。</p>
          </div>
          <form onSubmit={onSave}>
            <label>
              API Key
              <input
                aria-label="DeepSeek API Key"
                type="password"
                value={apiKeyInput}
                onChange={(event) => onApiKeyChange(event.target.value)}
                placeholder={modelSettings?.deepseek_api_key_configured ? "已配置，可输入新 Key 覆盖" : "sk-..."}
                required={!modelSettings?.deepseek_api_key_configured}
              />
            </label>
            <label>
              模型
              <input
                aria-label="DeepSeek 模型"
                value={modelInput}
                onChange={(event) => onModelChange(event.target.value)}
                placeholder="deepseek-v4-flash"
              />
            </label>
            <div>
              <button className="secondary-button" type="button" onClick={onCancel}>取消</button>
              <button className="primary-button" type="submit" disabled={!apiKeyInput.trim()}>保存配置</button>
            </div>
          </form>
        </div>
      )}
    </>
  );
}

