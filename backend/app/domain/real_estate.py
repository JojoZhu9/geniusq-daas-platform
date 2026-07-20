from __future__ import annotations

from .config import DomainConfig


REAL_ESTATE_DOMAIN = DomainConfig(
    allowed_tables=(
        "house_price_monthly",
        "housing_transactions",
        "district_population",
        "commuting_metrics",
    ),
    districts=("海淀区", "朝阳区", "西城区", "东城区", "丰台区", "通州区"),
    relative_year_offsets=(
        (("前年",), -2),
        (("上一年", "前一年", "去年", "上年"), -1),
        (("下一年", "后一年", "明年", "下年"), 1),
        (("今年", "本年"), 0),
    ),
    chart_field_priority=(
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
    ),
    tool_labels={
        "intent_parser": "问题理解器",
        "conversation_context": "会话上下文管理器",
        "knowledge_retriever": "知识库检索工具",
        "schema_selector": "数据表字段选择器",
        "deepseek_chat_completion": "DeepSeek SQL 生成工具",
        "sql_guard": "只读 SQL 安全校验器",
        "sqlite_query_runner": "SQLite 查询与图表工具",
    },
    field_units={
        "avg_price": "元/平方米",
        "rent_price": "元/平方米",
        "avg_transaction_price": "元/平方米",
        "mom_change": "%",
        "yoy_change": "%",
        "growth_rate": "%",
        "vacancy_rate": "%",
        "metro_coverage_rate": "%",
        "cross_district_ratio": "%",
        "transaction_count": "数量",
        "listing_count": "数量",
        "resident_population": "数量",
        "household_count": "数量",
        "new_house_count": "数量",
        "second_hand_count": "数量",
        "avg_commute_minutes": "分钟",
    },
)

