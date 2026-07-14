import re

from app.schemas import (
    AnalysisPlan,
    AnalysisStep,
    ChartSpec,
    PlannedQuery,
    QueryContext,
)


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
                "分析2025年各区房价趋势",
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
                    key="query_prices",
                    title="读取房产月度数据",
                    detail="按月份和区域读取均价、环比与同比指标。",
                ),
                AnalysisStep(
                    key="summarize_trend",
                    title="汇总趋势指标",
                    detail="用统一口径比较各区的月度走势。",
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
            requirement_ids=["2.1-a", "2.4-a", "2.4-b", "2.5"],
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
                    title="读取授权数据表",
                    detail=f"按区域读取 {year} 年房价涨幅、人口及通勤指标。",
                ),
                AnalysisStep(
                    key="align_districts",
                    title="按区域对齐口径",
                    detail="以区域为共同维度合并各数据源的年度指标。",
                ),
                AnalysisStep(
                    key="compare_metrics",
                    title="比较指标关系",
                    detail="生成同口径对比图表，供相关性解读。",
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
            requirement_ids=["2.1-a", "2.4-a", "2.4-b", "2.5", "5"],
            metadata={"mode": "offline", "intent": "cross_source_correlation"},
        )
