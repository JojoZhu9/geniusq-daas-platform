from app.schemas import QueryContext
from app.services.analysis import OfflineAnalysisEngine


def test_incomplete_house_price_question_returns_suggestions():
    plan = OfflineAnalysisEngine().analyze("分析房价", QueryContext())

    assert plan.needs_clarification is True
    assert len(plan.suggestions) == 3
    assert plan.queries == []


def test_complete_house_price_trend_returns_auditable_plan():
    plan = OfflineAnalysisEngine().analyze(
        "分析2025年各区房价趋势", QueryContext(year_from=2025, year_to=2025)
    )

    assert plan.needs_clarification is False
    assert [query.source for query in plan.queries] == ["房产数据"]
    assert "house_price_monthly" in plan.queries[0].sql
    assert plan.chart is not None
    assert plan.chart.type == "line"
    assert plan.steps
    assert all(step.status == "completed" for step in plan.steps)
    assert plan.insights
    assert plan.follow_ups


def test_cross_source_question_splits_into_multiple_queries():
    plan = OfflineAnalysisEngine().analyze(
        "2025年房价上涨是否与人口和通勤相关", QueryContext()
    )

    assert plan.needs_clarification is False
    assert len(plan.queries) >= 2
    assert {query.source for query in plan.queries} == {"房产数据", "人口通勤数据"}
    assert "5" in plan.requirement_ids
    assert plan.chart is not None
    assert plan.insights
    assert plan.follow_ups
