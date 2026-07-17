from fastapi.testclient import TestClient

from app.config import get_settings
from app.main import app


def test_model_settings_hide_api_key_and_default_to_offline():
    response = TestClient(app).get("/api/model-settings")

    assert response.status_code == 200
    payload = response.json()
    assert payload["llm_mode"] == "offline"
    assert payload["deepseek_base_url"] == "https://api.deepseek.com"
    assert payload["deepseek_model"] == "deepseek-v4-flash"
    assert payload["deepseek_api_key_configured"] is False
    assert payload["deepseek_api_key_masked"] == ""


def test_runtime_deepseek_settings_are_applied_without_echoing_secret(monkeypatch):
    response = TestClient(app).post(
        "/api/model-settings/deepseek",
        json={
            "api_key": "sk-test-secret",
            "base_url": "https://api.deepseek.com",
            "model": "deepseek-v4-flash",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["llm_mode"] == "deepseek"
    assert payload["deepseek_base_url"] == "https://api.deepseek.com"
    assert payload["deepseek_model"] == "deepseek-v4-flash"
    assert payload["deepseek_api_key_configured"] is True
    assert payload["deepseek_api_key_masked"] == "sk-****cret"
    assert "sk-test-secret" not in response.text
    assert get_settings().llm_mode == "deepseek"

    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    monkeypatch.setenv("LLM_MODE", "offline")
    get_settings.cache_clear()
