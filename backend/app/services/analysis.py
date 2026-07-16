import re
from sqlalchemy.orm import Session

from app.config import Settings
from app.errors import ApiError
from app.schemas import (
    AnalysisPlan,
    AnalysisStep,
    ChartSpec,
    PlannedQuery,
    QueryContext,
)
from app.services.retrieval import retrieve_relevant_knowledge
from app.services.text_to_sql import DeepSeekTextToSqlService


class OfflineAnalysisEngine:
    """Build deterministic, auditable analysis plans without external services."""

    def analyze(self, question: str, context: QueryContext) -> AnalysisPlan:
        normalized = question.strip()
        year = self._resolve_year(normalized, context)

        if self._is_cross_source_question(normalized):
            return self._cross_source_plan(year)
        if self._is_incomplete_house_price_question(normalized, context):
            return self._clarification_plan()
        return self._house_price_trend_plan(year, context)

    @staticmethod
    def _resolve_year(question: str, context: QueryContext) -> int:
        match = re.search(r"(20\d{2})年", question)
        if match:
            return int(match.group(1))
        return context.year_from or context.year_to or 2025

    @staticmethod
    def _is_cross_source_question(question: str) -> bool:
        return "房价" in question and ("人口" in question or "通勤" in question)

    @staticmethod
    def _is_incomplete_house_price_question(
        question: str, context: QueryContext
    ) -> bool:
        has_context_year = context.year_from is not None or context.year_to is not None
        has_question_year = re.search(r"20\d{2}年", question) is not None
        return "房价" in question and not has_context_year and not has_question_year

    @staticmethod
    def _clarification_plan() -> AnalysisPlan:
        return AnalysisPlan(
            needs_clarification=True,
            suggestions=[
                "分析2025年各区平均房价",
                "对比2024年与2025年各区房价涨幅",
                "分析2025年房价与成交量的关系",
            ],
            steps=[
                AnalysisStep(
                    key="check_scope",
                    title="检查分析范围",
                    detail="已确认问题缺少时间范围，需要补充后再查询数据。",
                )
            ],
            insights=["当前问题未指定房价分析的时间范围。"],
            requirement_ids=["2.2"],
            metadata={"mode": "offline", "intent": "house_price_incomplete"},
        )

    @staticmethod
    def _house_price_trend_plan(year: int, context: QueryContext) -> AnalysisPlan:
        district_filter = (
            f" AND district = '{context.district}'" if context.district else ""
        )
        sql = (
            "SELECT month, district, avg_price, mom_change, yoy_change "
            "FROM house_price_monthly "
            f"WHERE month LIKE '{year}-%'{district_filter} "
            "ORDER BY month, district"
        )
        return AnalysisPlan(
            steps=[
                AnalysisStep(
                    key="scope",
                    title="确认分析范围",
                    detail=f"分析 {year} 年房价月度变化。",
                ),
                AnalysisStep(
                    key="select_tables",
                    title="选择数据表与字段",
                    detail="house_price_monthly：district、month、avg_price、mom_change、yoy_change。",
                ),
                AnalysisStep(
                    key="invoke_skill",
                    title="调用趋势与异常检测 Skill",
                    detail="按统一口径计算最大值、月度趋势和异常波动。",
                ),
                AnalysisStep(
                    key="execute_sql",
                    title="规划并校验只读 SQL",
                    detail="通过授权表、单语句和 500 行上限校验后执行查询。",
                ),
            ],
            queries=[PlannedQuery(source="房产数据", sql=sql)],
            chart=ChartSpec(
                type="line",
                x_field="month",
                y_fields=["avg_price"],
                title=f"{year}年各区房价趋势",
            ),
            insights=[
                f"已生成 {year} 年按月、按区的房价趋势分析口径。",
                "结果同时保留环比和同比字段，可用于识别趋势和异常波动。",
            ],
            follow_ups=[
                "哪些区的同比涨幅最高？",
                "是否继续分析房价与成交量的关系？",
            ],
            requirement_ids=[
                "2.1-a", "2.1-b", "2.1-c", "2.4-a", "2.4-b", "2.5"
            ],
            metadata={"mode": "offline", "intent": "house_price_trend"},
        )

    @staticmethod
    def _cross_source_plan(year: int) -> AnalysisPlan:
        price_sql = (
            "SELECT district, AVG(avg_price) AS avg_price, "
            "AVG(yoy_change) AS avg_yoy_change "
            "FROM house_price_monthly "
            f"WHERE month LIKE '{year}-%' GROUP BY district ORDER BY district"
        )
        population_commute_sql = (
            "SELECT p.district, p.resident_population, p.growth_rate, "
            "c.avg_commute_minutes, c.cross_district_ratio "
            "FROM district_population AS p "
            "JOIN commuting_metrics AS c "
            "ON p.district = c.district AND p.year = c.year "
            f"WHERE p.year = {year} ORDER BY p.district"
        )
        return AnalysisPlan(
            steps=[
                AnalysisStep(
                    key="split_sources",
                    title="拆分多源指标",
                    detail="将问题拆分为房价、人口和通勤三类指标。",
                ),
                AnalysisStep(
                    key="query_sources",
                    title="选择数据表与字段",
                    detail=(
                        f"从 house_price_monthly、district_population 和 "
                        f"commuting_metrics 读取 {year} 年授权字段。"
                    ),
                ),
                AnalysisStep(
                    key="align_districts",
                    title="按区域对齐口径",
                    detail="以区域为共同维度合并各数据源的年度指标。",
                ),
                AnalysisStep(
                    key="invoke_skill",
                    title="调用多源关联分析 Skill",
                    detail="生成同口径对比与相关性提示，不将相关性解释为因果。",
                ),
            ],
            queries=[
                PlannedQuery(source="房产数据", sql=price_sql),
                PlannedQuery(source="人口通勤数据", sql=population_commute_sql),
            ],
            chart=ChartSpec(
                type="bar",
                x_field="district",
                y_fields=[
                    "avg_yoy_change",
                    "growth_rate",
                    "avg_commute_minutes",
                ],
                title=f"{year}年房价、人口与通勤指标对比",
            ),
            insights=[
                "已将房价与人口通勤指标按区域对齐，可进行横向比较。",
                "相关性仅表示指标共同变化，不直接表示因果关系。",
            ],
            follow_ups=[
                "哪些区的人口增长与房价涨幅同向？",
                "是否排除异常区域后重新比较？",
            ],
            requirement_ids=[
                "2.1-a", "2.1-b", "2.1-c", "2.4-a", "2.4-b", "2.5", "5"
            ],
            metadata={"mode": "offline", "intent": "cross_source_correlation"},
        )


class DeepSeekAnalysisEngine:
    """Build analysis plans with retrieved knowledge and DeepSeek Text-to-SQL."""

    def __init__(self, session: Session, settings: Settings) -> None:
        if not settings.deepseek_api_key:
            raise ApiError(
                503,
                "DEEPSEEK_API_KEY_MISSING",
                "DeepSeek API Key 未配置",
                "请在 .env 中配置 DEEPSEEK_API_KEY，或切换 LLM_MODE=offline",
            )
        self.session = session
        self.settings = settings
        self.service = DeepSeekTextToSqlService(
            api_key=settings.deepseek_api_key,
            base_url=settings.deepseek_base_url,
            model=settings.deepseek_model,
            timeout_seconds=settings.deepseek_timeout_seconds,
        )

    def analyze(self, question: str, context: QueryContext) -> AnalysisPlan:
        knowledge = retrieve_relevant_knowledge(self.session, question)
        result = self.service.generate(question, context, knowledge)
        used_knowledge = [
            {
                "id": item.id,
                "title": item.title,
                "kind": item.kind,
                "scope": item.scope,
                "linked_tables": item.linked_tables,
                "score": item.score,
            }
            for item in knowledge
            if item.id in result.used_knowledge_ids
        ]
        if result.needs_clarification:
            return AnalysisPlan(
                needs_clarification=True,
                suggestions=result.suggestions,
                steps=[
                    AnalysisStep(
                        key="deepseek_clarification",
                        title="DeepSeek 判断需要补充信息",
                        detail=result.reasoning or "模型认为当前问题缺少必要分析条件。",
                    )
                ],
                insights=[result.reasoning] if result.reasoning else [],
                metadata={
                    "mode": "deepseek",
                    "model": self.settings.deepseek_model,
                    "used_knowledge": used_knowledge,
                    "model_reasoning": result.reasoning,
                    "confidence": result.confidence,
                    "sql_validation_status": "not_run",
                },
            )
        return AnalysisPlan(
            steps=[
                AnalysisStep(
                    key="retrieve_knowledge",
                    title="检索问数知识",
                    detail=f"已检索到 {len(used_knowledge)} 条相关知识用于生成 SQL。",
                ),
                AnalysisStep(
                    key="deepseek_text_to_sql",
                    title="调用 DeepSeek 生成 SQL",
                    detail=result.reasoning or "模型已返回候选 SQL 和图表建议。",
                ),
                AnalysisStep(
                    key="validate_sql",
                    title="校验只读 SQL",
                    detail="候选 SQL 将继续经过授权表、单语句和只读规则校验。",
                ),
            ],
            queries=[PlannedQuery(source="DeepSeek Text-to-SQL", sql=result.sql)],
            chart=result.chart,
            insights=[result.reasoning] if result.reasoning else [],
            follow_ups=[
                "改成柱状图",
                "只看朝阳区和海淀区",
                "把当前 SQL 收藏为示例",
            ],
            metadata={
                "mode": "deepseek",
                "model": self.settings.deepseek_model,
                "used_knowledge": used_knowledge,
                "model_reasoning": result.reasoning,
                "confidence": result.confidence,
                "sql_validation_status": "pending",
            },
        )
