from __future__ import annotations

import re
from typing import Any

from app.domain import get_default_domain_config
from app.schemas import AnalysisPlan, QueryContext


DOMAIN_CONFIG = get_default_domain_config()
DISTRICTS = DOMAIN_CONFIG.districts
RELATIVE_YEAR_OFFSETS = DOMAIN_CONFIG.relative_year_offsets


def merge_context(previous: QueryContext, question: str) -> QueryContext:
    values = previous.model_dump()
    years = [int(value) for value in re.findall(r"20\d{2}", question)]
    if years:
        values["year_from"] = min(years)
        values["year_to"] = max(years)
    else:
        base_year = previous.year_to or previous.year_from
        if base_year:
            for keywords, offset in RELATIVE_YEAR_OFFSETS:
                if any(keyword in question for keyword in keywords):
                    values["year_from"] = base_year + offset
                    values["year_to"] = base_year + offset
                    break
    for district in DISTRICTS:
        district_alias = district.removesuffix("区")
        if district in question or district_alias in question:
            values["district"] = district
            break
    if "各区" in question or "全市" in question:
        values["district"] = None
    if "租金" in question:
        values["metric"] = "租金"
    elif "成交" in question or "交易" in question:
        values["metric"] = "成交量"
    elif "人口" in question:
        values["metric"] = "人口"
    elif "通勤" in question:
        values["metric"] = "通勤"
    elif "房价" in question or "均价" in question:
        values["metric"] = "平均房价"
    return QueryContext(**values)


def _normalize_known_district_literals(query: Any) -> bool:
    normalized_sql = query.sql
    for district in DISTRICTS:
        district_alias = district.removesuffix("区")
        if not district_alias:
            continue
        for quote in ("'", '"'):
            normalized_sql = normalized_sql.replace(
                f"{quote}{district_alias}{quote}", f"{quote}{district}{quote}"
            )
    if normalized_sql == query.sql:
        return False
    query.sql = normalized_sql
    return True


def _selected_fields_sql(sql: str) -> str:
    match = re.search(r"\bselect\b(.*?)\bfrom\b", sql, flags=re.IGNORECASE | re.DOTALL)
    return match.group(1) if match else ""


def _scope_sql_to_single_year_context(query: Any, context: QueryContext) -> bool:
    if not context.year_from or context.year_from != context.year_to:
        return False
    sql = query.sql.strip().rstrip(";")
    sql_years = set(re.findall(r"20\d{2}", sql))
    context_year = str(context.year_from)
    if context_year in sql_years:
        return False
    if sql_years:
        query.sql = re.sub(r"20\d{2}", context_year, sql)
        return True
    selected_fields = _selected_fields_sql(sql)
    year = context.year_from
    if re.search(r"\bmonth\b", selected_fields, flags=re.IGNORECASE):
        query.sql = (
            f"SELECT * FROM ({sql}) AS scoped_query "
            f"WHERE month LIKE '{year}-%'"
        )
        return True
    if re.search(r"\byear\b", selected_fields, flags=re.IGNORECASE):
        query.sql = (
            f"SELECT * FROM ({sql}) AS scoped_query "
            f"WHERE year = {year}"
        )
        return True
    return False


def prepare_query_for_context(plan: AnalysisPlan, query: Any, context: QueryContext) -> None:
    if _normalize_known_district_literals(query):
        plan.metadata["sql_district_normalized"] = True
    if _scope_sql_to_single_year_context(query, context):
        plan.metadata["sql_context_scoped"] = True
        if re.search(r"20\d{2}", query.sql):
            plan.metadata["sql_context_year_corrected"] = True

