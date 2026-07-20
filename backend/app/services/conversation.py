from __future__ import annotations

import json
import uuid
from typing import Any

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.config import get_settings
from app.domain import get_default_domain_config
from app.errors import ApiError
from app.schemas import AnalysisPlan, QueryContext
from app.services.analysis import DeepSeekAnalysisEngine, OfflineAnalysisEngine
from app.services.conversation_charting import repair_chart as _repair_chart
from app.services.conversation_context import (
    merge_context,
    prepare_query_for_context as _prepare_query_for_context,
)
from app.services.conversation_history import (
    create_conversation,
    get_analysis,
    get_conversation_history,
    list_conversations,
    load_context as _load_context,
    utc_now,
)
from app.services.conversation_insights import (
    dedupe_recommendations as _dedupe_recommendations,
    result_insights as _result_insights,
    used_questions_and_recommendations as _used_questions_and_recommendations,
)
from app.services.conversation_sql_repair import apply_sql_repair as _apply_sql_repair
from app.services.conversation_trace import (
    finalize_agent_trace as _finalize_agent_trace,
    prime_agent_trace as _prime_agent_trace,
    step_failed as _step_failed,
    step_output as _step_output,
    tables_from_sql as _tables_from_sql,
)
from app.services.sql_guard import (
    TABLE_REF,
    SqlSafetyError,
    execute_read_only,
    validate_read_only_sql,
)


DOMAIN_CONFIG = get_default_domain_config()
ALLOWED_TABLES = DOMAIN_CONFIG.allowed_tables


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


def select_analysis_engine(session: Session):
    settings = get_settings()
    if settings.llm_mode == "deepseek":
        return DeepSeekAnalysisEngine(session, settings)
    return OfflineAnalysisEngine()


def run_chat(
    session: Session,
    conversation_id: str,
    question: str,
    engine: object | None = None,
) -> dict[str, Any] | None:
    previous = _load_context(session, conversation_id)
    if previous is None:
        return None

    inherited_context = any(value is not None for value in previous.model_dump().values())
    context = merge_context(previous, question)
    analysis_engine = engine or select_analysis_engine(session)
    plan = analysis_engine.analyze(question, context)
    _prime_agent_trace(plan, question, context)
    used_recommendations = _used_questions_and_recommendations(session, conversation_id)
    if plan.needs_clarification:
        plan.suggestions = _dedupe_recommendations(
            plan.suggestions, used_recommendations, context, question
        )
    else:
        plan.follow_ups = _dedupe_recommendations(
            plan.follow_ups, used_recommendations, context, question
        )
    datasets: list[dict[str, Any]] = []
    last_safe_sql: str | None = None
    if not plan.needs_clarification:
        target_engine = session.get_bind()
        for query in plan.queries:
            _prepare_query_for_context(plan, query, context)
            try:
                safe_sql = validate_read_only_sql(query.sql, ALLOWED_TABLES)
            except SqlSafetyError as exc:
                plan.metadata["sql_validation_status"] = "rejected"
                _step_failed(
                    plan,
                    "validate_sql",
                    str(exc),
                    {"status": "rejected", "tables": _tables_from_sql(query.sql)},
                )
                raise ApiError(
                    422,
                    "SQL_REJECTED",
                    f"模型生成的 SQL 未通过安全校验，已阻止执行：{exc}",
                    "请修改问题后重试，或切换 LLM_MODE=offline",
                ) from exc
            plan.metadata["sql_validation_status"] = "passed"
            last_safe_sql = safe_sql
            try:
                rows = execute_read_only(
                    target_engine, safe_sql, get_settings().query_row_limit
                )
            except SQLAlchemyError as exc:
                if _apply_sql_repair(
                    analysis_engine,
                    plan,
                    query,
                    question,
                    context,
                    str(exc),
                    "execution_error",
                ):
                    plan.metadata["sql_repair_status"] = "repaired"
                    _prepare_query_for_context(plan, query, context)
                    safe_sql = validate_read_only_sql(query.sql, ALLOWED_TABLES)
                    rows = execute_read_only(
                        target_engine, safe_sql, get_settings().query_row_limit
                    )
                else:
                    plan.metadata["sql_validation_status"] = "execution_failed"
                    _step_failed(
                        plan,
                        "execute_and_visualize",
                        str(exc),
                        {"sql": safe_sql, "tables": _tables_from_sql(safe_sql)},
                    )
                    raise ApiError(
                        422,
                        "SQL_EXECUTION_FAILED",
                        f"SQL 执行失败，且自动修复未成功：{exc}",
                        "请换一种问法，或检查模型生成 SQL 是否与数据表字段一致",
                    ) from exc
            if not rows and _apply_sql_repair(
                analysis_engine,
                plan,
                query,
                question,
                context,
                "SQL 执行成功但返回 0 行",
                "empty_result",
            ):
                plan.metadata["sql_repair_status"] = "empty_result_retried"
                _prepare_query_for_context(plan, query, context)
                safe_sql = validate_read_only_sql(query.sql, ALLOWED_TABLES)
                rows = execute_read_only(
                    target_engine, safe_sql, get_settings().query_row_limit
                )
            datasets.append(_dataset(query.source, safe_sql, rows))
    chart = _repair_chart(plan.chart, datasets, question, plan.metadata)
    _finalize_agent_trace(plan, last_safe_sql, datasets, chart)

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
        "chart": chart.model_dump() if chart else None,
        "insights": _result_insights(plan, datasets),
        "follow_ups": plan.follow_ups,
        "requirement_ids": list(dict.fromkeys([
            *plan.requirement_ids,
            *(["2.3"] if inherited_context else []),
        ])),
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
