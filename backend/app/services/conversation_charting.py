from __future__ import annotations

from typing import Any

from app.domain import get_default_domain_config
from app.schemas import ChartSpec


DOMAIN_CONFIG = get_default_domain_config()
CHART_FIELD_PRIORITY = DOMAIN_CONFIG.chart_field_priority


def is_number(value: object) -> bool:
    if value is None or isinstance(value, bool):
        return False
    try:
        float(value)
    except (TypeError, ValueError):
        return False
    return True


def chart_title(question: str, x_field: str, y_fields: list[str]) -> str:
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


def pick_y_fields(question: str, fields: list[str], numeric_fields: list[str]) -> list[str]:
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


def repair_chart(
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
        field for field in fields if any(is_number(row.get(field)) for row in rows)
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
        return enrich_chart_spec(chart, fields)

    x_field = "month" if "month" in fields else "district" if "district" in fields else fields[0]
    y_fields = pick_y_fields(question, fields, numeric_fields)
    chart_type = "line" if x_field == "month" else "bar"
    metadata["chart_validation_status"] = "repaired"
    metadata["chart_repair_reason"] = (
        "模型未返回图表建议或图表字段不在 SQL 查询结果中，已按实际结果字段重建图表。"
    )
    return enrich_chart_spec(ChartSpec(
        type=chart_type,
        x_field=x_field,
        y_fields=y_fields,
        title=chart_title(question, x_field, y_fields),
    ), fields)


def field_unit(field: str) -> str | None:
    return DOMAIN_CONFIG.field_units.get(field)


def recommend_reason(chart_type: str, x_field: str) -> str:
    if chart_type == "line" and x_field == "month":
        return "按月份展示趋势，推荐使用折线图。"
    if chart_type == "bar":
        return "按区域或类别对比数值，推荐使用柱状图。"
    if chart_type == "pie":
        return "展示构成占比，推荐使用饼图。"
    if chart_type == "scatter":
        return "展示两个数值指标之间的关系，推荐使用散点图。"
    if chart_type == "stacked_bar":
        return "展示多个指标在同一类别下的构成，推荐使用堆叠柱状图。"
    return "展示查询明细，推荐使用表格。"


def enrich_chart_spec(chart: ChartSpec, fields: list[str]) -> ChartSpec:
    y_field = chart.y_fields[0] if chart.y_fields else ""
    return ChartSpec(
        type=chart.type,
        x_field=chart.x_field,
        y_fields=chart.y_fields,
        title=chart.title,
        x_axis_name=chart.x_axis_name or chart.x_field,
        y_axis_name=chart.y_axis_name or y_field or None,
        unit=chart.unit or field_unit(y_field),
        series_mode=chart.series_mode or ("stacked" if chart.type == "stacked_bar" else None),
        recommended_reason=chart.recommended_reason or recommend_reason(chart.type, chart.x_field),
    )
