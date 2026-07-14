from collections.abc import Iterable

from sqlalchemy import Engine, text


SCHEMA_STATEMENTS = (
    """
    CREATE TABLE IF NOT EXISTS house_price_monthly (
        district TEXT NOT NULL,
        month TEXT NOT NULL,
        avg_price INTEGER NOT NULL,
        mom_change REAL NOT NULL,
        yoy_change REAL NOT NULL,
        PRIMARY KEY (district, month)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS housing_transactions (
        district TEXT NOT NULL,
        month TEXT NOT NULL,
        transaction_count INTEGER NOT NULL,
        transaction_area REAL NOT NULL,
        PRIMARY KEY (district, month)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS district_population (
        district TEXT NOT NULL,
        year INTEGER NOT NULL,
        resident_population REAL NOT NULL,
        growth_rate REAL NOT NULL,
        PRIMARY KEY (district, year)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS commuting_metrics (
        district TEXT NOT NULL,
        year INTEGER NOT NULL,
        avg_commute_minutes REAL NOT NULL,
        cross_district_ratio REAL NOT NULL,
        PRIMARY KEY (district, year)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS requirement_mappings (
        id TEXT PRIMARY KEY,
        original TEXT NOT NULL,
        solution TEXT NOT NULL,
        page TEXT NOT NULL,
        acceptance TEXT NOT NULL,
        module TEXT NOT NULL,
        priority TEXT NOT NULL,
        status TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS conversations (
        id TEXT PRIMARY KEY,
        context_json TEXT NOT NULL,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS messages (
        id TEXT PRIMARY KEY,
        conversation_id TEXT NOT NULL,
        role TEXT NOT NULL,
        content TEXT NOT NULL,
        created_at TEXT NOT NULL,
        FOREIGN KEY (conversation_id) REFERENCES conversations(id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS analysis_runs (
        id TEXT PRIMARY KEY,
        conversation_id TEXT NOT NULL,
        question TEXT NOT NULL,
        status TEXT NOT NULL,
        response_json TEXT NOT NULL,
        created_at TEXT NOT NULL,
        FOREIGN KEY (conversation_id) REFERENCES conversations(id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS knowledge_items (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        kind TEXT NOT NULL,
        scope TEXT NOT NULL,
        library TEXT NOT NULL,
        content TEXT NOT NULL,
        fingerprint TEXT NOT NULL,
        linked_tables_json TEXT NOT NULL,
        tags_json TEXT NOT NULL,
        schema_status TEXT NOT NULL,
        overrides_id TEXT,
        created_at TEXT NOT NULL,
        UNIQUE (library, fingerprint)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS data_tables (
        name TEXT PRIMARY KEY,
        status TEXT NOT NULL,
        schema_version INTEGER NOT NULL,
        updated_at TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS sync_logs (
        id TEXT PRIMARY KEY,
        request_id TEXT NOT NULL,
        mode TEXT NOT NULL,
        status TEXT NOT NULL,
        message TEXT NOT NULL,
        changed_tables_json TEXT NOT NULL,
        created_at TEXT NOT NULL
    )
    """,
)


DISTRICTS = (
    ("东城区", 105000, 3200, 210.1, 31.2, 0.43),
    ("西城区", 120000, 2900, 110.0, 32.5, 0.39),
    ("朝阳区", 76000, 7800, 345.5, 41.8, 0.51),
    ("海淀区", 98000, 5100, 313.3, 39.6, 0.47),
    ("丰台区", 59000, 4600, 201.2, 42.4, 0.55),
    ("通州区", 44000, 3900, 184.3, 45.1, 0.58),
)


REQUIREMENT_MAPPINGS = (
    ("2.1-a", "展示具体处理过程", "任务步骤模型和可折叠时间线", "智能问数工作台", "提交完整问题，展开每个思考步骤", "智慧问数", "P0", "planned"),
    ("2.1-b", "关联数据并展示表名、更新时间、字段、时间范围、置信度", "数据来源侧栏和分析元数据", "智能问数工作台", "查看来源卡片并跳转数据表详情", "智慧问数", "P0", "planned"),
    ("2.1-c", "展示关联模型和分析步骤，模型做成 Skill", "模型/Skill 调用步骤与离线分析技能", "智能问数工作台", "查看趋势与异常检测 Skill 调用记录", "智慧问数", "P0", "planned"),
    ("2.2", "问题不完整时自动推荐相关问题", "完整性判定器和推荐问题组件", "智能问数工作台", "输入分析房价，点击推荐的时间范围问题", "智慧问数", "P0", "planned"),
    ("2.3", "支持多轮对话和连续追问", "会话上下文存储", "智能问数工作台", "首问 2025 年房价，再追问只看海淀区", "智慧问数", "P0", "planned"),
    ("2.4-a", "自动生成图表并发布，支持多图表组合", "图表规范、类型切换和加入仪表盘", "智能问数工作台", "生成图表，切换类型并加入仪表盘", "智慧问数", "P0", "planned"),
    ("2.4-b", "自动输出最大值、趋势和异常点等有价值结论", "确定性洞察计算器", "智能问数工作台", "查看结果上方的总结卡片", "智慧问数", "P0", "planned"),
    ("2.5", "从结果继续深入分析并推荐下一步问题", "基于结果元数据生成推荐追问", "智能问数工作台", "点击继续分析异常区域成交量", "智慧问数", "P1", "planned"),
    ("2.6", "保存仪表盘、多图表组合、拖拽布局、更新、分享与发布", "仪表盘卡片持久化和本地分享视图", "我的仪表盘", "移动卡片、刷新并打开分享链接", "智慧问数", "P1", "planned"),
    ("3.2", "自动查重；同库不重复；私有优先；私有可补充说明", "指纹查重和覆盖关系", "知识库管理", "创建重复知识并查看冲突处理", "知识库管理", "P0", "planned"),
    ("3.3", "公开库定义、入库同步、定时同步和删除联动", "数据表同步服务和模拟调度入口", "知识库管理", "手动同步、模拟定时同步、确认删除联动", "知识库管理", "P0", "planned"),
    ("3.4-a", "标签分类、筛选与检索", "标签、多条件筛选和全文检索", "知识库管理", "按房价和 SQL 组合筛选", "知识库管理", "P1", "planned"),
    ("3.4-b", "文本与数据表建立关联并可查看", "knowledge_links 双向关系", "知识库管理", "从文本知识打开关联表详情", "知识库管理", "P1", "planned"),
    ("3.4-c", "SQL 与数据表建立关系；SQL 变化时自动提示调整", "SQL 表名提取和失效状态", "知识库管理", "修改模拟表结构，查看 SQL 待调整提示", "知识库管理", "P1", "planned"),
    ("5", "多源知识学习；将综合问题拆为多个 SQL 并汇总结果", "多源规划器、子查询执行器和结果汇总器", "智能问数工作台", "提问房价上涨是否与人口和通勤相关", "智慧问数", "P0", "planned"),
)


def create_schema(engine: Engine) -> None:
    with engine.begin() as connection:
        for statement in SCHEMA_STATEMENTS:
            connection.execute(text(statement))


def _months() -> Iterable[tuple[int, int, int]]:
    for offset in range(24):
        yield 2024 + offset // 12, offset % 12 + 1, offset


def seed_all(engine: Engine) -> None:
    price_rows = []
    transaction_rows = []
    population_rows = []
    commuting_rows = []

    for district_index, (
        district,
        base_price,
        base_transactions,
        base_population,
        base_commute,
        base_cross_ratio,
    ) in enumerate(DISTRICTS):
        for year, month, offset in _months():
            month_key = f"{year:04d}-{month:02d}"
            price_rows.append(
                {
                    "district": district,
                    "month": month_key,
                    "avg_price": base_price + offset * (90 + district_index * 15) + ((month % 4) - 2) * 120,
                    "mom_change": round(0.18 + ((month + district_index) % 5) * 0.07, 2),
                    "yoy_change": round(1.4 + district_index * 0.22 + (offset // 12) * 0.35, 2),
                }
            )
            transaction_rows.append(
                {
                    "district": district,
                    "month": month_key,
                    "transaction_count": base_transactions + ((month * 137 + offset * 23 + district_index * 89) % 900),
                    "transaction_area": round((base_transactions + month * 41 + offset * 9) * (82.0 + district_index * 2.5), 1),
                }
            )

        for year_offset, year in enumerate((2024, 2025)):
            population_rows.append(
                {
                    "district": district,
                    "year": year,
                    "resident_population": round(base_population * (1 + year_offset * (0.002 + district_index * 0.0007)), 2),
                    "growth_rate": round(0.2 + district_index * 0.07 + year_offset * 0.05, 2),
                }
            )
            commuting_rows.append(
                {
                    "district": district,
                    "year": year,
                    "avg_commute_minutes": round(base_commute - year_offset * 0.3, 1),
                    "cross_district_ratio": round(base_cross_ratio - year_offset * 0.004, 3),
                }
            )

    with engine.begin() as connection:
        connection.execute(
            text(
                """
                INSERT OR IGNORE INTO house_price_monthly
                    (district, month, avg_price, mom_change, yoy_change)
                VALUES (:district, :month, :avg_price, :mom_change, :yoy_change)
                """
            ),
            price_rows,
        )
        connection.execute(
            text(
                """
                INSERT OR IGNORE INTO housing_transactions
                    (district, month, transaction_count, transaction_area)
                VALUES (:district, :month, :transaction_count, :transaction_area)
                """
            ),
            transaction_rows,
        )
        connection.execute(
            text(
                """
                INSERT OR IGNORE INTO district_population
                    (district, year, resident_population, growth_rate)
                VALUES (:district, :year, :resident_population, :growth_rate)
                """
            ),
            population_rows,
        )
        connection.execute(
            text(
                """
                INSERT OR IGNORE INTO commuting_metrics
                    (district, year, avg_commute_minutes, cross_district_ratio)
                VALUES (:district, :year, :avg_commute_minutes, :cross_district_ratio)
                """
            ),
            commuting_rows,
        )
        connection.execute(
            text(
                """
                INSERT OR IGNORE INTO requirement_mappings
                    (id, original, solution, page, acceptance, module, priority, status)
                VALUES
                    (:id, :original, :solution, :page, :acceptance, :module, :priority, :status)
                """
            ),
            [
                dict(
                    zip(
                        ("id", "original", "solution", "page", "acceptance", "module", "priority", "status"),
                        row,
                    )
                )
                for row in REQUIREMENT_MAPPINGS
            ],
        )
        connection.execute(
            text(
                """
                INSERT OR IGNORE INTO data_tables
                    (name, status, schema_version, updated_at)
                VALUES (:name, 'active', 1, '2026-07-14T00:00:00+08:00')
                """
            ),
            [{"name": name} for name in (
                "house_price_monthly",
                "housing_transactions",
                "district_population",
                "commuting_metrics",
            )],
        )
        connection.execute(
            text(
                """
                INSERT OR IGNORE INTO knowledge_items
                    (id, name, kind, scope, library, content, fingerprint,
                     linked_tables_json, tags_json, schema_status, overrides_id, created_at)
                VALUES
                    (:id, :name, :kind, :scope, :library, :content, :fingerprint,
                     :linked_tables, :tags, :schema_status, :overrides_id, :created_at)
                """
            ),
            [
                {
                    "id": "knowledge-public-house-price",
                    "name": "行政区房价口径（公开）",
                    "kind": "text",
                    "scope": "public",
                    "library": "公共知识库",
                    "content": "平均房价按行政区和月份统计，单位为元/平方米。",
                    "fingerprint": "seed-house-price-definition",
                    "linked_tables": '["house_price_monthly"]',
                    "tags": '["房价", "指标口径"]',
                    "schema_status": "valid",
                    "overrides_id": None,
                    "created_at": "2026-07-14T00:00:00+08:00",
                },
                {
                    "id": "knowledge-private-house-price",
                    "name": "行政区房价口径",
                    "kind": "text",
                    "scope": "private",
                    "library": "个人知识库",
                    "content": "平均房价按行政区和月份统计，内部分析补充剔除无效成交。",
                    "fingerprint": "seed-house-price-definition",
                    "linked_tables": '["house_price_monthly"]',
                    "tags": '["房价", "指标口径", "私有优先"]',
                    "schema_status": "valid",
                    "overrides_id": "knowledge-public-house-price",
                    "created_at": "2026-07-14T00:01:00+08:00",
                },
                {
                    "id": "knowledge-sql-trend",
                    "name": "月度房价趋势 SQL 模型",
                    "kind": "sql",
                    "scope": "private",
                    "library": "个人知识库",
                    "content": "SELECT month, district, avg_price FROM house_price_monthly",
                    "fingerprint": "seed-house-price-sql",
                    "linked_tables": '["house_price_monthly"]',
                    "tags": '["房价", "SQL"]',
                    "schema_status": "valid",
                    "overrides_id": None,
                    "created_at": "2026-07-14T00:02:00+08:00",
                },
            ],
        )
