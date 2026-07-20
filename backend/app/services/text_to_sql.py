from __future__ import annotations

import json
import re
from typing import Any

import httpx

from app.schemas import (
    ChartSpec,
    QueryContext,
    RetrievedKnowledge,
    SemanticMetric,
    TextToSqlResult,
)


class ModelOutputError(ValueError):
    """Raised when the model response cannot be parsed as the required JSON."""


class DeepSeekProviderError(RuntimeError):
    def __init__(self, error_type: str, message: str) -> None:
        super().__init__(message)
        self.error_type = error_type
        self.message = message


def parse_model_json(content: str) -> dict[str, Any]:
    cleaned = content.strip()
    fence = re.fullmatch(r"```(?:json)?\s*(.*?)\s*```", cleaned, flags=re.DOTALL)
    if fence:
        cleaned = fence.group(1).strip()
    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise ModelOutputError("模型输出不是合法 JSON") from exc
    if not isinstance(parsed, dict):
        raise ModelOutputError("模型输出 JSON 必须是对象")
    return parsed


class DeepSeekTextToSqlService:
    def __init__(
        self,
        api_key: str,
        base_url: str,
        model: str,
        timeout_seconds: int = 30,
        client: Any | None = None,
    ) -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout_seconds = timeout_seconds
        self.client = client or httpx.Client()

    def generate(
        self,
        question: str,
        context: QueryContext,
        knowledge: list[RetrievedKnowledge],
        metrics: list[SemanticMetric] | None = None,
    ) -> TextToSqlResult:
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": self._system_prompt()},
                {
                    "role": "user",
                    "content": self._user_prompt(question, context, knowledge, metrics or []),
                },
            ],
            "temperature": 0.1,
            "response_format": {"type": "json_object"},
            "max_tokens": 1200,
        }
        response = self._post(payload)
        raw = response.json()
        content = raw["choices"][0]["message"]["content"]
        parsed = parse_model_json(content)
        return self._normalize_result(parsed, knowledge)

    def repair_sql(
        self,
        question: str,
        context: QueryContext,
        knowledge: list[RetrievedKnowledge],
        failed_sql: str,
        error_message: str,
        repair_reason: str,
        metrics: list[SemanticMetric] | None = None,
    ) -> TextToSqlResult:
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": self._system_prompt()},
                {
                    "role": "user",
                    "content": self._repair_prompt(
                        question,
                        context,
                        knowledge,
                        metrics or [],
                        failed_sql,
                        error_message,
                        repair_reason,
                    ),
                },
            ],
            "temperature": 0.05,
            "response_format": {"type": "json_object"},
            "max_tokens": 1200,
        }
        response = self._post(payload)
        raw = response.json()
        content = raw["choices"][0]["message"]["content"]
        parsed = parse_model_json(content)
        return self._normalize_result(parsed, knowledge)

    def _post(self, payload: dict[str, Any]) -> httpx.Response:
        try:
            response = self.client.post(
                f"{self.base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
                timeout=self.timeout_seconds,
            )
            response.raise_for_status()
            return response
        except httpx.TimeoutException as exc:
            raise DeepSeekProviderError("timeout", "DeepSeek 请求超时，请检查网络或稍后重试。") from exc
        except httpx.HTTPStatusError as exc:
            status_code = exc.response.status_code
            if status_code in (401, 403):
                raise DeepSeekProviderError("auth_error", "DeepSeek 鉴权失败，请检查 API Key 是否正确。") from exc
            if status_code == 429:
                raise DeepSeekProviderError("rate_limited", "DeepSeek 请求被限流，请稍后重试。") from exc
            raise DeepSeekProviderError("provider_error", f"DeepSeek 服务返回异常状态码：{status_code}。") from exc
        except httpx.HTTPError as exc:
            raise DeepSeekProviderError("network_error", "DeepSeek 网络连接失败，请检查 Base URL 和本地网络。") from exc

    @staticmethod
    def _system_prompt() -> str:
        return (
            "你是企业数据平台的 Text-to-SQL 助手。只返回 JSON。"
            "SQL 必须是 SQLite 单条 SELECT 或 WITH 查询；只能使用提供的表和字段；"
            "不允许 INSERT、UPDATE、DELETE、DROP、ALTER、CREATE。"
            "如果用户问题已经包含年份、指标、表名、字段名或明确分析对象，请直接生成 SQL，"
            "不要因为缺少展示偏好、排序方式或图表细节而要求澄清。"
            "SQL SELECT 字段必须包含 chart_suggestion 的 x_field 和全部 y_fields；"
            "图表字段必须来自 SQL 结果字段。"
            "当问题提到租金、挂牌、空置、成交、人口、收入、地铁、就业或通勤时，"
            "优先选择对应字段 rent_price、listing_count、vacancy_rate、transaction_count、"
            "resident_population、median_income、metro_coverage_rate、employment_density、avg_commute_minutes。"
            "只有在缺少可查询指标或无法判断任何可用数据表时，才返回 needs_clarification=true。"
            "JSON 示例："
            '{"needs_clarification":false,"suggestions":[],"sql":"SELECT ...",'
            '"reasoning":"...","chart_suggestion":{"type":"line","x_field":"month",'
            '"y_fields":["avg_price"],"title":"..."}, "confidence":0.8}'
        )

    @staticmethod
    def _user_prompt(
        question: str,
        context: QueryContext,
        knowledge: list[RetrievedKnowledge],
        metrics: list[SemanticMetric] | None = None,
    ) -> str:
        knowledge_lines = [
            (
                f"- [{item.id}] {item.title} / {item.kind} / {item.scope} / "
                f"tables={','.join(item.linked_tables)}\n{item.content}"
            )
            for item in knowledge
        ]
        metric_lines = [
            (
                f"- [{item.id}] {item.name}: {item.description}\n"
                f"  formula={item.formula}; fields={','.join(item.fields)}; "
                f"tables={','.join(item.tables)}; dimensions={','.join(item.dimensions)}; "
                f"aliases={','.join(item.aliases)}"
            )
            for item in (metrics or [])
        ]
        return "\n".join(
            [
                "可用数据表：",
                "house_price_monthly(district, month, avg_price, rent_price, listing_count, vacancy_rate, mom_change, yoy_change)",
                "housing_transactions(district, month, transaction_count, transaction_area, new_house_count, second_hand_count, avg_transaction_price)",
                "district_population(district, year, resident_population, growth_rate, median_income, household_count)",
                "commuting_metrics(district, year, avg_commute_minutes, cross_district_ratio, metro_coverage_rate, employment_density)",
                "",
                "检索到的知识：",
                "\n".join(knowledge_lines) or "无",
                "",
                "命中的业务指标口径：",
                "\n".join(metric_lines) or "无",
                "",
                f"当前上下文：{context.model_dump_json()}",
                f"用户问题：{question}",
                "",
                "返回字段：needs_clarification, suggestions, sql, reasoning, chart_suggestion, confidence。",
            ]
        )

    @staticmethod
    def _repair_prompt(
        question: str,
        context: QueryContext,
        knowledge: list[RetrievedKnowledge],
        metrics: list[SemanticMetric],
        failed_sql: str,
        error_message: str,
        repair_reason: str,
    ) -> str:
        return "\n".join(
            [
                DeepSeekTextToSqlService._user_prompt(question, context, knowledge, metrics),
                "",
                "上一次 SQL 需要修复：",
                failed_sql,
                "",
                f"修复原因：{repair_reason}",
                f"错误或诊断信息：{error_message}",
                "",
                "请只返回修复后的 JSON。修复要求：",
                "1. sql 必须仍然是 SQLite 单条 SELECT 或 WITH 查询。",
                "2. 不要使用不存在的字段或未授权数据表。",
                "3. 如果原因是 empty_result，请优先放宽过窄的 WHERE 条件，但保留用户问题的核心年份和指标。",
                "4. chart_suggestion 的 x_field 和 y_fields 必须来自修复后 SQL 的 SELECT 输出字段。",
            ]
        )

    @staticmethod
    def _normalize_result(
        parsed: dict[str, Any], knowledge: list[RetrievedKnowledge]
    ) -> TextToSqlResult:
        chart = None
        chart_payload = parsed.get("chart_suggestion") or parsed.get("chart")
        if isinstance(chart_payload, dict):
            chart_type = chart_payload.get("type")
            if chart_type not in {"line", "bar", "pie", "table", "scatter", "stacked_bar"}:
                chart_type = "table"
            chart = ChartSpec(
                type=chart_type,
                x_field=str(chart_payload.get("x_field") or ""),
                y_fields=[str(value) for value in chart_payload.get("y_fields") or []],
                x_axis_name=chart_payload.get("x_axis_name"),
                y_axis_name=chart_payload.get("y_axis_name"),
                unit=chart_payload.get("unit"),
                series_mode=chart_payload.get("series_mode"),
                recommended_reason=chart_payload.get("recommended_reason"),
                title=str(chart_payload.get("title") or "模型生成图表"),
            )
        return TextToSqlResult(
            sql=str(parsed.get("sql") or ""),
            reasoning=str(parsed.get("reasoning") or ""),
            chart=chart,
            confidence=parsed.get("confidence"),
            used_knowledge_ids=[item.id for item in knowledge],
            raw_model_output=parsed,
            needs_clarification=bool(parsed.get("needs_clarification", False)),
            suggestions=[str(item) for item in parsed.get("suggestions") or []],
        )
