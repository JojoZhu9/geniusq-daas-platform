from __future__ import annotations

import json
import re

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.schemas import RetrievedKnowledge


DOMAIN_TERMS = {
    "房价": ["house_price_monthly", "avg_price", "均价", "价格"],
    "均价": ["house_price_monthly", "avg_price", "房价"],
    "趋势": ["month", "月度", "变化"],
    "成交": ["housing_transactions", "transaction_count", "transaction_area"],
    "人口": ["district_population", "resident_population", "growth_rate"],
    "通勤": ["commuting_metrics", "avg_commute_minutes", "cross_district_ratio"],
}


def _tokens(text_value: str) -> set[str]:
    lowered = text_value.lower()
    words = set(re.findall(r"[a-zA-Z_][a-zA-Z0-9_]*|20\d{2}|[\u4e00-\u9fff]{2,}", lowered))
    for key, expansions in DOMAIN_TERMS.items():
        if key in text_value:
            words.add(key)
            words.update(expansions)
    return words


def _active_tables(session: Session) -> set[str]:
    rows = session.execute(
        text("SELECT name FROM data_tables WHERE status = 'active'")
    ).mappings()
    return {row["name"] for row in rows}


def retrieve_relevant_knowledge(
    session: Session, question: str, limit: int = 5
) -> list[RetrievedKnowledge]:
    question_tokens = _tokens(question)
    if not question_tokens:
        return []
    active_tables = _active_tables(session)
    rows = session.execute(
        text(
            "SELECT * FROM knowledge_items "
            "WHERE schema_status = 'valid' "
            "ORDER BY CASE scope WHEN 'private' THEN 0 ELSE 1 END, created_at DESC"
        )
    ).mappings()

    results: list[RetrievedKnowledge] = []
    for row in rows:
        linked_tables = json.loads(row["linked_tables_json"])
        if linked_tables and not set(linked_tables).issubset(active_tables):
            continue
        tags = json.loads(row["tags_json"])
        haystack = " ".join(
            [
                row["name"],
                row["kind"],
                row["scope"],
                row["content"],
                " ".join(linked_tables),
                " ".join(tags),
            ]
        )
        knowledge_tokens = _tokens(haystack)
        overlap = question_tokens & knowledge_tokens
        if not overlap:
            continue
        score = float(len(overlap) * 2)
        if row["scope"] == "private":
            score += 1.5
        if row["kind"] == "sql":
            score += 1.0
        if "指标口径" in tags:
            score += 10.0
        if set(linked_tables) & question_tokens:
            score += 1.0
        results.append(
            RetrievedKnowledge(
                id=row["id"],
                title=row["name"],
                kind=row["kind"],
                scope=row["scope"],
                content=row["content"],
                linked_tables=linked_tables,
                score=score,
            )
        )

    results.sort(key=lambda item: (-item.score, 0 if item.scope == "private" else 1, item.title))
    return results[:limit]
