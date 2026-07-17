from app.config import get_settings


def test_model_settings_masks_configured_api_key(client, monkeypatch):
    monkeypatch.setenv("LLM_MODE", "deepseek")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-demo-secret-123456")
    monkeypatch.setenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
    monkeypatch.setenv("DEEPSEEK_MODEL", "deepseek-chat")
    get_settings.cache_clear()

    response = client.get("/api/model-settings")

    assert response.status_code == 200
    payload = response.json()
    assert payload["llm_mode"] == "deepseek"
    assert payload["deepseek_api_key_configured"] is True
    assert payload["deepseek_api_key_masked"] == "sk-****3456"
    assert "sk-demo-secret" not in response.text


def test_deepseek_connection_test_returns_friendly_message_without_key(client):
    response = client.post("/api/model-settings/deepseek/test")

    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is False
    assert payload["mode"] == "offline"
    assert "API Key" in payload["message"]
