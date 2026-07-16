from __future__ import annotations

import json
import re
from typing import Any

import httpx

from app.schemas import ChartSpec, QueryContext, RetrievedKnowledge, TextToSqlResult


class ModelOutputError(ValueError):
    """Raised when the model response cannot be parsed as the required JSON."""


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
    ) -> TextToSqlResult:
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": self._system_prompt()},
                {
                    "role": "user",
                    "content": self._user_prompt(question, context, knowledge),
                },
            ],
            "temperature": 0.1,
            "response_format": {"type": "json_object"},
        }
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
        raw = response.json()
        content = raw["choices"][0]["message"]["content"]
        parsed = parse_model_json(content)
        return self._normalize_result(parsed, knowledge)

    @staticmethod
    def _system_prompt() -> str:
        return (
            "你是企业数据平台的 Text-to-SQL 助手。只返回 JSON。"
            "SQL 必须是 SQLite 单条 SELECT 或 WITH 查询；只能使用提供的表和字段；"
            "不允许 INSERT、UPDATE、DELETE、DROP、ALTER、CREATE。"
        )

    @staticmethod
    def _user_prompt(
        question: str,
        context: QueryContext,
        knowledge: list[RetrievedKnowledge],
    ) -> str:
        knowledge_lines = [
            (
                f"- [{item.id}] {item.title} / {item.kind} / {item.scope} / "
                f"tables={','.join(item.linked_tables)}\n{item.content}"
            )
            for item in knowledge
        ]
        return "\n".join(
            [
                "可用数据表：",
                "house_price_monthly(district, month, avg_price, mom_change, yoy_change)",
                "housing_transactions(district, month, transaction_count, transaction_area)",
                "district_population(district, year, resident_population, growth_rate)",
                "commuting_metrics(district, year, avg_commute_minutes, cross_district_ratio)",
                "",
                "检索到的知识：",
                "\n".join(knowledge_lines) or "无",
                "",
                f"当前上下文：{context.model_dump_json()}",
                f"用户问题：{question}",
                "",
                "返回字段：needs_clarification, suggestions, sql, reasoning, chart_suggestion, confidence。",
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
            if chart_type not in {"line", "bar", "pie", "table"}:
                chart_type = "table"
            chart = ChartSpec(
                type=chart_type,
                x_field=str(chart_payload.get("x_field") or ""),
                y_fields=[str(value) for value in chart_payload.get("y_fields") or []],
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
