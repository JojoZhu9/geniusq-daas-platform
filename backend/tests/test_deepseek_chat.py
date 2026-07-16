from app.config import get_settings
from app.schemas import ChartSpec, TextToSqlResult
from app.services import text_to_sql
import pytest


@pytest.fixture(autouse=True)
def clear_settings_cache_between_tests():
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def _deepseek_env(monkeypatch, api_key="test-key"):
    monkeypatch.setenv("LLM_MODE", "deepseek")
    if api_key:
        monkeypatch.setenv("DEEPSEEK_API_KEY", api_key)
    else:
        monkeypatch.setenv("DEEPSEEK_API_KEY", "")
    monkeypatch.setenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
    monkeypatch.setenv("DEEPSEEK_MODEL", "deepseek-v4-flash")
    get_settings.cache_clear()


def test_deepseek_mode_requires_api_key(client, monkeypatch):
    _deepseek_env(monkeypatch, api_key="")
    conversation_id = client.post("/api/conversations").json()["id"]

    response = client.post(
        "/api/chat",
        json={"conversation_id": conversation_id, "question": "分析2025年各区房价趋势"},
    )

    assert response.status_code == 503
    assert response.json()["code"] == "DEEPSEEK_API_KEY_MISSING"
    assert response.json()["action"] == "请在 .env 中配置 DEEPSEEK_API_KEY，或切换 LLM_MODE=offline"


def test_deepseek_mode_executes_safe_generated_sql(client, monkeypatch):
    _deepseek_env(monkeypatch)

    def fake_generate(self, question, context, knowledge):
        return TextToSqlResult(
            sql=(
                "SELECT month, district, avg_price FROM house_price_monthly "
                "WHERE month LIKE '2025-%' ORDER BY month, district"
            ),
            reasoning="使用房价月度表生成趋势查询",
            chart=ChartSpec(
                type="line",
                x_field="month",
                y_fields=["avg_price"],
                title="2025年各区房价趋势",
            ),
            confidence=0.81,
            used_knowledge_ids=[item.id for item in knowledge],
        )

    monkeypatch.setattr(text_to_sql.DeepSeekTextToSqlService, "generate", fake_generate)
    conversation_id = client.post("/api/conversations").json()["id"]

    response = client.post(
        "/api/chat",
        json={"conversation_id": conversation_id, "question": "分析2025年各区房价趋势"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "completed"
    assert body["metadata"]["mode"] == "deepseek"
    assert body["metadata"]["model_reasoning"] == "使用房价月度表生成趋势查询"
    assert body["metadata"]["confidence"] == 0.81
    assert body["metadata"]["sql_validation_status"] == "passed"
    assert body["metadata"]["used_knowledge"][0]["id"] == "knowledge-private-house-price"
    assert body["datasets"][0]["rows"]


def test_deepseek_mode_rejects_dangerous_sql(client, monkeypatch):
    _deepseek_env(monkeypatch)

    def fake_generate(self, question, context, knowledge):
        return TextToSqlResult(
            sql="DELETE FROM house_price_monthly",
            reasoning="危险 SQL",
            confidence=0.4,
            used_knowledge_ids=[item.id for item in knowledge],
        )

    monkeypatch.setattr(text_to_sql.DeepSeekTextToSqlService, "generate", fake_generate)
    conversation_id = client.post("/api/conversations").json()["id"]

    response = client.post(
        "/api/chat",
        json={"conversation_id": conversation_id, "question": "删除房价数据"},
    )

    assert response.status_code == 422
    assert response.json()["code"] == "SQL_REJECTED"
    assert "已阻止执行" in response.json()["message"]


def test_feedback_can_save_analysis_as_sql_knowledge(client, monkeypatch):
    _deepseek_env(monkeypatch)

    def fake_generate(self, question, context, knowledge):
        return TextToSqlResult(
            sql="SELECT month, district, avg_price FROM house_price_monthly WHERE month LIKE '2025-%'",
            reasoning="可沉淀为示例",
            chart=ChartSpec(
                type="line",
                x_field="month",
                y_fields=["avg_price"],
                title="2025年各区房价趋势",
            ),
            confidence=0.9,
            used_knowledge_ids=[item.id for item in knowledge],
        )

    monkeypatch.setattr(text_to_sql.DeepSeekTextToSqlService, "generate", fake_generate)
    conversation_id = client.post("/api/conversations").json()["id"]
    analysis = client.post(
        "/api/chat",
        json={"conversation_id": conversation_id, "question": "分析2025年各区房价趋势"},
    ).json()

    response = client.post(
        f"/api/analysis/{analysis['analysis_id']}/feedback",
        json={
            "rating": "correct",
            "comment": "SQL 正确，可作为示例",
            "save_as_example": True,
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["rating"] == "correct"
    assert body["saved_knowledge_id"]
    knowledge = client.get("/api/knowledge", params={"kind": "sql"}).json()
    assert any(item["id"] == body["saved_knowledge_id"] for item in knowledge)
