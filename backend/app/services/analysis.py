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
from app.services.semantic import retrieve_semantic_metrics
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
        if self._is_simple_question(question, context):
            return self._simple_question_plan()
        knowledge = retrieve_relevant_knowledge(self.session, question)
        metrics = retrieve_semantic_metrics(self.session, question)
        try:
            result = self.service.generate(question, context, knowledge, metrics)
        except TypeError as exc:
            if "positional" not in str(exc) and "argument" not in str(exc):
                raise
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
        used_metrics = [
            {
                "id": item.id,
                "name": item.name,
                "formula": item.formula,
                "fields": item.fields,
                "tables": item.tables,
                "description": item.description,
            }
            for item in metrics
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
                    "used_metrics": used_metrics,
                    "model_reasoning": result.reasoning,
                    "confidence": result.confidence,
                    "sql_validation_status": "not_run",
                },
            )
        return AnalysisPlan(
            steps=[
                AnalysisStep(
                    key="understand_question",
                    title="理解用户问题",
                    detail=(
                        f"识别到用户问题为“{question}”，当前上下文为"
                        f"年份 {context.year_from or context.year_to or '未指定'}、"
                        f"区域 {context.district or '各区/全市'}、"
                        f"指标 {context.metric or '待模型判断'}。"
                    ),
                ),
                AnalysisStep(
                    key="merge_context",
                    title="合并会话上下文",
                    detail="读取同一会话中的历史年份、区域和指标；本轮显式输入会覆盖历史条件。",
                ),
                AnalysisStep(
                    key="retrieve_knowledge",
                    title="检索问数知识",
                    detail=(
                        f"从知识库中检索到 {len(used_knowledge)} 条相关知识，"
                        "优先使用私有口径、SQL 示例和可用数据表说明。"
                    ),
                ),
                AnalysisStep(
                    key="select_tables_fields",
                    title="选择数据表与字段",
                    detail=(
                        "根据问题和知识匹配授权表字段，例如 house_price_monthly 的 "
                        "month、district、avg_price、mom_change、yoy_change。"
                    ),
                ),
                AnalysisStep(
                    key="deepseek_text_to_sql",
                    title="调用 DeepSeek 生成 SQL",
                    detail=result.reasoning or "将问题、上下文、表结构和知识片段发送给 DeepSeek，要求返回结构化 JSON。",
                ),
                AnalysisStep(
                    key="validate_sql",
                    title="校验只读 SQL",
                    detail="候选 SQL 将继续经过授权表、单语句和只读规则校验。",
                ),
                AnalysisStep(
                    key="execute_and_visualize",
                    title="执行查询并生成图表建议",
                    detail="SQL 校验通过后查询本地 SQLite，并使用模型返回的图表建议渲染折线、柱状或表格。",
                ),
            ],
            queries=[PlannedQuery(source="DeepSeek Text-to-SQL", sql=result.sql)],
            chart=result.chart,
            insights=[result.reasoning] if result.reasoning else [],
            follow_ups=self._follow_ups(context),
            metadata={
                "mode": "deepseek",
                "model": self.settings.deepseek_model,
                "used_knowledge": used_knowledge,
                "used_metrics": used_metrics,
                "model_reasoning": result.reasoning,
                "confidence": result.confidence,
                "sql_validation_status": "pending",
            },
        )

    @staticmethod
    def _is_simple_question(question: str, context: QueryContext) -> bool:
        normalized = question.strip()
        if any(term in normalized for term in ("删除", "修改", "更新", "写入", "清空", "drop", "delete", "update")):
            return False
        has_year = re.search(r"20\d{2}", normalized) is not None
        if len(normalized) <= 4 and any(term in normalized for term in ("房价", "均价", "成交", "人口", "通勤", "数据")):
            return True
        if normalized in {"分析", "看一下", "查一下", "帮我分析", "问数"}:
            return True
        return (
            any(term in normalized for term in ("房价", "均价"))
            and not has_year
            and context.year_from is None
            and context.year_to is None
        )

    @staticmethod
    def _simple_question_plan() -> AnalysisPlan:
        return AnalysisPlan(
            needs_clarification=True,
            suggestions=[
                "分析2025年各区房价趋势",
                "对比2024年和2025年各区房价涨幅",
                "分析2025年房价与成交量的关系",
            ],
            steps=[
                AnalysisStep(
                    key="detect_simple_question",
                    title="识别简单问题",
                    detail="当前问题缺少时间范围、分析对象或指标口径，先不调用模型生成 SQL。",
                ),
                AnalysisStep(
                    key="recommend_questions",
                    title="推荐可问问题",
                    detail="基于房价、成交量和趋势分析场景，生成 3 个可直接点击的推荐问题。",
                ),
            ],
            insights=["当前问题较简单，建议先选择一个明确的分析问题。"],
            requirement_ids=["2.2"],
            metadata={
                "mode": "deepseek",
                "intent": "simple_question_recommendation",
                "sql_validation_status": "not_run",
            },
        )

    def repair_sql(
        self,
        question: str,
        context: QueryContext,
        failed_sql: str,
        error_message: str,
        repair_reason: str,
    ):
        knowledge = retrieve_relevant_knowledge(self.session, question)
        metrics = retrieve_semantic_metrics(self.session, question)
        try:
            return self.service.repair_sql(
                question,
                context,
                knowledge,
                failed_sql,
                error_message,
                repair_reason,
                metrics,
            )
        except TypeError as exc:
            if "positional" not in str(exc) and "argument" not in str(exc):
                raise
            return self.service.repair_sql(
                question,
                context,
                knowledge,
                failed_sql,
                error_message,
                repair_reason,
            )

    @staticmethod
    def _follow_ups(context: QueryContext) -> list[str]:
        year = context.year_from or context.year_to or 2025
        if context.district:
            return [
                f"对比{context.district}和全市其他区的{year}年房价趋势",
                f"继续分析{context.district}{year}年房价与成交量的关系",
                f"查看{context.district}{year}年同比涨幅最高的月份",
            ]
        return [
            f"只看海淀区和朝阳区的{year}年房价趋势",
            f"继续分析{year}年房价与成交量的关系",
            f"把{year}年各区房价趋势保存到仪表盘",
        ]
