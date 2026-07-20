import { useEffect, useState, type FormEvent } from "react";
import { api } from "../../../api/client";
import { DEFAULT_DEEPSEEK_BASE_URL, DEFAULT_DEEPSEEK_MODEL } from "../../../config/modelDefaults";
import type { ModelSettings } from "../components/ModelConfigStrip";

export function useModelSettings(onNotice: (notice: string) => void) {
  const [modelSettings, setModelSettings] = useState<ModelSettings | null>(null);
  const [showModelSettings, setShowModelSettings] = useState(false);
  const [apiKeyInput, setApiKeyInput] = useState("");
  const [modelInput, setModelInput] = useState(DEFAULT_DEEPSEEK_MODEL);

  useEffect(() => {
    api.get<ModelSettings>("/api/model-settings")
      .then((settings) => {
        setModelSettings(settings);
        setModelInput(settings.deepseek_model || DEFAULT_DEEPSEEK_MODEL);
      })
      .catch(() => setModelSettings(null));
  }, []);

  async function saveModelSettings(event: FormEvent) {
    event.preventDefault();
    const settings = await api.post<ModelSettings>("/api/model-settings/deepseek", {
      api_key: apiKeyInput.trim(),
      base_url: modelSettings?.deepseek_base_url || DEFAULT_DEEPSEEK_BASE_URL,
      model: modelInput.trim() || DEFAULT_DEEPSEEK_MODEL
    });
    setModelSettings(settings);
    setApiKeyInput("");
    setShowModelSettings(false);
    onNotice("DeepSeek API Key 已配置，本次本地后端运行生效");
  }

  return {
    modelSettings,
    showModelSettings,
    apiKeyInput,
    modelInput,
    setShowModelSettings,
    setApiKeyInput,
    setModelInput,
    saveModelSettings
  };
}
