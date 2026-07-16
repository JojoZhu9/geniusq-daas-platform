from __future__ import annotations

import json
import re

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.schemas import SemanticMetric


def _tokens(value: str) -> set[str]:
    return set(re.findall(r"[a-zA-Z_][a-zA-Z0-9_]*|20\d{2}|[\u4e00-\u9fff]{2,}", value.lower()))


def _metric_from_row(row, score: float) -> SemanticMetric:
    return SemanticMetric(
        id=row["id"],
        name=row["name"],
        aliases=json.loads(row["aliases_json"]),
        description=row["description"],
        formula=row["formula"],
        fields=json.loads(row["fields_json"]),
        tables=json.loads(row["tables_json"]),
        dimensions=json.loads(row["dimensions_json"]),
        score=score,
    )


def retrieve_semantic_metrics(
    session: Session, question: str, limit: int = 4
) -> list[SemanticMetric]:
    question_tokens = _tokens(question)
    if not question_tokens:
        return []

    rows = session.execute(
        text("SELECT * FROM semantic_metrics ORDER BY created_at, id")
    ).mappings()
    results: list[SemanticMetric] = []
    for row in rows:
        aliases = json.loads(row["aliases_json"])
        direct_alias_hits = [alias for alias in aliases if alias.lower() in question.lower()]
        haystack = " ".join(
            [
                row["name"],
                row["description"],
                row["formula"],
                " ".join(aliases),
                " ".join(json.loads(row["fields_json"])),
                " ".join(json.loads(row["tables_json"])),
            ]
        )
        overlap = question_tokens & _tokens(haystack)
        if not direct_alias_hits and not overlap:
            continue
        score = float(len(overlap) * 2 + len(direct_alias_hits) * 10)
        results.append(_metric_from_row(row, score))

    results.sort(key=lambda item: (-item.score, item.name))
    return results[:limit]
