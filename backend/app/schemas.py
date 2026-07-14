from typing import Any, List, Literal, Optional, Protocol

from pydantic import BaseModel, Field


class QueryContext(BaseModel):
    year_from: Optional[int] = None
    year_to: Optional[int] = None
    district: Optional[str] = None
    metric: Optional[str] = None


class AnalysisStep(BaseModel):
    key: str
    title: str
    detail: str
    status: Literal["pending", "running", "completed", "failed"] = "completed"


class PlannedQuery(BaseModel):
    source: str
    sql: str


class ChartSpec(BaseModel):
    type: Literal["line", "bar", "pie", "table"]
    x_field: str
    y_fields: List[str]
    title: str


class AnalysisPlan(BaseModel):
    needs_clarification: bool = False
    suggestions: List[str] = Field(default_factory=list)
    steps: List[AnalysisStep] = Field(default_factory=list)
    queries: List[PlannedQuery] = Field(default_factory=list)
    chart: Optional[ChartSpec] = None
    insights: List[str] = Field(default_factory=list)
    follow_ups: List[str] = Field(default_factory=list)
    requirement_ids: List[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class AnalysisEngine(Protocol):
    def analyze(self, question: str, context: QueryContext) -> AnalysisPlan:
        ...


class ChatRequest(BaseModel):
    conversation_id: str
    question: str = Field(min_length=1, max_length=500)
