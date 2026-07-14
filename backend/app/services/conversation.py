from __future__ import annotations

import json
import re
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config import get_settings
from app.schemas import AnalysisPlan, QueryContext
from app.services.analysis import OfflineAnalysisEngine
from app.services.sql_guard import TABLE_REF, execute_read_only, validate_read_only_sql


ALLOWED_TABLES = {
    "house_price_monthly",
    "housing_transactions",
    "district_population",
    "commuting_metrics",
}
DISTRICTS = ("海淀区", "朝阳区", "西城区", "东城区", "丰台区", "通州区")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def merge_context(previous: QueryContext, question: str) -> QueryContext:
    values = previous.model_dump()
    years = [int(value) for value in re.findall(r"20\d{2}", question)]
    if years:
        values["year_from"] = min(years)
        values["year_to"] = max(years)
    for district in DISTRICTS:
        if district in question:
            values["district"] = district
            break
    if "各区" in question or "全市" in question:
        values["district"] = None
    if "房价" in question or "均价" in question:
        values["metric"] = "平均房价"
    return QueryContext(**values)


def create_conversation(session: Session) -> dict[str, Any]:
    conversation_id = str(uuid.uuid4())
    timestamp = utc_now()
    context = QueryContext()
    session.execute(
        text(
            "INSERT INTO conversations "
            "(id, context_json, created_at, updated_at) "
            "VALUES (:id, :context, :created_at, :updated_at)"
        ),
        {
            "id": conversation_id,
            "context": context.model_dump_json(),
            "created_at": timestamp,
            "updated_at": timestamp,
        },
    )
    session.commit()
    return {"id": conversation_id, "context": context.model_dump(), "created_at": timestamp}


def _load_context(session: Session, conversation_id: str) -> QueryContext | None:
    row = session.execute(
        text("SELECT context_json FROM conversations WHERE id = :id"),
        {"id": conversation_id},
    ).mappings().first()
    if row is None:
        return None
    return QueryContext(**json.loads(row["context_json"]))


def _dataset(source: str, sql: str, rows: list[dict[str, object]]) -> dict[str, Any]:
    tables = sorted(set(TABLE_REF.findall(sql)))
    fields = list(rows[0].keys()) if rows else []
    return {
        "source": source,
        "table": "、".join(tables),
        "tables": tables,
        "updated_at": "2026-07-14T00:00:00+08:00",
        "confidence": 0.96,
        "fields": fields,
        "rows": rows,
    }


def _result_insights(plan: AnalysisPlan, datasets: list[dict[str, Any]]) -> list[str]:
    insights = list(plan.insights)
    price_rows = [
        row
        for dataset in datasets
        for row in dataset["rows"]
        if row.get("avg_price") is not None
    ]
    if price_rows:
        maximum = max(price_rows, key=lambda row: float(row["avg_price"]))
        insights.insert(
            0,
            f"最大值：{maximum.get('district', '当前范围')}平均房价为"
            f" {float(maximum['avg_price']):,.0f} 元/平方米。",
        )
    yoy_rows = [row for row in price_rows if row.get("yoy_change") is not None]
    if yoy_rows:
        anomaly = max(yoy_rows, key=lambda row: abs(float(row["yoy_change"])))
        insights.insert(
            1,
            f"异常点：{anomaly.get('district', '当前范围')}"
            f" {anomaly.get('month', '')} 同比变化 {float(anomaly['yoy_change']):.2f}%。",
        )
    if not any(dataset["rows"] for dataset in datasets):
        insights.insert(0, "当前筛选条件下没有匹配数据，可放宽时间或区域范围。")
    return insights


def run_chat(
    session: Session,
    conversation_id: str,
    question: str,
    engine: OfflineAnalysisEngine | None = None,
) -> dict[str, Any] | None:
    previous = _load_context(session, conversation_id)
    if previous is None:
        return None

    context = merge_context(previous, question)
    plan = (engine or OfflineAnalysisEngine()).analyze(question, context)
    datasets: list[dict[str, Any]] = []
    if not plan.needs_clarification:
        target_engine = session.get_bind()
        for query in plan.queries:
            safe_sql = validate_read_only_sql(query.sql, ALLOWED_TABLES)
            rows = execute_read_only(
                target_engine, safe_sql, get_settings().query_row_limit
            )
            datasets.append(_dataset(query.source, safe_sql, rows))

    analysis_id = str(uuid.uuid4())
    timestamp = utc_now()
    response = {
        "status": "needs_clarification" if plan.needs_clarification else "completed",
        "analysis_id": analysis_id,
        "conversation_id": conversation_id,
        "context": context.model_dump(),
        "suggestions": plan.suggestions,
        "steps": [step.model_dump() for step in plan.steps],
        "queries": [query.model_dump() for query in plan.queries],
        "datasets": datasets,
        "chart": plan.chart.model_dump() if plan.chart else None,
        "insights": _result_insights(plan, datasets),
        "follow_ups": plan.follow_ups,
        "requirement_ids": plan.requirement_ids,
        "metadata": plan.metadata,
        "created_at": timestamp,
    }
    session.execute(
        text(
            "UPDATE conversations SET context_json = :context, updated_at = :updated_at "
            "WHERE id = :id"
        ),
        {
            "id": conversation_id,
            "context": context.model_dump_json(),
            "updated_at": timestamp,
        },
    )
    session.execute(
        text(
            "INSERT INTO messages (id, conversation_id, role, content, created_at) "
            "VALUES (:id, :conversation_id, 'user', :content, :created_at)"
        ),
        {
            "id": str(uuid.uuid4()),
            "conversation_id": conversation_id,
            "content": question,
            "created_at": timestamp,
        },
    )
    session.execute(
        text(
            "INSERT INTO analysis_runs "
            "(id, conversation_id, question, status, response_json, created_at) "
            "VALUES (:id, :conversation_id, :question, :status, :response, :created_at)"
        ),
        {
            "id": analysis_id,
            "conversation_id": conversation_id,
            "question": question,
            "status": response["status"],
            "response": json.dumps(response, ensure_ascii=False),
            "created_at": timestamp,
        },
    )
    session.commit()
    return response


def get_analysis(session: Session, analysis_id: str) -> dict[str, Any] | None:
    row = session.execute(
        text("SELECT response_json FROM analysis_runs WHERE id = :id"),
        {"id": analysis_id},
    ).mappings().first()
    return json.loads(row["response_json"]) if row else None
