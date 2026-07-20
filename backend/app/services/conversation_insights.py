from __future__ import annotations

import json
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.schemas import AnalysisPlan, QueryContext


def result_insights(plan: AnalysisPlan, datasets: list[dict[str, Any]]) -> list[str]:
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


def used_questions_and_recommendations(session: Session, conversation_id: str) -> set[str]:
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


def recommendation_pool(context: QueryContext) -> list[str]:
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


def dedupe_recommendations(
    primary: list[str],
    used: set[str],
    context: QueryContext,
    current_question: str,
) -> list[str]:
    blocked = {current_question.strip(), *used}
    result: list[str] = []
    for item in [*primary, *recommendation_pool(context)]:
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

