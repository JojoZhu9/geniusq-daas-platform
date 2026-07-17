from __future__ import annotations

from typing import Any

from sqlalchemy import inspect, text
from sqlalchemy.orm import Session


BUSINESS_TABLES = {
    "house_price_monthly": {
        "title": "房价月度指标",
        "description": "按行政区和月份记录平均房价、租金、挂牌量、空置率及环比同比变化。",
    },
    "housing_transactions": {
        "title": "住房成交指标",
        "description": "按行政区和月份记录成交套数、成交面积、新房/二手房数量与成交均价。",
    },
    "district_population": {
        "title": "区域人口指标",
        "description": "按行政区和年份记录常住人口、增速、收入中位数和家庭数量。",
    },
    "commuting_metrics": {
        "title": "通勤与就业指标",
        "description": "按行政区和年份记录平均通勤时长、跨区通勤比例、轨道覆盖率与就业密度。",
    },
    "semantic_metrics": {
        "title": "语义指标库",
        "description": "记录系统可理解的业务指标、别名、公式、字段和维度。",
    },
    "knowledge_items": {
        "title": "知识库条目",
        "description": "记录私有和公共知识，用于增强 Text-to-SQL 的表结构与业务口径理解。",
    },
}

INTERNAL_TABLES = {
    "conversations",
    "messages",
    "analysis_runs",
    "dashboards",
    "dashboard_cards",
    "analysis_feedback",
    "sync_logs",
    "data_tables",
    "requirement_mappings",
}

COLUMN_LABELS = {
    "district": "行政区",
    "month": "月份",
    "year": "年份",
    "avg_price": "平均房价",
    "rent_price": "平均租金",
    "listing_count": "挂牌量",
    "vacancy_rate": "空置率",
    "mom_change": "环比变化",
    "yoy_change": "同比变化",
    "transaction_count": "成交套数",
    "transaction_area": "成交面积",
    "new_house_count": "新房成交套数",
    "second_hand_count": "二手房成交套数",
    "avg_transaction_price": "成交均价",
    "resident_population": "常住人口",
    "growth_rate": "人口增速",
    "median_income": "收入中位数",
    "household_count": "家庭数量",
    "avg_commute_minutes": "平均通勤时长",
    "cross_district_ratio": "跨区通勤比例",
    "metro_coverage_rate": "轨道覆盖率",
    "employment_density": "就业密度",
}


def visible_table_names(session: Session) -> list[str]:
    inspector = inspect(session.get_bind())
    names = inspector.get_table_names()
    return sorted(name for name in names if name in BUSINESS_TABLES and name not in INTERNAL_TABLES)


def list_tables(session: Session) -> list[dict[str, Any]]:
    return [table_summary(session, name) for name in visible_table_names(session)]


def overview(session: Session, database_url: str) -> dict[str, Any]:
    tables = list_tables(session)
    return {
        "database": {
            "engine": "SQLite",
            "url": mask_sqlite_url(database_url),
        },
        "table_count": len(tables),
        "column_count": sum(table["column_count"] for table in tables),
        "row_count": sum(table["row_count"] for table in tables),
        "business_tables": [table["name"] for table in tables],
    }


def table_detail(session: Session, table_name: str) -> dict[str, Any] | None:
    if table_name not in visible_table_names(session):
        return None
    summary = table_summary(session, table_name)
    return {
        **summary,
        "columns": table_columns(session, table_name),
        "sample_rows": sample_rows(session, table_name),
        "suggested_questions": suggested_questions(table_name),
    }


def table_summary(session: Session, table_name: str) -> dict[str, Any]:
    metadata = BUSINESS_TABLES[table_name]
    return {
        "name": table_name,
        "title": metadata["title"],
        "description": metadata["description"],
        "row_count": row_count(session, table_name),
        "column_count": len(table_columns(session, table_name)),
    }


def table_columns(session: Session, table_name: str) -> list[dict[str, Any]]:
    inspector = inspect(session.get_bind())
    primary_keys = set(inspector.get_pk_constraint(table_name).get("constrained_columns") or [])
    sample = sample_rows(session, table_name, limit=1)
    first_row = sample[0] if sample else {}
    return [
        {
            "name": column["name"],
            "type": str(column["type"]),
            "label": COLUMN_LABELS.get(column["name"], column["name"]),
            "role": infer_column_role(column["name"], str(column["type"])),
            "is_primary_key": column["name"] in primary_keys,
            "sample_value": first_row.get(column["name"]),
        }
        for column in inspector.get_columns(table_name)
    ]


def row_count(session: Session, table_name: str) -> int:
    return int(session.execute(text(f'SELECT COUNT(*) FROM "{table_name}"')).scalar_one())


def sample_rows(session: Session, table_name: str, limit: int = 5) -> list[dict[str, Any]]:
    rows = session.execute(text(f'SELECT * FROM "{table_name}" LIMIT :limit'), {"limit": limit}).mappings().all()
    return [dict(row) for row in rows]


def infer_column_role(name: str, column_type: str) -> str:
    if name in {"district", "month", "year"}:
        return "筛选 / 分组维度"
    if "TEXT" in column_type.upper():
        return "文本说明"
    return "可聚合指标"


def suggested_questions(table_name: str) -> list[str]:
    questions = {
        "house_price_monthly": [
            "2025年各区平均房价趋势如何？",
            "海淀区和朝阳区的房价、租金有什么差异？",
            "哪个区域的房价同比涨幅最高？",
        ],
        "housing_transactions": [
            "2025年各区成交套数趋势如何？",
            "哪个区域的新房和二手房成交差异最大？",
            "成交均价和成交面积是否同步变化？",
        ],
        "district_population": [
            "各区常住人口和收入中位数有什么关系？",
            "哪个区人口增速最高？",
            "2024年和2025年各区人口有什么变化？",
        ],
        "commuting_metrics": [
            "哪些区域平均通勤时间最长？",
            "跨区通勤比例和轨道覆盖率有什么关系？",
            "就业密度最高的区域有哪些？",
        ],
    }
    return questions.get(table_name, ["这张表有哪些字段可以用于分析？"])


def mask_sqlite_url(database_url: str) -> str:
    if database_url.startswith("sqlite:///"):
        return "sqlite:///backend/runtime/daas_demo.db"
    return database_url
