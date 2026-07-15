# Intelligent Query Optimization Demo Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Windows-local, offline-first GeniusQ DaaS Platform intelligent-query demo and a Chinese implementation proposal, with every feature traceable to the 石墨 0714 requirement list.

**Architecture:** A React + TypeScript single-page application calls a FastAPI service over JSON. FastAPI owns conversation orchestration, deterministic offline analysis, optional OpenAI-compatible inference, read-only SQLite execution, knowledge-base rules, dashboards, and requirement mappings; SQLite stores both demo business data and application state.

**Tech Stack:** Python 3.9+, FastAPI, SQLModel/SQLAlchemy, Pydantic, Pytest, React, TypeScript, Vite, React Router, TanStack Query, ECharts, Vitest, Testing Library, Playwright, SQLite, PowerShell.

## Global Constraints

- The demo must complete all acceptance paths without network access or an LLM key.
- `LLM_MODE=offline` is the default; `LLM_MODE=openai-compatible` requires `LLM_BASE_URL`, `LLM_API_KEY`, and `LLM_MODEL`.
- Browser code never receives or persists model credentials.
- Only one read-only `SELECT` or `WITH` statement may execute per subquery; reject DDL, DML, PRAGMA, ATTACH, and multi-statement SQL.
- Query results are capped at 500 rows and restricted to the four seeded demo tables.
- “思考过程” means auditable business execution steps, never hidden chain-of-thought text.
- The UI follows the supplied GeniusQ DaaS Platform screenshots: dark top bar, blue active state, left navigation, central workspace, pale gray page background.
- Every user-visible feature carries a requirement id from `2.1` through `5`, and `/api/requirements` is the canonical traceability source.
- PowerShell scripts call `npm.cmd`, not `npm`, because the current machine blocks `npm.ps1`.
- Do not edit or delete the pre-existing untracked mojibake file `docs/superpowers/specs/2026-07-14-smart-qa-optimization-demo-design.md`.

## Planned File Structure

```text
.
├── .env.example                         # Optional model configuration
├── README.md                            # Setup, demo script, troubleshooting
├── start-demo.ps1                       # One-command Windows launcher
├── backend/
│   ├── pyproject.toml                   # Python dependencies and pytest config
│   ├── app/
│   │   ├── main.py                      # FastAPI app and router registration
│   │   ├── config.py                    # Environment settings
│   │   ├── db.py                        # Engine/session/init functions
│   │   ├── schemas.py                   # Public API models
│   │   ├── seed.py                      # Deterministic business and requirement data
│   │   ├── api/
│   │   │   ├── chat.py                  # Conversation and analysis endpoints
│   │   │   ├── knowledge.py             # Knowledge and sync endpoints
│   │   │   ├── dashboards.py            # Dashboard endpoints
│   │   │   └── requirements.py          # Traceability endpoint
│   │   └── services/
│   │       ├── sql_guard.py              # Read-only SQL validation/execution
│   │       ├── analysis.py               # Offline and optional LLM engines
│   │       ├── conversation.py           # Context merge and answer orchestration
│   │       ├── knowledge.py              # Fingerprints, priority, links, sync
│   │       └── dashboards.py             # Card/layout persistence
│   └── tests/
│       ├── conftest.py
│       ├── test_db_seed.py
│       ├── test_sql_guard.py
│       ├── test_analysis.py
│       ├── test_chat_api.py
│       ├── test_knowledge_api.py
│       ├── test_dashboards_api.py
│       └── test_requirements_api.py
├── frontend/
│   ├── package.json
│   ├── vite.config.ts
│   ├── src/
│   │   ├── main.tsx
│   │   ├── app.tsx
│   │   ├── styles.css
│   │   ├── api/client.ts
│   │   ├── types.ts
│   │   ├── layout/PlatformShell.tsx
│   │   ├── components/RequirementBadge.tsx
│   │   ├── pages/QueryWorkspace.tsx
│   │   ├── pages/KnowledgeWorkspace.tsx
│   │   ├── pages/DashboardWorkspace.tsx
│   │   ├── pages/RequirementMatrix.tsx
│   │   └── test/
│   │       ├── setup.ts
│   │       ├── query-workspace.test.tsx
│   │       ├── knowledge-workspace.test.tsx
│   │       ├── dashboard-workspace.test.tsx
│   │       └── requirement-matrix.test.tsx
│   └── e2e/demo.spec.ts
└── docs/
    ├── 智能问数优化实施计划书.md
    └── 需求追踪矩阵.md
```

---

### Task 1: Backend foundation and deterministic database

**Files:**
- Create: `backend/pyproject.toml`
- Create: `backend/app/__init__.py`
- Create: `backend/app/config.py`
- Create: `backend/app/db.py`
- Create: `backend/app/seed.py`
- Create: `backend/app/main.py`
- Create: `backend/tests/conftest.py`
- Create: `backend/tests/test_db_seed.py`

**Interfaces:**
- Produces: `Settings(database_url: str, llm_mode: str, query_row_limit: int)`.
- Produces: `get_engine(database_url: str) -> Engine`, `init_database(engine: Engine) -> None`, and `get_session() -> Iterator[Session]`.
- Produces: FastAPI `app` with `GET /api/health -> {"status":"ok","mode":"offline"}`.
- Seeds: `house_price_monthly`, `housing_transactions`, `district_population`, `commuting_metrics`, and `requirement_mappings`.

- [ ] **Step 1: Create dependency configuration and the failing seed test**

```toml
# backend/pyproject.toml
[project]
name = "geniusq-daas-platform"
version = "0.1.0"
requires-python = ">=3.9"
dependencies = [
  "fastapi>=0.115,<1",
  "uvicorn[standard]>=0.30,<1",
  "sqlmodel>=0.0.22,<1",
  "pydantic-settings>=2.5,<3",
  "httpx>=0.27,<1"
]

[project.optional-dependencies]
test = ["pytest>=8,<9", "pytest-cov>=5,<7"]

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["."]
```

```python
# backend/tests/test_db_seed.py
from sqlalchemy import inspect, text

from app.db import get_engine, init_database


def test_init_database_seeds_business_tables(tmp_path):
    engine = get_engine(f"sqlite:///{tmp_path / 'demo.db'}")
    init_database(engine)

    assert {
        "house_price_monthly",
        "housing_transactions",
        "district_population",
        "commuting_metrics",
        "requirement_mappings",
    }.issubset(inspect(engine).get_table_names())
    with engine.connect() as connection:
        count = connection.execute(text("select count(*) from house_price_monthly")).scalar_one()
    assert count >= 24
```

- [ ] **Step 2: Install backend test dependencies and verify RED**

Run: `python -m pip install -e "backend[test]" && python -m pytest backend/tests/test_db_seed.py -v`

Expected: FAIL with `ModuleNotFoundError: No module named 'app.db'`.

- [ ] **Step 3: Implement settings, engine, schema creation, seeding, and health route**

```python
# backend/app/config.py
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "sqlite:///./daas_demo.db"
    llm_mode: str = "offline"
    query_row_limit: int = 500
    llm_base_url: str = ""
    llm_api_key: str = ""
    llm_model: str = ""
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
```

```python
# backend/app/db.py
from collections.abc import Iterator
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session
from .config import get_settings
from .seed import create_schema, seed_all


def get_engine(database_url: str) -> Engine:
    return create_engine(database_url, connect_args={"check_same_thread": False})


engine = get_engine(get_settings().database_url)


def init_database(target: Engine = engine) -> None:
    create_schema(target)
    seed_all(target)


def get_session() -> Iterator[Session]:
    with Session(engine) as session:
        yield session
```

Implement `seed.py` with explicit `CREATE TABLE IF NOT EXISTS` statements and idempotent `INSERT OR IGNORE` rows for six Beijing districts across 2024–2025, plus all 15 traceability rows defined in the design spec.

```python
# backend/app/main.py
from contextlib import asynccontextmanager
from fastapi import FastAPI
from .config import get_settings
from .db import init_database


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_database()
    yield


app = FastAPI(title="GeniusQ DaaS Platform 智能问数优化 Demo", lifespan=lifespan)


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok", "mode": get_settings().llm_mode}
```

- [ ] **Step 4: Verify GREEN**

Run: `python -m pytest backend/tests/test_db_seed.py -v`

Expected: `1 passed`.

- [ ] **Step 5: Commit foundation**

```powershell
git add backend
git commit -m "feat: seed deterministic DAAS demo data"
```

---

### Task 2: Read-only SQL guard and offline analysis engine

**Files:**
- Create: `backend/app/schemas.py`
- Create: `backend/app/services/__init__.py`
- Create: `backend/app/services/sql_guard.py`
- Create: `backend/app/services/analysis.py`
- Create: `backend/tests/test_sql_guard.py`
- Create: `backend/tests/test_analysis.py`

**Interfaces:**
- Produces: `validate_read_only_sql(sql: str, allowed_tables: set[str]) -> str`.
- Produces: `execute_read_only(engine: Engine, sql: str, row_limit: int) -> list[dict[str, object]]`.
- Produces: `AnalysisEngine.analyze(question: str, context: QueryContext) -> AnalysisPlan`.
- `AnalysisPlan` contains `needs_clarification`, `suggestions`, `steps`, `queries`, `chart`, `insights`, and `follow_ups`.

- [ ] **Step 1: Write failing SQL safety tests**

```python
# backend/tests/test_sql_guard.py
import pytest
from app.services.sql_guard import SqlSafetyError, validate_read_only_sql


ALLOWED = {"house_price_monthly", "housing_transactions"}


def test_accepts_single_select_from_allowed_table():
    sql = validate_read_only_sql(
        "SELECT district, avg_price FROM house_price_monthly", ALLOWED
    )
    assert sql.startswith("SELECT")


@pytest.mark.parametrize("sql", [
    "DELETE FROM house_price_monthly",
    "SELECT 1; DROP TABLE house_price_monthly",
    "PRAGMA table_info(house_price_monthly)",
    "SELECT * FROM secret_users",
])
def test_rejects_unsafe_sql(sql):
    with pytest.raises(SqlSafetyError):
        validate_read_only_sql(sql, ALLOWED)
```

- [ ] **Step 2: Run SQL tests and verify RED**

Run: `python -m pytest backend/tests/test_sql_guard.py -v`

Expected: FAIL because `app.services.sql_guard` does not exist.

- [ ] **Step 3: Implement the minimal SQL guard**

```python
# backend/app/services/sql_guard.py
import re
from sqlalchemy import Engine, text


class SqlSafetyError(ValueError):
    pass


FORBIDDEN = re.compile(
    r"\b(insert|update|delete|drop|alter|create|replace|truncate|attach|detach|pragma|vacuum)\b",
    re.IGNORECASE,
)
TABLE_REF = re.compile(r"\b(?:from|join)\s+([A-Za-z_][A-Za-z0-9_]*)", re.IGNORECASE)


def validate_read_only_sql(sql: str, allowed_tables: set[str]) -> str:
    normalized = sql.strip()
    if ";" in normalized.rstrip(";") or not re.match(r"^(select|with)\b", normalized, re.I):
        raise SqlSafetyError("仅允许执行单条 SELECT 或 WITH 查询")
    if FORBIDDEN.search(normalized):
        raise SqlSafetyError("查询包含被禁止的 SQL 操作")
    referenced = set(TABLE_REF.findall(normalized))
    if not referenced or not referenced.issubset(allowed_tables):
        raise SqlSafetyError("查询访问了未授权数据表")
    return normalized.rstrip(";")


def execute_read_only(engine: Engine, sql: str, row_limit: int = 500):
    guarded = f"SELECT * FROM ({sql}) AS safe_query LIMIT {int(row_limit)}"
    with engine.connect() as connection:
        return [dict(row) for row in connection.execute(text(guarded)).mappings()]
```

- [ ] **Step 4: Verify SQL tests pass**

Run: `python -m pytest backend/tests/test_sql_guard.py -v`

Expected: all parameterized cases pass.

- [ ] **Step 5: Write failing offline-analysis tests**

```python
# backend/tests/test_analysis.py
from app.schemas import QueryContext
from app.services.analysis import OfflineAnalysisEngine


def test_incomplete_house_price_question_returns_suggestions():
    plan = OfflineAnalysisEngine().analyze("分析房价", QueryContext())
    assert plan.needs_clarification is True
    assert len(plan.suggestions) == 3
    assert plan.queries == []


def test_cross_source_question_splits_into_multiple_queries():
    plan = OfflineAnalysisEngine().analyze(
        "2025年房价上涨是否与人口和通勤相关", QueryContext()
    )
    assert plan.needs_clarification is False
    assert len(plan.queries) >= 2
    assert {query.source for query in plan.queries} == {"房产数据", "人口通勤数据"}
    assert "5" in plan.requirement_ids
```

- [ ] **Step 6: Run analysis tests and verify RED**

Run: `python -m pytest backend/tests/test_analysis.py -v`

Expected: FAIL because `OfflineAnalysisEngine` is missing.

- [ ] **Step 7: Implement public schemas and deterministic analysis plans**

```python
# backend/app/schemas.py
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
```

Implement `OfflineAnalysisEngine` with three explicit intent branches: incomplete house-price question, complete house-price trend question, and cross-source correlation question. Each complete branch returns auditable steps, parameter-free demo SQL against allowed tables, a chart spec, deterministic insights, follow-up questions, and requirement ids.

- [ ] **Step 8: Verify analysis tests and the full backend suite**

Run: `python -m pytest backend/tests -v`

Expected: all tests pass.

- [ ] **Step 9: Commit analysis core**

```powershell
git add backend/app/schemas.py backend/app/services backend/tests
git commit -m "feat: add safe offline analysis engine"
```

---

### Task 3: Conversation context and chat API

**Files:**
- Create: `backend/app/services/conversation.py`
- Create: `backend/app/api/__init__.py`
- Create: `backend/app/api/chat.py`
- Modify: `backend/app/main.py`
- Create: `backend/tests/test_chat_api.py`

**Interfaces:**
- Consumes: `OfflineAnalysisEngine.analyze(question, context)` and `execute_read_only`.
- Produces: `POST /api/conversations -> ConversationResponse`.
- Produces: `POST /api/chat` body `{conversation_id, question}` -> clarification or completed analysis.
- Produces: `GET /api/analysis/{analysis_id} -> AnalysisResponse`.

- [ ] **Step 1: Write failing API tests for clarification and context inheritance**

```python
# backend/tests/test_chat_api.py
def test_incomplete_question_returns_recommendations(client):
    conversation = client.post("/api/conversations").json()
    response = client.post("/api/chat", json={
        "conversation_id": conversation["id"], "question": "分析房价"
    })
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "needs_clarification"
    assert len(body["suggestions"]) == 3
    assert body["queries"] == []


def test_follow_up_inherits_year_and_overrides_district(client):
    conversation_id = client.post("/api/conversations").json()["id"]
    first = client.post("/api/chat", json={
        "conversation_id": conversation_id,
        "question": "分析2025年各区平均房价",
    }).json()
    second = client.post("/api/chat", json={
        "conversation_id": conversation_id,
        "question": "只看海淀区",
    }).json()
    assert first["context"]["year_from"] == 2025
    assert second["context"] == {
        "year_from": 2025, "year_to": 2025, "district": "海淀区", "metric": "平均房价"
    }
```

- [ ] **Step 2: Run tests and verify RED**

Run: `python -m pytest backend/tests/test_chat_api.py -v`

Expected: FAIL with 404 for `/api/conversations`.

- [ ] **Step 3: Implement context merge and endpoints**

```python
# backend/app/services/conversation.py
import re
from app.schemas import QueryContext


DISTRICTS = ("海淀区", "朝阳区", "西城区", "东城区", "丰台区", "昌平区")


def merge_context(previous: QueryContext, question: str) -> QueryContext:
    values = previous.model_dump()
    years = [int(value) for value in re.findall(r"20\d{2}", question)]
    if years:
        values["year_from"], values["year_to"] = min(years), max(years)
    for district in DISTRICTS:
        if district in question:
            values["district"] = district
    if "房价" in question:
        values["metric"] = "平均房价"
    return QueryContext(**values)
```

Use UUID strings for conversations and analyses. Persist conversation context and API responses as JSON in the seeded application tables. Execute each plan query through the guard, merge cross-source result groups under `datasets`, and calculate insights from returned rows. Register the chat router in `main.py` under `/api`.

- [ ] **Step 4: Verify chat tests and regression suite**

Run: `python -m pytest backend/tests/test_chat_api.py backend/tests/test_analysis.py backend/tests/test_sql_guard.py -v`

Expected: all tests pass.

- [ ] **Step 5: Commit chat workflow**

```powershell
git add backend/app backend/tests/test_chat_api.py
git commit -m "feat: add contextual intelligent query API"
```

---

### Task 4: Knowledge deduplication, priority, links, and sync

**Files:**
- Create: `backend/app/services/knowledge.py`
- Create: `backend/app/api/knowledge.py`
- Modify: `backend/app/main.py`
- Create: `backend/tests/test_knowledge_api.py`

**Interfaces:**
- Produces: `normalize_sql(sql: str) -> str` and `knowledge_fingerprint(kind: str, content: str, linked_tables: list[str]) -> str`.
- Produces: CRUD routes at `/api/knowledge`.
- Produces: `POST /api/knowledge/deduplicate` with `duplicate`, `existing_id`, and `priority`.
- Produces: `POST /api/sync` and `GET /api/sync/logs`.
- Produces: `DELETE /api/data-tables/{table_name}?confirm=true` for deletion-linkage demonstration.
- Produces: `run_sync(mode: str, session: Session) -> dict[str, object]`, shared by both sync modes.

- [ ] **Step 1: Write failing tests for same-library duplicates and private priority**

```python
# backend/tests/test_knowledge_api.py
def test_same_library_duplicate_is_rejected(client):
    item = {
        "name": "行政区房价口径", "kind": "text", "scope": "private",
        "library": "个人知识库", "content": "平均房价按行政区和月份统计",
        "linked_tables": ["house_price_monthly"], "tags": ["房价", "指标口径"],
    }
    assert client.post("/api/knowledge", json=item).status_code == 201
    duplicate = client.post("/api/knowledge", json=item)
    assert duplicate.status_code == 409
    assert duplicate.json()["code"] == "KNOWLEDGE_DUPLICATE"


def test_private_item_overrides_public_match(client):
    public_id = create_knowledge(client, scope="public", library="公共知识库")
    result = client.post("/api/knowledge/deduplicate", json={
        "name": "行政区房价口径", "kind": "text", "scope": "private",
        "library": "个人知识库", "content": "平均房价按行政区和月份统计",
        "linked_tables": ["house_price_monthly"], "tags": ["房价"],
    }).json()
    assert result["duplicate"] is False
    assert result["priority"] == "private_over_public"
    assert result["overrides_id"] == public_id
```

- [ ] **Step 2: Run knowledge tests and verify RED**

Run: `python -m pytest backend/tests/test_knowledge_api.py -v`

Expected: FAIL with 404 for `/api/knowledge`.

- [ ] **Step 3: Implement canonical fingerprints and knowledge routes**

```python
# backend/app/services/knowledge.py
import hashlib, json, re


def normalize_sql(sql: str) -> str:
    return re.sub(r"\s+", " ", sql.strip().lower()).rstrip(";")


def knowledge_fingerprint(kind: str, content: str, linked_tables: list[str]) -> str:
    canonical = {
        "kind": kind,
        "content": normalize_sql(content) if kind == "sql" else " ".join(content.split()),
        "linked_tables": sorted(linked_tables),
    }
    raw = json.dumps(canonical, ensure_ascii=False, sort_keys=True).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()
```

Implement list filters for `query`, `kind`, `scope`, and `tag`; store links and tags as normalized JSON arrays; return public/private override relationships; extract table names from SQL using the same `FROM/JOIN` parser as the SQL guard.

- [ ] **Step 4: Add failing sync and deletion-linkage tests**

```python
def test_manual_and_scheduled_demo_sync_share_audit_shape(client):
    manual = client.post("/api/sync", json={"mode": "manual"}).json()
    scheduled = client.post("/api/sync", json={"mode": "scheduled_demo"}).json()
    assert manual["status"] == scheduled["status"] == "completed"
    logs = client.get("/api/sync/logs").json()
    assert {row["mode"] for row in logs} >= {"manual", "scheduled_demo"}


def test_table_delete_requires_confirmation_and_removes_links(client):
    preview = client.delete("/api/data-tables/house_price_monthly")
    assert preview.status_code == 409
    assert preview.json()["affected_knowledge_count"] >= 1
    confirmed = client.delete("/api/data-tables/house_price_monthly?confirm=true")
    assert confirmed.status_code == 200
    assert confirmed.json()["linked_items_removed"] >= 1
```

- [ ] **Step 5: Verify the new tests fail for missing sync routes**

Run: `python -m pytest backend/tests/test_knowledge_api.py -v`

Expected: duplicate tests pass; sync tests FAIL with 404.

- [ ] **Step 6: Implement sync audit and confirmed deletion linkage**

Use one `run_sync(mode, session)` service for both modes. It upserts known demo table metadata, marks changed SQL links as `needs_review`, and appends a sync log. The delete route first returns affected items; with `confirm=true`, it marks the table unavailable and deletes linked knowledge records in one transaction.

- [ ] **Step 7: Verify knowledge tests and full backend suite**

Run: `python -m pytest backend/tests -v`

Expected: all tests pass.

- [ ] **Step 8: Commit knowledge domain**

```powershell
git add backend/app backend/tests/test_knowledge_api.py
git commit -m "feat: add traceable knowledge management workflow"
```

---

### Task 5: Dashboards and canonical requirement mapping API

**Files:**
- Create: `backend/app/services/dashboards.py`
- Create: `backend/app/api/dashboards.py`
- Create: `backend/app/api/requirements.py`
- Modify: `backend/app/main.py`
- Create: `backend/tests/test_dashboards_api.py`
- Create: `backend/tests/test_requirements_api.py`

**Interfaces:**
- Produces: dashboard create/list/detail routes and card add/layout patch routes.
- Produces: `GET /api/dashboards/share/{share_id}` without authentication for local demo.
- Produces: `GET /api/requirements?module=&priority=`.

- [ ] **Step 1: Write failing dashboard persistence test**

```python
# backend/tests/test_dashboards_api.py
def test_dashboard_round_trip_preserves_card_layout(client):
    dashboard = client.post("/api/dashboards", json={"name": "房价分析看板"}).json()
    card = client.post(f"/api/dashboards/{dashboard['id']}/cards", json={
        "title": "各区平均房价", "analysis_id": "demo-analysis",
        "chart": {"type": "bar", "x_field": "district", "y_fields": ["avg_price"]},
        "layout": {"x": 0, "y": 0, "w": 6, "h": 4},
    }).json()
    client.patch(f"/api/dashboards/{dashboard['id']}/layout", json={
        "cards": [{"id": card["id"], "x": 6, "y": 0, "w": 6, "h": 5}]
    })
    saved = client.get(f"/api/dashboards/{dashboard['id']}").json()
    assert saved["cards"][0]["layout"] == {"x": 6, "y": 0, "w": 6, "h": 5}
    assert saved["share_id"]
```

- [ ] **Step 2: Write failing requirement coverage test**

```python
# backend/tests/test_requirements_api.py
def test_requirement_endpoint_contains_every_shimo_item(client):
    rows = client.get("/api/requirements").json()
    ids = {row["id"] for row in rows}
    assert ids == {
        "2.1-a", "2.1-b", "2.1-c", "2.2", "2.3", "2.4-a", "2.4-b",
        "2.5", "2.6", "3.2", "3.3", "3.4-a", "3.4-b", "3.4-c", "5",
    }
    assert all(row["page"] and row["acceptance"] for row in rows)
```

- [ ] **Step 3: Run both tests and verify RED**

Run: `python -m pytest backend/tests/test_dashboards_api.py backend/tests/test_requirements_api.py -v`

Expected: FAIL with 404 responses.

- [ ] **Step 4: Implement dashboard and requirements routers**

Persist each dashboard and card as rows, validate layout values as non-negative integers, generate a stable UUID share id, and serialize cards ordered by `(y, x)`. Query the seeded `requirement_mappings` table and support exact module/priority filters.

- [ ] **Step 5: Verify backend suite**

Run: `python -m pytest backend/tests -v --cov=app --cov-report=term-missing`

Expected: all tests pass and no new domain service is untested.

- [ ] **Step 6: Commit backend completion**

```powershell
git add backend
git commit -m "feat: add dashboards and requirement traceability API"
```

---

### Task 6: Frontend foundation and platform shell

**Files:**
- Create: `frontend/package.json`
- Create: `frontend/index.html`
- Create: `frontend/tsconfig.json`
- Create: `frontend/vite.config.ts`
- Create: `frontend/src/main.tsx`
- Create: `frontend/src/app.tsx`
- Create: `frontend/src/styles.css`
- Create: `frontend/src/types.ts`
- Create: `frontend/src/api/client.ts`
- Create: `frontend/src/layout/PlatformShell.tsx`
- Create: `frontend/src/components/RequirementBadge.tsx`
- Create: `frontend/src/test/setup.ts`
- Create: `frontend/src/test/requirement-badge.test.tsx`

**Interfaces:**
- Produces: `api.get<T>()`, `api.post<T>()`, `api.patch<T>()`, and `api.delete<T>()`.
- Produces: `<PlatformShell />` with routes for query, knowledge, dashboards, and requirements.
- Produces: `<RequirementBadge id="2.3" />` linking to `/requirements?id=2.3`.

- [ ] **Step 1: Create frontend config and failing badge test**

```json
// frontend/package.json
{
  "name": "geniusq-daas-platform-ui",
  "private": true,
  "type": "module",
  "scripts": {
    "dev": "vite --host 127.0.0.1",
    "build": "tsc -b && vite build",
    "test": "vitest",
    "test:run": "vitest run",
    "e2e": "playwright test"
  },
  "dependencies": {
    "@tanstack/react-query": "^5.0.0",
    "echarts": "^5.5.0",
    "react": "^18.3.0",
    "react-dom": "^18.3.0",
    "react-router-dom": "^6.28.0"
  },
  "devDependencies": {
    "@playwright/test": "^1.49.0",
    "@testing-library/jest-dom": "^6.6.0",
    "@testing-library/react": "^16.1.0",
    "@testing-library/user-event": "^14.5.0",
    "@types/react": "^18.3.0",
    "@types/react-dom": "^18.3.0",
    "@vitejs/plugin-react": "^4.3.0",
    "jsdom": "^25.0.0",
    "msw": "^2.6.0",
    "typescript": "^5.7.0",
    "vite": "^6.0.0",
    "vitest": "^2.1.0"
  }
}
```

```tsx
// frontend/src/test/requirement-badge.test.tsx
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { RequirementBadge } from "../components/RequirementBadge";

test("links a feature to its canonical requirement row", () => {
  render(<MemoryRouter><RequirementBadge id="2.3" /></MemoryRouter>);
  expect(screen.getByRole("link", { name: "需求 2.3" }))
    .toHaveAttribute("href", "/requirements?id=2.3");
});
```

- [ ] **Step 2: Install packages and verify RED**

Run: `cd frontend; npm.cmd install; npm.cmd run test:run -- src/test/requirement-badge.test.tsx`

Expected: FAIL because `RequirementBadge` does not exist.

- [ ] **Step 3: Implement the badge, shell, routes, API client, and base theme**

```tsx
// frontend/src/components/RequirementBadge.tsx
import { Link } from "react-router-dom";

export function RequirementBadge({ id }: { id: string }) {
  return <Link className="requirement-badge" to={`/requirements?id=${id}`}>需求 {id}</Link>;
}
```

`PlatformShell` renders the logo text, top-level modules, left navigation, main outlet, and user/help area. `styles.css` defines the screenshot-derived colors `#111923`, `#0878df`, `#f5f7fa`, `#ffffff`, 1px pale borders, and compact 12–14px data-platform typography. `app.tsx` lazy-loads the four workspace pages.

- [ ] **Step 4: Verify component test and production build**

Run: `cd frontend; npm.cmd run test:run; npm.cmd run build`

Expected: tests pass; Vite writes `frontend/dist` with exit code 0.

- [ ] **Step 5: Commit frontend foundation**

```powershell
git add frontend
git commit -m "feat: add DAAS platform shell"
```

---

### Task 7: Intelligent query workspace

**Files:**
- Create: `frontend/src/pages/QueryWorkspace.tsx`
- Create: `frontend/src/components/ThinkingTimeline.tsx`
- Create: `frontend/src/components/DataSourcePanel.tsx`
- Create: `frontend/src/components/AnalysisChart.tsx`
- Create: `frontend/src/test/query-workspace.test.tsx`

**Interfaces:**
- Consumes: `POST /api/conversations`, `POST /api/chat`, and dashboard card endpoint.
- Produces: question composer, clarification suggestions, multi-step timeline, SQL, chart, insights, follow-ups, and “加入仪表盘”.

- [ ] **Step 1: Write failing clarification-flow test**

```tsx
// frontend/src/test/query-workspace.test.tsx
test("submits an incomplete question and offers clickable suggestions", async () => {
  server.use(
    http.post("/api/conversations", () => HttpResponse.json({ id: "c1" })),
    http.post("/api/chat", () => HttpResponse.json({
      status: "needs_clarification", analysis_id: "a1", queries: [],
      suggestions: ["分析2025年各区平均房价", "分析2024—2025年房价趋势", "只看海淀区房价"],
      requirement_ids: ["2.2"],
    })),
  );
  renderQueryWorkspace();
  await userEvent.type(screen.getByPlaceholderText("请输入想分析的问题"), "分析房价");
  await userEvent.click(screen.getByRole("button", { name: "发送" }));
  expect(await screen.findByText("分析2025年各区平均房价")).toBeVisible();
  expect(screen.getByRole("link", { name: "需求 2.2" })).toBeVisible();
});
```

- [ ] **Step 2: Run test and verify RED**

Run: `cd frontend; npm.cmd run test:run -- src/test/query-workspace.test.tsx`

Expected: FAIL because `QueryWorkspace` is missing.

- [ ] **Step 3: Implement clarification and completed-analysis rendering**

Use React Query mutations. Keep the conversation id for the page lifetime. Render user and assistant messages, suggestion buttons, collapsible execution steps, source metadata, model Skill card, SQL blocks, ECharts output, deterministic insight cards, and follow-up buttons. Add requirement badges beside each relevant section.

- [ ] **Step 4: Add failing tests for timeline expansion and dashboard save**

```tsx
test("expands auditable steps and saves the chart to a dashboard", async () => {
  server.use(completedAnalysisHandlers());
  renderQueryWorkspace();
  await askQuestion("分析2024—2025年各区平均房价变化");
  await userEvent.click(await screen.findByRole("button", { name: "查看思考过程" }));
  expect(screen.getByText("选择数据表与字段")).toBeVisible();
  expect(screen.getByText("house_price_monthly")).toBeVisible();
  await userEvent.click(screen.getByRole("button", { name: "加入仪表盘" }));
  expect(await screen.findByText("已加入“房价分析看板”")).toBeVisible();
});
```

- [ ] **Step 5: Verify the new test fails, implement save feedback, then verify GREEN**

Run twice around the implementation: `cd frontend; npm.cmd run test:run -- src/test/query-workspace.test.tsx`

Expected RED: missing timeline/save behavior. Expected GREEN after implementation: all query workspace tests pass.

- [ ] **Step 6: Commit intelligent query UI**

```powershell
git add frontend/src
git commit -m "feat: build traceable intelligent query workspace"
```

---

### Task 8: Knowledge, dashboard, and requirement workspaces

**Files:**
- Create: `frontend/src/pages/KnowledgeWorkspace.tsx`
- Create: `frontend/src/pages/DashboardWorkspace.tsx`
- Create: `frontend/src/pages/RequirementMatrix.tsx`
- Create: `frontend/src/test/knowledge-workspace.test.tsx`
- Create: `frontend/src/test/dashboard-workspace.test.tsx`
- Create: `frontend/src/test/requirement-matrix.test.tsx`

**Interfaces:**
- Consumes: all knowledge, sync, dashboard, and requirements API routes.
- Produces: filters, duplicate conflict view, priority indicators, linked-table details, sync logs, dashboard card layout controls, share view, and traceability table.

- [ ] **Step 1: Write failing knowledge-conflict test**

```tsx
test("shows that private knowledge overrides a public match", async () => {
  server.use(knowledgeHandlersWithConflict());
  renderKnowledgeWorkspace();
  await userEvent.click(await screen.findByText("行政区房价口径"));
  expect(screen.getByText("私有知识优先")).toBeVisible();
  expect(screen.getByText("公开条目被覆盖")).toBeVisible();
  expect(screen.getByRole("link", { name: "需求 3.2" })).toBeVisible();
});
```

- [ ] **Step 2: Run test and verify RED**

Run: `cd frontend; npm.cmd run test:run -- src/test/knowledge-workspace.test.tsx`

Expected: FAIL because the page is missing.

- [ ] **Step 3: Implement knowledge tabs, filters, conflict details, sync, and delete preview**

The page uses a three-column workspace: dark secondary navigation, table/list, and details. The delete action first renders the backend’s affected-knowledge preview and only sends `confirm=true` after explicit confirmation.

- [ ] **Step 4: Write failing dashboard and traceability tests**

```tsx
test("persists a resized dashboard card", async () => {
  server.use(dashboardHandlers());
  renderDashboardWorkspace();
  await userEvent.click(await screen.findByRole("button", { name: "放大卡片" }));
  expect(await screen.findByText("布局已保存")).toBeVisible();
});

test("filters requirement rows by module and preserves every source id", async () => {
  server.use(requirementHandlers());
  renderRequirementMatrix();
  await userEvent.selectOptions(await screen.findByLabelText("模块"), "知识库管理");
  expect(screen.getByText("3.2")).toBeVisible();
  expect(screen.queryByText("2.3")).not.toBeInTheDocument();
});
```

- [ ] **Step 5: Run tests and verify RED**

Run: `cd frontend; npm.cmd run test:run -- src/test/dashboard-workspace.test.tsx src/test/requirement-matrix.test.tsx`

Expected: FAIL because both pages are missing.

- [ ] **Step 6: Implement dashboard and requirement pages**

Use button-based move/resize controls rather than a heavy drag library so layout remains keyboard-accessible and deterministic. Provide refresh, remove, share-link copy, chart-type switch, module/priority filters, and expandable acceptance details.

- [ ] **Step 7: Verify all frontend tests and build**

Run: `cd frontend; npm.cmd run test:run; npm.cmd run build`

Expected: all Vitest tests pass and the production build exits 0.

- [ ] **Step 8: Commit remaining workspaces**

```powershell
git add frontend/src
git commit -m "feat: add knowledge dashboards and requirement matrix"
```

---

### Task 9: Formal proposal, traceability document, and one-command launcher

**Files:**
- Create: `.env.example`
- Create: `README.md`
- Create: `start-demo.ps1`
- Create: `docs/智能问数优化实施计划书.md`
- Create: `docs/需求追踪矩阵.md`
- Create: `backend/tests/test_documentation.py`

**Interfaces:**
- Produces: `start-demo.ps1 [-NoBrowser]` that initializes and starts API on `127.0.0.1:8000` and Vite on `127.0.0.1:5173`.
- Produces: proposal sections for background, issues, goals, architecture, phases, staffing, risks, acceptance, and requirement mapping.

- [ ] **Step 1: Write failing documentation coverage test**

```python
# backend/tests/test_documentation.py
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
REQUIREMENT_IDS = {
    "2.1-a", "2.1-b", "2.1-c", "2.2", "2.3", "2.4-a", "2.4-b",
    "2.5", "2.6", "3.2", "3.3", "3.4-a", "3.4-b", "3.4-c", "5",
}


def test_proposal_and_matrix_cover_every_requirement():
    proposal = (ROOT / "docs/智能问数优化实施计划书.md").read_text(encoding="utf-8")
    matrix = (ROOT / "docs/需求追踪矩阵.md").read_text(encoding="utf-8")
    for requirement_id in REQUIREMENT_IDS:
        assert requirement_id in proposal
        assert requirement_id in matrix


def test_readme_documents_offline_start_and_optional_llm():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "start-demo.ps1" in readme
    assert "LLM_MODE=offline" in readme
    assert "LLM_MODE=openai-compatible" in readme
```

- [ ] **Step 2: Run test and verify RED**

Run: `python -m pytest backend/tests/test_documentation.py -v`

Expected: FAIL because the delivery documents do not exist.

- [ ] **Step 3: Write the formal Chinese proposal and standalone traceability matrix**

The proposal must contain these exact sections: 项目背景、现状问题、建设目标、需求范围、总体方案、功能方案、技术架构、数据与安全、实施阶段与排期、人员分工建议、风险与应对、验收方案、需求追踪矩阵. Use a four-week reference schedule with weekly deliverables, while clearly stating that dates are recommendations for integration into the real platform, not claims about this standalone demo.

- [ ] **Step 4: Implement environment example and launcher**

```dotenv
# .env.example
LLM_MODE=offline
LLM_BASE_URL=
LLM_API_KEY=
LLM_MODEL=
DATABASE_URL=sqlite:///./daas_demo.db
QUERY_ROW_LIMIT=500
```

```powershell
# start-demo.ps1 core behavior
param([switch]$NoBrowser)
$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Backend = Join-Path $Root 'backend'
$Frontend = Join-Path $Root 'frontend'
python -m pip install -e "$Backend[test]"
Push-Location $Frontend
npm.cmd install
Pop-Location
Start-Process python -ArgumentList '-m','uvicorn','app.main:app','--app-dir',$Backend,'--host','127.0.0.1','--port','8000' -WorkingDirectory $Root -WindowStyle Hidden
Start-Process npm.cmd -ArgumentList 'run','dev','--','--port','5173' -WorkingDirectory $Frontend -WindowStyle Hidden
if (-not $NoBrowser) { Start-Process 'http://127.0.0.1:5173' }
```

Add bounded health polling before opening the browser and actionable messages when `python`, `node`, or `npm.cmd` is absent.

- [ ] **Step 5: Verify documentation tests and PowerShell syntax**

Run: `python -m pytest backend/tests/test_documentation.py -v`

Run: `powershell -NoProfile -Command "[void][scriptblock]::Create((Get-Content -Raw './start-demo.ps1')); 'syntax ok'"`

Expected: documentation tests pass and PowerShell prints `syntax ok`.

- [ ] **Step 6: Commit deliverable documentation**

```powershell
git add .env.example README.md start-demo.ps1 docs backend/tests/test_documentation.py
git commit -m "docs: add implementation proposal and local demo guide"
```

---

### Task 10: End-to-end acceptance and final verification

**Files:**
- Create: `frontend/playwright.config.ts`
- Create: `frontend/e2e/demo.spec.ts`
- Modify: `README.md`

**Interfaces:**
- Consumes: running FastAPI and Vite servers.
- Produces: automated browser evidence for the five acceptance journeys in the design spec.

- [ ] **Step 1: Write the first failing Playwright journey**

```ts
// frontend/e2e/demo.spec.ts
import { test, expect } from "@playwright/test";

test("question to chart to dashboard traces requirements 2.1-2.6", async ({ page }) => {
  await page.goto("/");
  await page.getByPlaceholder("请输入想分析的问题").fill("分析2024—2025年各行政区平均房价变化，并找出异常区域");
  await page.getByRole("button", { name: "发送" }).click();
  await expect(page.getByText("数据来源")).toBeVisible();
  await expect(page.getByText("最大值")).toBeVisible();
  await page.getByRole("button", { name: "查看思考过程" }).click();
  await expect(page.getByText("趋势与异常检测 Skill")).toBeVisible();
  await page.getByRole("button", { name: "加入仪表盘" }).click();
  await expect(page.getByText("已加入“房价分析看板”")).toBeVisible();
});
```

- [ ] **Step 2: Start the app and verify Playwright RED**

Run in terminal 1: `powershell -ExecutionPolicy Bypass -File .\start-demo.ps1 -NoBrowser`

Run in terminal 2: `cd frontend; npx.cmd playwright install chromium; npm.cmd run e2e`

Expected: the first journey fails until selectors and live API wiring are complete.

- [ ] **Step 3: Correct live integration defects without changing acceptance expectations**

For each defect, first keep the failing Playwright assertion, fix only the app wiring or accessible label responsible, then rerun the single test with `npm.cmd run e2e -- --grep "question to chart"` until it passes.

- [ ] **Step 4: Add the remaining four acceptance journeys**

Add tests for: multi-turn “只看海淀区”; cross-source house-price/population/commuting split; duplicate knowledge with private priority; manual/scheduled sync and confirmed deletion linkage. Each test asserts its requirement badges and user-visible completion state.

- [ ] **Step 5: Run fresh full verification**

Run: `python -m pytest backend/tests -v --cov=app --cov-report=term-missing`

Run: `cd frontend; npm.cmd run test:run; npm.cmd run build; npm.cmd run e2e`

Run: `git status --short`

Expected: all Pytest tests pass; all Vitest tests pass; Vite build exits 0; all five Playwright journeys pass; only the preserved pre-existing untracked mojibake spec may remain untracked.

- [ ] **Step 6: Perform requirement-by-requirement manual audit**

Open `/requirements` and compare its 15 rows against `docs/需求追踪矩阵.md`. For each row, follow the page link and perform the stated acceptance action. Record no row as complete unless its page, API behavior, and automated or manual check all exist.

- [ ] **Step 7: Commit end-to-end verification assets**

```powershell
git add frontend/e2e frontend/playwright.config.ts README.md
git commit -m "test: cover end-to-end optimization journeys"
```
