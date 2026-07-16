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
    assert [step["title"] for step in body["steps"]] == [
        "理解用户问题",
        "合并会话上下文",
        "检索问数知识",
        "选择数据表与字段",
        "调用 DeepSeek 生成 SQL",
        "校验只读 SQL",
        "执行查询并生成图表建议",
    ]
    assert len(body["follow_ups"]) == 3
    assert body["follow_ups"] == [
        "只看海淀区和朝阳区的2025年房价趋势",
        "继续分析2025年房价与成交量的关系",
        "把2025年各区房价趋势保存到仪表盘",
    ]


def test_deepseek_mode_uses_semantic_metric_context(client, monkeypatch):
    _deepseek_env(monkeypatch)

    def fake_generate(self, question, context, knowledge, metrics=None):
        assert metrics
        assert [metric.id for metric in metrics] == ["inventory_pressure"]
        return TextToSqlResult(
            sql=(
                "SELECT p.month, p.district, "
                "ROUND(CAST(p.listing_count AS REAL) / t.transaction_count, 4) AS inventory_pressure "
                "FROM house_price_monthly AS p "
                "JOIN housing_transactions AS t ON p.district = t.district AND p.month = t.month "
                "WHERE p.month LIKE '2025-%' ORDER BY p.month, p.district"
            ),
            reasoning="命中语义指标库存压力，按 listing_count / transaction_count 计算。",
            chart=ChartSpec(
                type="line",
                x_field="month",
                y_fields=["inventory_pressure"],
                title="2025年各区库存压力趋势",
            ),
            confidence=0.9,
            used_knowledge_ids=[item.id for item in knowledge],
        )

    monkeypatch.setattr(text_to_sql.DeepSeekTextToSqlService, "generate", fake_generate)
    conversation_id = client.post("/api/conversations").json()["id"]

    response = client.post(
        "/api/chat",
        json={"conversation_id": conversation_id, "question": "分析2025年各区库存压力趋势"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["datasets"][0]["rows"]
    assert body["chart"]["y_fields"] == ["inventory_pressure"]
    assert body["metadata"]["used_metrics"] == [
        {
            "id": "inventory_pressure",
            "name": "库存压力",
            "formula": "listing_count / transaction_count",
            "fields": ["listing_count", "transaction_count"],
            "tables": ["house_price_monthly", "housing_transactions"],
            "description": "用挂牌量与成交量的比值衡量区域库存压力，比值越高表示去化压力越大。",
        }
    ]


def test_deepseek_mode_repairs_irrelevant_or_invalid_chart_fields(client, monkeypatch):
    _deepseek_env(monkeypatch)

    def fake_generate(self, question, context, knowledge):
        return TextToSqlResult(
            sql=(
                "SELECT month, district, rent_price FROM house_price_monthly "
                "WHERE month LIKE '2025-%' AND district IN ('海淀区', '朝阳区') "
                "ORDER BY month, district"
            ),
            reasoning="用户询问租金趋势，应使用 rent_price。",
            chart=ChartSpec(
                type="line",
                x_field="not_in_result",
                y_fields=["avg_price"],
                title="错误的房价图表",
            ),
            confidence=0.84,
            used_knowledge_ids=[item.id for item in knowledge],
        )

    monkeypatch.setattr(text_to_sql.DeepSeekTextToSqlService, "generate", fake_generate)
    conversation_id = client.post("/api/conversations").json()["id"]

    response = client.post(
        "/api/chat",
        json={"conversation_id": conversation_id, "question": "分析2025年海淀区和朝阳区租金趋势"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["datasets"][0]["fields"] == ["month", "district", "rent_price"]
    assert body["chart"]["x_field"] == "month"
    assert body["chart"]["y_fields"] == ["rent_price"]
    assert body["chart"]["type"] == "line"
    assert body["metadata"]["chart_validation_status"] == "repaired"


def test_deepseek_mode_repairs_sql_after_execution_error(client, monkeypatch):
    _deepseek_env(monkeypatch)

    def fake_generate(self, question, context, knowledge):
        return TextToSqlResult(
            sql=(
                "SELECT month, district, bad_price FROM house_price_monthly "
                "WHERE month LIKE '2025-%' ORDER BY month, district"
            ),
            reasoning="第一次误用了不存在的 bad_price 字段。",
            chart=ChartSpec(type="line", x_field="month", y_fields=["bad_price"], title="错误图表"),
            confidence=0.62,
            used_knowledge_ids=[item.id for item in knowledge],
        )

    def fake_repair(self, question, context, knowledge, failed_sql, error_message, repair_reason):
        assert repair_reason == "execution_error"
        assert "bad_price" in failed_sql
        return TextToSqlResult(
            sql=(
                "SELECT month, district, avg_price FROM house_price_monthly "
                "WHERE month LIKE '2025-%' ORDER BY month, district"
            ),
            reasoning="已将不存在的 bad_price 修正为 avg_price。",
            chart=ChartSpec(type="line", x_field="month", y_fields=["avg_price"], title="修复后的房价趋势"),
            confidence=0.88,
            used_knowledge_ids=[item.id for item in knowledge],
        )

    monkeypatch.setattr(text_to_sql.DeepSeekTextToSqlService, "generate", fake_generate)
    monkeypatch.setattr(text_to_sql.DeepSeekTextToSqlService, "repair_sql", fake_repair)
    conversation_id = client.post("/api/conversations").json()["id"]

    response = client.post(
        "/api/chat",
        json={"conversation_id": conversation_id, "question": "分析2025年各区房价趋势"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["queries"][0]["sql"].startswith("SELECT month, district, avg_price")
    assert body["datasets"][0]["rows"]
    assert body["chart"]["y_fields"] == ["avg_price"]
    assert body["metadata"]["sql_repair_status"] == "repaired"
    assert body["metadata"]["sql_repair_attempts"][0]["reason"] == "execution_error"


def test_deepseek_mode_retries_when_sql_returns_empty_rows(client, monkeypatch):
    _deepseek_env(monkeypatch)

    def fake_generate(self, question, context, knowledge):
        return TextToSqlResult(
            sql=(
                "SELECT month, district, avg_price FROM house_price_monthly "
                "WHERE month LIKE '2025-%' AND district = '不存在区域'"
            ),
            reasoning="第一次条件过窄。",
            chart=ChartSpec(type="line", x_field="month", y_fields=["avg_price"], title="空结果图表"),
            confidence=0.67,
            used_knowledge_ids=[item.id for item in knowledge],
        )

    def fake_repair(self, question, context, knowledge, failed_sql, error_message, repair_reason):
        assert repair_reason == "empty_result"
        return TextToSqlResult(
            sql=(
                "SELECT month, district, avg_price FROM house_price_monthly "
                "WHERE month LIKE '2025-%' ORDER BY month, district"
            ),
            reasoning="已移除不存在的区域条件以放宽查询范围。",
            chart=ChartSpec(type="line", x_field="month", y_fields=["avg_price"], title="放宽后的房价趋势"),
            confidence=0.86,
            used_knowledge_ids=[item.id for item in knowledge],
        )

    monkeypatch.setattr(text_to_sql.DeepSeekTextToSqlService, "generate", fake_generate)
    monkeypatch.setattr(text_to_sql.DeepSeekTextToSqlService, "repair_sql", fake_repair)
    conversation_id = client.post("/api/conversations").json()["id"]

    response = client.post(
        "/api/chat",
        json={"conversation_id": conversation_id, "question": "分析2025年不存在区域房价趋势"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["datasets"][0]["rows"]
    assert "不存在区域" not in body["queries"][0]["sql"]
    assert body["metadata"]["sql_repair_status"] == "empty_result_retried"
    assert body["metadata"]["sql_repair_attempts"][0]["reason"] == "empty_result"


def test_deepseek_mode_simple_question_returns_three_recommendations_without_model_call(client, monkeypatch):
    _deepseek_env(monkeypatch)

    def fail_generate(self, question, context, knowledge):
        raise AssertionError("simple questions should not call DeepSeek")

    monkeypatch.setattr(text_to_sql.DeepSeekTextToSqlService, "generate", fail_generate)
    conversation_id = client.post("/api/conversations").json()["id"]

    response = client.post(
        "/api/chat",
        json={"conversation_id": conversation_id, "question": "房价"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "needs_clarification"
    assert body["metadata"]["intent"] == "simple_question_recommendation"
    assert body["queries"] == []
    assert len(body["suggestions"]) == 3
    assert body["suggestions"] == [
        "分析2025年各区房价趋势",
        "对比2024年和2025年各区房价涨幅",
        "分析2025年房价与成交量的关系",
    ]


def test_deepseek_mode_repeated_simple_questions_do_not_repeat_recommendations(client, monkeypatch):
    _deepseek_env(monkeypatch)

    def fail_generate(self, question, context, knowledge):
        raise AssertionError("simple questions should not call DeepSeek")

    monkeypatch.setattr(text_to_sql.DeepSeekTextToSqlService, "generate", fail_generate)
    conversation_id = client.post("/api/conversations").json()["id"]

    first = client.post(
        "/api/chat",
        json={"conversation_id": conversation_id, "question": "房价"},
    ).json()
    second = client.post(
        "/api/chat",
        json={"conversation_id": conversation_id, "question": "房价"},
    ).json()

    assert len(first["suggestions"]) == 3
    assert len(second["suggestions"]) == 3
    assert set(first["suggestions"]).isdisjoint(second["suggestions"])


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
