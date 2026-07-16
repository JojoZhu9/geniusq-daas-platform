import pytest

from app.schemas import QueryContext, RetrievedKnowledge
from app.services.text_to_sql import DeepSeekTextToSqlService, ModelOutputError, parse_model_json


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload


class FakeClient:
    def __init__(self):
        self.requests = []

    def post(self, url, headers, json, timeout):
        self.requests.append(
            {"url": url, "headers": headers, "json": json, "timeout": timeout}
        )
        return FakeResponse(
            {
                "choices": [
                    {
                        "message": {
                            "content": (
                                '{"sql":"SELECT month, district, avg_price '
                                "FROM house_price_monthly WHERE month LIKE "
                                "'2025-%'\","
                                '"reasoning":"按月查询房价趋势",'
                                '"chart_suggestion":{"type":"line",'
                                '"x_field":"month","y_fields":["avg_price"],'
                                '"title":"2025年各区房价趋势"},'
                                '"confidence":0.84}'
                            )
                        }
                    }
                ]
            }
        )


def test_parse_model_json_accepts_plain_and_fenced_json():
    assert parse_model_json('{"sql":"SELECT 1"}') == {"sql": "SELECT 1"}
    assert parse_model_json('```json\n{"sql":"SELECT 1"}\n```') == {"sql": "SELECT 1"}


def test_parse_model_json_rejects_malformed_output():
    with pytest.raises(ModelOutputError):
        parse_model_json("SELECT * FROM house_price_monthly")


def test_deepseek_service_generates_text_to_sql_result():
    client = FakeClient()
    service = DeepSeekTextToSqlService(
        api_key="test-key",
        base_url="https://api.deepseek.com/v1",
        model="deepseek-chat",
        client=client,
    )
    knowledge = [
        RetrievedKnowledge(
            id="knowledge-sql-trend",
            title="月度房价趋势 SQL 模型",
            kind="sql",
            scope="private",
            content="SELECT month, district, avg_price FROM house_price_monthly",
            linked_tables=["house_price_monthly"],
            score=8.5,
        )
    ]

    result = service.generate("分析2025年各区房价趋势", QueryContext(), knowledge)

    assert result.sql.startswith("SELECT month, district, avg_price")
    assert result.reasoning == "按月查询房价趋势"
    assert result.chart is not None
    assert result.chart.type == "line"
    assert result.confidence == 0.84
    assert result.used_knowledge_ids == ["knowledge-sql-trend"]
    assert client.requests[0]["headers"]["Authorization"] == "Bearer test-key"
