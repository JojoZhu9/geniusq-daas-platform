import re

from sqlalchemy import Engine, text


class SqlSafetyError(ValueError):
    """Raised when a query violates the read-only SQL policy."""


FORBIDDEN = re.compile(
    r"\b(insert|update|delete|drop|alter|create|replace|truncate|attach|detach|pragma|vacuum)\b",
    re.IGNORECASE,
)
TABLE_REF = re.compile(
    r"\b(?:from|join)\s+([A-Za-z_][A-Za-z0-9_]*)", re.IGNORECASE
)
CTE_REF = re.compile(
    r"(?:\bwith|,)\s*([A-Za-z_][A-Za-z0-9_]*)\s+as\s*\(", re.IGNORECASE
)


def validate_read_only_sql(sql: str, allowed_tables: set[str]) -> str:
    normalized = sql.strip()
    if ";" in normalized.rstrip(";") or not re.match(
        r"^(select|with)\b", normalized, re.IGNORECASE
    ):
        raise SqlSafetyError("仅允许执行单条 SELECT 或 WITH 查询")
    if FORBIDDEN.search(normalized):
        raise SqlSafetyError("查询包含被禁止的 SQL 操作")

    cte_names = set(CTE_REF.findall(normalized))
    referenced = set(TABLE_REF.findall(normalized)) - cte_names
    if not referenced or not referenced.issubset(allowed_tables):
        raise SqlSafetyError("查询访问了未授权数据表")
    return normalized.rstrip(";")


def execute_read_only(
    engine: Engine, sql: str, row_limit: int = 500
) -> list[dict[str, object]]:
    if row_limit <= 0:
        raise ValueError("row_limit must be positive")
    guarded = f"SELECT * FROM ({sql}) AS safe_query LIMIT {int(row_limit)}"
    with engine.connect() as connection:
        return [dict(row) for row in connection.execute(text(guarded)).mappings()]
