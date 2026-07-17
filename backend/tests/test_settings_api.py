from app.config import get_settings
from app.api import settings as settings_api


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


def test_deepseek_connection_test_uses_configured_api_request(client, monkeypatch):
    captured = {}

    class FakeResponse:
        def raise_for_status(self):
            return None

    class FakeClient:
        def __init__(self, timeout):
            captured["timeout"] = timeout

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, traceback):
            return None

        def post(self, url, headers, json):
            captured["url"] = url
            captured["headers"] = headers
            captured["json"] = json
            return FakeResponse()

    monkeypatch.setenv("LLM_MODE", "deepseek")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-demo-secret")
    monkeypatch.setenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
    monkeypatch.setenv("DEEPSEEK_MODEL", "deepseek-v4-flash")
    get_settings.cache_clear()
    monkeypatch.setattr(settings_api.httpx, "Client", FakeClient)

    response = client.post("/api/model-settings/deepseek/test")

    assert response.status_code == 200
    assert response.json()["ok"] is True
    assert captured["url"] == "https://api.deepseek.com/chat/completions"
    assert captured["headers"]["Authorization"] == "Bearer sk-demo-secret"
    assert captured["json"]["model"] == "deepseek-v4-flash"
