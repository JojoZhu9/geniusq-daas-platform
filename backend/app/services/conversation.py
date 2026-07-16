from __future__ import annotations

import json
import re
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.config import get_settings
from app.errors import ApiError
from app.schemas import AnalysisPlan, ChartSpec, QueryContext
from app.services.analysis import DeepSeekAnalysisEngine, OfflineAnalysisEngine
from app.services.sql_guard import (
    TABLE_REF,
    SqlSafetyError,
    execute_read_only,
    validate_read_only_sql,
)


ALLOWED_TABLES = {
    "house_price_monthly",
    "housing_transactions",
    "district_population",
    "commuting_metrics",
}
DISTRICTS = ("海淀区", "朝阳区", "西城区", "东城区", "丰台区", "通州区")
CHART_FIELD_PRIORITY = (
    (("租金", "rent"), ("rent_price",)),
    (("挂牌", "房源"), ("listing_count",)),
    (("空置",), ("vacancy_rate",)),
    (("成交", "交易"), ("transaction_count", "avg_transaction_price", "new_house_count", "second_hand_count")),
    (("新房",), ("new_house_count",)),
    (("二手",), ("second_hand_count",)),
    (("收入",), ("median_income",)),
    (("家庭", "户数"), ("household_count",)),
    (("人口",), ("resident_population", "growth_rate")),
    (("地铁", "轨道"), ("metro_coverage_rate",)),
    (("就业",), ("employment_density",)),
    (("通勤",), ("avg_commute_minutes", "cross_district_ratio")),
    (("同比",), ("yoy_change",)),
    (("环比",), ("mom_change",)),
    (("房价", "均价", "价格"), ("avg_price",)),
)
TOOL_LABELS = {
    "intent_parser": "问题理解器",
    "conversation_context": "会话上下文管理器",
    "knowledge_retriever": "知识库检索工具",
    "schema_selector": "数据表字段选择器",
    "deepseek_chat_completion": "DeepSeek SQL 生成工具",
    "sql_guard": "只读 SQL 安全校验器",
    "sqlite_query_runner": "SQLite 查询与图表工具",
}


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


def _is_number(value: object) -> bool:
    if value is None or isinstance(value, bool):
        return False
    try:
        float(value)
    except (TypeError, ValueError):
        return False
    return True


def _chart_title(question: str, x_field: str, y_fields: list[str]) -> str:
    metric_label = "、".join(y_fields) if y_fields else "查询结果"
    if "租金" in question:
        metric_label = "租金"
    elif "挂牌" in question:
        metric_label = "挂牌量"
    elif "空置" in question:
        metric_label = "空置率"
    elif "成交" in question:
        metric_label = "成交量"
    elif "地铁" in question:
        metric_label = "地铁覆盖率"
    elif "就业" in question:
        metric_label = "就业密度"
    elif "人口" in question:
        metric_label = "人口"
    elif "通勤" in question:
        metric_label = "通勤指标"
    elif "房价" in question or "均价" in question:
        metric_label = "房价"
    return f"{metric_label}按{x_field}分析"


def _pick_y_fields(question: str, fields: list[str], numeric_fields: list[str]) -> list[str]:
    lowered_question = question.lower()
    for keywords, candidates in CHART_FIELD_PRIORITY:
        if any(keyword.lower() in lowered_question for keyword in keywords):
            matched = [field for field in candidates if field in numeric_fields]
            if matched:
                return matched[:2]
    preferred = [
        field
        for field in (
            "avg_price",
            "rent_price",
            "transaction_count",
            "resident_population",
            "avg_commute_minutes",
            "median_income",
        )
        if field in numeric_fields
    ]
    return (preferred or numeric_fields)[:2]


def _repair_chart(
    chart: ChartSpec | None,
    datasets: list[dict[str, Any]],
    question: str,
    metadata: dict[str, Any],
) -> ChartSpec | None:
    rows = [row for dataset in datasets for row in dataset["rows"]]
    fields = list(dict.fromkeys(field for dataset in datasets for field in dataset["fields"]))
    if not rows or not fields:
        return None

    numeric_fields = [
        field for field in fields if any(_is_number(row.get(field)) for row in rows)
    ]
    if not numeric_fields:
        metadata["chart_validation_status"] = "table_only_no_numeric_field"
        return ChartSpec(type="table", x_field=fields[0], y_fields=[], title="查询结果明细")

    valid_chart = (
        chart is not None
        and chart.x_field in fields
        and bool(chart.y_fields)
        and all(field in fields for field in chart.y_fields)
        and any(field in numeric_fields for field in chart.y_fields)
    )
    if valid_chart:
        metadata["chart_validation_status"] = "passed"
        return chart

    x_field = "month" if "month" in fields else "district" if "district" in fields else fields[0]
    y_fields = _pick_y_fields(question, fields, numeric_fields)
    chart_type = "line" if x_field == "month" else "bar"
    metadata["chart_validation_status"] = "repaired"
    metadata["chart_repair_reason"] = (
        "模型未返回图表建议或图表字段不在 SQL 查询结果中，已按实际结果字段重建图表。"
    )
    return ChartSpec(
        type=chart_type,
        x_field=x_field,
        y_fields=y_fields,
        title=_chart_title(question, x_field, y_fields),
    )


def _apply_sql_repair(
    engine: object,
    plan: AnalysisPlan,
    query: Any,
    question: str,
    context: QueryContext,
    error_message: str,
    reason: str,
) -> bool:
    repair = getattr(engine, "repair_sql", None)
    if repair is None:
        return False
    original_sql = query.sql
    result = repair(question, context, original_sql, error_message, reason)
    repaired_sql = result.sql.strip()
    if not repaired_sql or repaired_sql == original_sql.strip():
        return False
    query.sql = repaired_sql
    if result.chart:
        plan.chart = result.chart
    if result.reasoning:
        plan.metadata["sql_repair_reasoning"] = result.reasoning
    plan.metadata.setdefault("sql_repair_attempts", []).append(
        {
            "reason": reason,
            "from_sql": original_sql,
            "to_sql": repaired_sql,
            "message": error_message[:240],
        }
    )
    return True


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


def _used_questions_and_recommendations(session: Session, conversation_id: str) -> set[str]:
    used = {
        row["content"].strip()
        for row in session.execute(
            text(
                "SELECT content FROM messages "
                "WHERE conversation_id = :conversation_id AND role = 'user'"
            ),
            {"conversation_id": conversation_id},
        ).mappings()
        if row["content"].strip()
    }
    rows = session.execute(
        text(
            "SELECT response_json FROM analysis_runs "
            "WHERE conversation_id = :conversation_id"
        ),
        {"conversation_id": conversation_id},
    ).mappings()
    for row in rows:
        try:
            response = json.loads(row["response_json"])
        except json.JSONDecodeError:
            continue
        used.update(item.strip() for item in response.get("suggestions", []) if item.strip())
        used.update(item.strip() for item in response.get("follow_ups", []) if item.strip())
    return used


def _recommendation_pool(context: QueryContext) -> list[str]:
    year = context.year_from or context.year_to or 2025
    district = context.district
    if district:
        return [
            f"对比{district}和全市其他区的{year}年房价趋势",
            f"继续分析{district}{year}年房价与成交量的关系",
            f"查看{district}{year}年同比涨幅最高的月份",
            f"分析{district}{year}年成交套数变化",
            f"对比{district}{year}年房价环比和同比变化",
            f"把{district}{year}年房价趋势保存到仪表盘",
        ]
    return [
        f"分析{year}年各区房价趋势",
        f"对比{year - 1}年和{year}年各区房价涨幅",
        f"分析{year}年房价与成交量的关系",
        f"只看海淀区和朝阳区的{year}年房价趋势",
        f"查看{year}年同比涨幅最高的区域",
        f"分析{year}年房价与人口增长的关系",
        f"分析{year}年房价与通勤时间的关系",
        f"把{year}年各区房价趋势保存到仪表盘",
    ]


def _dedupe_recommendations(
    primary: list[str],
    used: set[str],
    context: QueryContext,
    current_question: str,
) -> list[str]:
    blocked = {current_question.strip(), *used}
    result: list[str] = []
    for item in [*primary, *_recommendation_pool(context)]:
        if item and item not in blocked and item not in result:
            result.append(item)
        if len(result) == 3:
            return result
    year = context.year_from or context.year_to or 2025
    while len(result) < 3:
        fallback = f"继续探索{year}年房价分析方向 {len(result) + 1}"
        if fallback not in blocked:
            result.append(fallback)
    return result


def select_analysis_engine(session: Session):
    settings = get_settings()
    if settings.llm_mode == "deepseek":
        return DeepSeekAnalysisEngine(session, settings)
    return OfflineAnalysisEngine()


def _find_step(plan: AnalysisPlan, key: str):
    return next((step for step in plan.steps if step.key == key), None)


def _step_output(plan: AnalysisPlan, key: str, output: dict[str, Any], status: str = "completed") -> None:
    step = _find_step(plan, key)
    if step:
        step.status = status
        step.output = output
        step.output_summary = _friendly_output_summary(key, output)


def _step_failed(plan: AnalysisPlan, key: str, error: str, output: dict[str, Any] | None = None) -> None:
    step = _find_step(plan, key)
    if step:
        step.status = "failed"
        step.error = error
        step.output = output
        step.output_summary = [f"执行失败：{error}"]


def _tables_from_sql(sql: str) -> list[str]:
    return sorted({match.group(1) for match in TABLE_REF.finditer(sql)})


def _chart_reason(chart: ChartSpec | None, datasets: list[dict[str, Any]]) -> str:
    if chart is None:
        return "table view selected because no valid chart suggestion was available"
    if chart.type == "line" and chart.x_field in {"month", "date"}:
        return "line chart selected for month trend"
    if chart.type == "bar":
        return "bar chart selected for category comparison"
    if chart.type == "table":
        return "table selected for detailed row inspection"
    fields = datasets[0]["fields"] if datasets else []
    return f"{chart.type} chart selected for x={chart.x_field}, y={chart.y_fields}, available_fields={fields}"


def _friendly_input_summary(key: str, input_data: dict[str, Any]) -> list[str]:
    if key == "understand_question":
        return [f"读取用户问题：{input_data.get('question')}"]
    if key == "merge_context":
        return ["读取当前会话中的历史年份、区域和指标条件"]
    if key == "retrieve_knowledge":
        return ["检索用户问题相关的知识片段", f"最多返回 {input_data.get('limit', 5)} 条候选知识"]
    if key == "select_tables_fields":
        return ["结合问题、知识库和指标口径选择可用数据表", "只选择回答问题所需的字段"]
    if key == "deepseek_text_to_sql":
        return [
            f"调用模型：{input_data.get('model') or 'DeepSeek'}",
            f"携带 {input_data.get('knowledge_count', 0)} 条知识和 {input_data.get('metric_count', 0)} 个指标口径",
        ]
    if key == "validate_sql":
        return ["检查 SQL 是否只读、单语句且只访问授权数据表"]
    if key == "execute_and_visualize":
        return [f"在本地 SQLite 中执行查询，最多返回 {input_data.get('row_limit')} 行"]
    return []


def _friendly_output_summary(key: str, output: dict[str, Any]) -> list[str]:
    if key in {"understand_question", "merge_context"}:
        year = output.get("year_from") or output.get("year_to") or "未指定"
        district = output.get("district") or "各区/全市"
        metric = output.get("metric") or "由模型判断"
        return [f"分析年份：{year}", f"分析区域：{district}", f"分析指标：{metric}"]
    if key == "retrieve_knowledge":
        result = [f"命中 {output.get('knowledge_count', 0)} 条知识"]
        metric_count = output.get("metric_count", 0)
        if metric_count:
            result.append(f"命中 {metric_count} 个指标口径")
        titles = [item for item in output.get("knowledge_titles", []) if item]
        if titles:
            result.append("知识来源：" + "、".join(titles[:3]))
        metric_names = [item for item in output.get("metric_names", []) if item]
        if metric_names:
            result.append("指标口径：" + "、".join(metric_names[:3]))
        return result
    if key == "select_tables_fields":
        tables = output.get("tables") or []
        fields = output.get("fields") or []
        return [
            "选择数据表：" + ("、".join(tables) if tables else "未确定"),
            "使用字段：" + ("、".join(fields) if fields else "未确定"),
        ]
    if key == "deepseek_text_to_sql":
        chart = output.get("chart") or {}
        result = ["已生成候选 SQL"]
        if output.get("confidence") is not None:
            result.append(f"模型置信度：{round(float(output['confidence']) * 100)}%")
        if chart:
            result.append(f"建议图表：{chart.get('title') or chart.get('type')}")
        return result
    if key == "validate_sql":
        tables = output.get("tables") or []
        status = "通过" if output.get("status") == "passed" else output.get("status")
        return [f"SQL 安全校验：{status}", "授权数据表：" + ("、".join(tables) if tables else "无")]
    if key == "execute_and_visualize":
        return [
            f"查询返回 {output.get('row_count', 0)} 行数据",
            f"生成 {output.get('chart_type') or '表格'} 展示",
            _friendly_chart_reason(str(output.get("chart_reason") or "")),
        ]
    return []


def _friendly_chart_reason(reason: str) -> str:
    if reason == "line chart selected for month trend":
        return "选择折线图：适合展示按月份变化的趋势"
    if reason == "bar chart selected for category comparison":
        return "选择柱状图：适合对比不同区域或类别"
    if reason == "table selected for detailed row inspection":
        return "选择表格：适合查看明细数据"
    if reason.startswith("table view selected"):
        return "选择表格：模型图表建议不可用，已降级为明细展示"
    return "根据字段类型和问题意图选择图表"


def _prime_agent_trace(plan: AnalysisPlan, question: str, context: QueryContext) -> None:
    metadata = plan.metadata
    used_knowledge = metadata.get("used_knowledge") or []
    used_metrics = metadata.get("used_metrics") or []
    query_sql = plan.queries[0].sql if plan.queries else ""
    chart = plan.chart.model_dump() if plan.chart else None
    trace_defaults: dict[str, dict[str, Any]] = {
        "understand_question": {
            "tool": "intent_parser",
            "input": {"question": question},
            "output": context.model_dump(),
        },
        "merge_context": {
            "tool": "conversation_context",
            "input": {"question": question},
            "output": context.model_dump(),
        },
        "retrieve_knowledge": {
            "tool": "knowledge_retriever",
            "input": {"question": question, "limit": 5},
            "output": {
                "knowledge_count": len(used_knowledge),
                "knowledge_titles": [item.get("title") for item in used_knowledge],
                "metric_count": len(used_metrics),
                "metric_names": [item.get("name") for item in used_metrics],
            },
        },
        "select_tables_fields": {
            "tool": "schema_selector",
            "input": {
                "question": question,
                "knowledge_tables": sorted({
                    table
                    for item in used_knowledge
                    for table in item.get("linked_tables", [])
                }),
                "metric_tables": sorted({
                    table
                    for item in used_metrics
                    for table in item.get("tables", [])
                }),
            },
        },
        "deepseek_text_to_sql": {
            "tool": "deepseek_chat_completion",
            "input": {
                "model": metadata.get("model"),
                "knowledge_count": len(used_knowledge),
                "metric_count": len(used_metrics),
            },
            "output": {
                "sql": query_sql,
                "confidence": metadata.get("confidence"),
                "chart": chart,
            },
        },
        "validate_sql": {
            "tool": "sql_guard",
            "input": {"sql": query_sql},
        },
        "execute_and_visualize": {
            "tool": "sqlite_query_runner",
            "input": {"row_limit": get_settings().query_row_limit},
        },
    }
    for step in plan.steps:
        defaults = trace_defaults.get(step.key)
        if defaults:
            step.tool = defaults.get("tool")
            step.tool_label = TOOL_LABELS.get(str(step.tool), str(step.tool))
            step.input = defaults.get("input")
            step.input_summary = _friendly_input_summary(step.key, step.input or {})
            if defaults.get("output") is not None:
                step.output = defaults.get("output")
                step.output_summary = _friendly_output_summary(step.key, step.output or {})


def _finalize_agent_trace(
    plan: AnalysisPlan,
    safe_sql: str | None,
    datasets: list[dict[str, Any]],
    chart: ChartSpec | None,
) -> None:
    tables = _tables_from_sql(safe_sql or "")
    fields = datasets[0]["fields"] if datasets else []
    if tables or fields:
        _step_output(plan, "select_tables_fields", {"tables": tables, "fields": fields})
    if safe_sql:
        _step_output(plan, "validate_sql", {"status": "passed", "tables": tables})
    row_count = sum(len(dataset["rows"]) for dataset in datasets)
    _step_output(
        plan,
        "execute_and_visualize",
        {
            "row_count": row_count,
            "dataset_count": len(datasets),
            "chart_type": chart.type if chart else None,
            "chart_reason": _chart_reason(chart, datasets),
        },
    )


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


def get_analysis(session: Session, analysis_id: str) -> dict[str, Any] | None:
    row = session.execute(
        text("SELECT response_json FROM analysis_runs WHERE id = :id"),
        {"id": analysis_id},
    ).mappings().first()
    return json.loads(row["response_json"]) if row else None
