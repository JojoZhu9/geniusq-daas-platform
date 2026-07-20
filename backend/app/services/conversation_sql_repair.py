from __future__ import annotations

from typing import Any

from app.schemas import AnalysisPlan, QueryContext


def apply_sql_repair(
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
    try:
        result = repair(question, context, original_sql, error_message, reason)
    except Exception as exc:  # model repair is best-effort; never turn it into a 500
        plan.metadata["sql_repair_status"] = "failed"
        plan.metadata["sql_repair_error"] = str(exc)
        plan.metadata.setdefault("sql_repair_attempts", []).append(
            {
                "reason": reason,
                "from_sql": original_sql,
                "message": error_message[:240],
                "error": str(exc)[:240],
            }
        )
        return False
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

