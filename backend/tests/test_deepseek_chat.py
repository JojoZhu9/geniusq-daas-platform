from app.config import get_settings
from app.schemas import ChartSpec, TextToSqlResult
from app.services import text_to_sql
from app.services.text_to_sql import ModelOutputError
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
    assert body["chart"]["x_axis_name"] == "month"
    assert body["chart"]["y_axis_name"] == "avg_price"
    assert body["chart"]["unit"] == "元/平方米"
    assert body["chart"]["recommended_reason"] == "按月份展示趋势，推荐使用折线图。"
    trace_by_key = {step["key"]: step for step in body["steps"]}
    assert trace_by_key["retrieve_knowledge"]["tool"] == "knowledge_retriever"
    assert trace_by_key["retrieve_knowledge"]["tool_label"] == "知识库检索工具"
    assert "检索用户问题相关的知识片段" in trace_by_key["retrieve_knowledge"]["input_summary"]
    assert any("命中" in item for item in trace_by_key["retrieve_knowledge"]["output_summary"])
    assert trace_by_key["retrieve_knowledge"]["output"]["knowledge_count"] >= 1
    assert trace_by_key["select_tables_fields"]["tool_label"] == "数据表字段选择器"
    assert trace_by_key["select_tables_fields"]["output"]["tables"] == ["house_price_monthly"]
    assert trace_by_key["select_tables_fields"]["output"]["fields"] == ["month", "district", "avg_price"]
    assert trace_by_key["deepseek_text_to_sql"]["tool"] == "deepseek_chat_completion"
    assert trace_by_key["deepseek_text_to_sql"]["tool_label"] == "DeepSeek SQL 生成工具"
    assert trace_by_key["deepseek_text_to_sql"]["output"]["sql"].startswith("SELECT month")
    assert trace_by_key["validate_sql"]["tool_label"] == "只读 SQL 安全校验器"
    assert trace_by_key["validate_sql"]["output"] == {"status": "passed", "tables": ["house_price_monthly"]}
    assert trace_by_key["execute_and_visualize"]["tool_label"] == "SQLite 查询与图表工具"
    assert trace_by_key["execute_and_visualize"]["output"]["row_count"] == len(body["datasets"][0]["rows"])
    assert trace_by_key["execute_and_visualize"]["output"]["chart_reason"] == "line chart selected for month trend"
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


def test_deepseek_mode_normalizes_district_alias_from_follow_up_sql(client, monkeypatch):
    _deepseek_env(monkeypatch)

    def fake_generate(self, question, context, knowledge, metrics=None):
        if "朝阳" not in question:
            return TextToSqlResult(
                sql=(
                    "SELECT month, district, avg_price FROM house_price_monthly "
                    "WHERE month LIKE '2025-%' ORDER BY month, district"
                ),
                reasoning="首轮趋势分析。",
                chart=ChartSpec(
                    type="line",
                    x_field="month",
                    y_fields=["avg_price"],
                    title="2025年各区房价趋势",
                ),
                confidence=0.82,
                used_knowledge_ids=[item.id for item in knowledge],
            )
        assert context.year_from == 2025
        assert context.district == "朝阳区"
        return TextToSqlResult(
            sql=(
                "SELECT month, district, avg_price FROM house_price_monthly "
                "WHERE month LIKE '2025-%' AND district = '朝阳' ORDER BY month"
            ),
            reasoning="模型使用了区域简称。",
            chart=ChartSpec(
                type="line",
                x_field="month",
                y_fields=["avg_price"],
                title="2025年朝阳区房价趋势",
            ),
            confidence=0.82,
            used_knowledge_ids=[item.id for item in knowledge],
        )

    monkeypatch.setattr(text_to_sql.DeepSeekTextToSqlService, "generate", fake_generate)
    conversation_id = client.post("/api/conversations").json()["id"]
    client.post(
        "/api/chat",
        json={
            "conversation_id": conversation_id,
            "question": "分析2025年各区平均房价",
        },
    )

    response = client.post(
        "/api/chat",
        json={"conversation_id": conversation_id, "question": "那朝阳呢"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["context"]["district"] == "朝阳区"
    assert body["datasets"][0]["rows"]
    assert {row["district"] for row in body["datasets"][0]["rows"]} == {"朝阳区"}
    assert "district = '朝阳区'" in body["queries"][0]["sql"]
    assert body["metadata"]["sql_district_normalized"] is True


def test_deepseek_mode_does_not_crash_when_sql_repair_returns_invalid_json(client, monkeypatch):
    _deepseek_env(monkeypatch)

    def fake_generate(self, question, context, knowledge, metrics=None):
        return TextToSqlResult(
            sql=(
                "SELECT month, district, avg_price FROM house_price_monthly "
                "WHERE month LIKE '2025-%' AND district = '不存在区域'"
            ),
            reasoning="第一次查询条件过窄。",
            chart=ChartSpec(type="line", x_field="month", y_fields=["avg_price"], title="空结果图表"),
            confidence=0.67,
            used_knowledge_ids=[item.id for item in knowledge],
        )

    def fake_repair(self, question, context, knowledge, failed_sql, error_message, repair_reason):
        raise ModelOutputError("模型返回不是合法 JSON")

    monkeypatch.setattr(text_to_sql.DeepSeekTextToSqlService, "generate", fake_generate)
    monkeypatch.setattr(text_to_sql.DeepSeekTextToSqlService, "repair_sql", fake_repair)
    conversation_id = client.post("/api/conversations").json()["id"]

    response = client.post(
        "/api/chat",
        json={"conversation_id": conversation_id, "question": "分析2025年不存在区域房价趋势"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "completed"
    assert body["datasets"][0]["rows"] == []
    assert body["metadata"]["sql_repair_status"] == "failed"
    assert "模型返回不是合法 JSON" in body["metadata"]["sql_repair_error"]


def test_deepseek_mode_scopes_sql_to_single_year_context_when_model_omits_year(client, monkeypatch):
    _deepseek_env(monkeypatch)

    def fake_generate(self, question, context, knowledge, metrics=None):
        if "上一年" not in question:
            return TextToSqlResult(
                sql=(
                    "SELECT month, district, avg_price FROM house_price_monthly "
                    "WHERE month LIKE '2025-%' ORDER BY month, district"
                ),
                reasoning="首轮趋势分析。",
                chart=ChartSpec(type="line", x_field="month", y_fields=["avg_price"], title="2025年房价趋势"),
                confidence=0.75,
                used_knowledge_ids=[item.id for item in knowledge],
            )
        assert context.year_from == 2024
        return TextToSqlResult(
            sql=(
                "SELECT month, AVG(avg_price) AS avg_price FROM house_price_monthly "
                "GROUP BY month ORDER BY month"
            ),
            reasoning="模型漏掉了年份过滤。",
            chart=ChartSpec(type="line", x_field="month", y_fields=["avg_price"], title="上一年房价趋势"),
            confidence=0.75,
            used_knowledge_ids=[item.id for item in knowledge],
        )

    monkeypatch.setattr(text_to_sql.DeepSeekTextToSqlService, "generate", fake_generate)
    conversation_id = client.post("/api/conversations").json()["id"]
    client.post(
        "/api/chat",
        json={
            "conversation_id": conversation_id,
            "question": "分析2025年各区平均房价",
        },
    )

    response = client.post(
        "/api/chat",
        json={"conversation_id": conversation_id, "question": "那上一年呢"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["context"]["year_from"] == 2024
    assert "2024-%" in body["queries"][0]["sql"]
    assert body["metadata"]["sql_context_scoped"] is True
    assert {row["month"][:4] for row in body["datasets"][0]["rows"]} == {"2024"}


def test_deepseek_mode_corrects_sql_year_when_model_conflicts_with_context(client, monkeypatch):
    _deepseek_env(monkeypatch)

    def fake_generate(self, question, context, knowledge, metrics=None):
        if "上一年" not in question:
            return TextToSqlResult(
                sql=(
                    "SELECT month, district, avg_price FROM house_price_monthly "
                    "WHERE month LIKE '2025-%' ORDER BY month, district"
                ),
                reasoning="首轮趋势分析。",
                chart=ChartSpec(type="line", x_field="month", y_fields=["avg_price"], title="2025年房价趋势"),
                confidence=0.75,
                used_knowledge_ids=[item.id for item in knowledge],
            )
        assert context.year_from == 2024
        return TextToSqlResult(
            sql=(
                "SELECT month, avg_price FROM house_price_monthly "
                "WHERE substr(month, 1, 4) = '2023' ORDER BY month"
            ),
            reasoning="模型错误地把上一年再次回退到 2023。",
            chart=ChartSpec(type="line", x_field="month", y_fields=["avg_price"], title="上一年房价趋势"),
            confidence=0.75,
            used_knowledge_ids=[item.id for item in knowledge],
        )

    monkeypatch.setattr(text_to_sql.DeepSeekTextToSqlService, "generate", fake_generate)
    conversation_id = client.post("/api/conversations").json()["id"]
    client.post(
        "/api/chat",
        json={
            "conversation_id": conversation_id,
            "question": "分析2025年各区平均房价",
        },
    )

    response = client.post(
        "/api/chat",
        json={"conversation_id": conversation_id, "question": "那上一年呢"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["context"]["year_from"] == 2024
    assert "2024" in body["queries"][0]["sql"]
    assert "2023" not in body["queries"][0]["sql"]
    assert body["metadata"]["sql_context_year_corrected"] is True
    assert {row["month"][:4] for row in body["datasets"][0]["rows"]} == {"2024"}


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
