from __future__ import annotations

from typing import Any

from app.config import get_settings
from app.domain import get_default_domain_config
from app.schemas import AnalysisPlan, ChartSpec, QueryContext
from app.services.sql_guard import TABLE_REF


TOOL_LABELS = get_default_domain_config().tool_labels


def find_step(plan: AnalysisPlan, key: str):
    return next((step for step in plan.steps if step.key == key), None)


def step_output(plan: AnalysisPlan, key: str, output: dict[str, Any], status: str = "completed") -> None:
    step = find_step(plan, key)
    if step:
        step.status = status
        step.output = output
        step.output_summary = friendly_output_summary(key, output)


def step_failed(plan: AnalysisPlan, key: str, error: str, output: dict[str, Any] | None = None) -> None:
    step = find_step(plan, key)
    if step:
        step.status = "failed"
        step.error = error
        step.output = output
        step.output_summary = [f"执行失败：{error}"]


def tables_from_sql(sql: str) -> list[str]:
    return sorted({match.group(1) for match in TABLE_REF.finditer(sql)})


def chart_reason(chart: ChartSpec | None, datasets: list[dict[str, Any]]) -> str:
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


def friendly_input_summary(key: str, input_data: dict[str, Any]) -> list[str]:
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


def friendly_output_summary(key: str, output: dict[str, Any]) -> list[str]:
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
            friendly_chart_reason(str(output.get("chart_reason") or "")),
        ]
    return []


def friendly_chart_reason(reason: str) -> str:
    if reason == "line chart selected for month trend":
        return "选择折线图：适合展示按月份变化的趋势"
    if reason == "bar chart selected for category comparison":
        return "选择柱状图：适合对比不同区域或类别"
    if reason == "table selected for detailed row inspection":
        return "选择表格：适合查看明细数据"
    if reason.startswith("table view selected"):
        return "选择表格：模型图表建议不可用，已降级为明细展示"
    return "根据字段类型和问题意图选择图表"


def prime_agent_trace(plan: AnalysisPlan, question: str, context: QueryContext) -> None:
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
            step.input_summary = friendly_input_summary(step.key, step.input or {})
            if defaults.get("output") is not None:
                step.output = defaults.get("output")
                step.output_summary = friendly_output_summary(step.key, step.output or {})


def finalize_agent_trace(
    plan: AnalysisPlan,
    safe_sql: str | None,
    datasets: list[dict[str, Any]],
    chart: ChartSpec | None,
) -> None:
    tables = tables_from_sql(safe_sql or "")
    fields = datasets[0]["fields"] if datasets else []
    if tables or fields:
        step_output(plan, "select_tables_fields", {"tables": tables, "fields": fields})
    if safe_sql:
        step_output(plan, "validate_sql", {"status": "passed", "tables": tables})
    row_count = sum(len(dataset["rows"]) for dataset in datasets)
    step_output(
        plan,
        "execute_and_visualize",
        {
            "row_count": row_count,
            "dataset_count": len(datasets),
            "chart_type": chart.type if chart else None,
            "chart_reason": chart_reason(chart, datasets),
        },
    )

