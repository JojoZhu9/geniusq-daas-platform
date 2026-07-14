# 极智 DAAS 智能问数优化 Demo Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 交付一份可逐项追踪石墨需求的实施计划书，以及一个在 Windows 本地默认离线运行、可选接入 OpenAI 兼容模型的极智 DAAS 智能问数优化 Demo。

**Architecture:** React + TypeScript 提供与现有平台一致的前端外壳和四个业务页面；FastAPI 负责会话编排、只读 SQL、知识库规则、同步和仪表盘；SQLite 同时保存样例业务数据和应用状态。离线分析引擎以确定性规则完成所有验收路径，真实模型适配器复用同一结构化计划与 SQL 安全管线。

**Tech Stack:** Python 3.9、FastAPI、SQLAlchemy、Pydantic、Pytest、React、TypeScript、Vite、React Router、ECharts、Vitest、Testing Library、SQLite、PowerShell

## Global Constraints

- Demo 必须在不配置模型密钥、断网的情况下完成五条端到端演示路径。
- Demo 不连接公司生产数据库，不修改或复制极智 DAAS 专有源代码。
- 只允许单条 `SELECT` 或 `WITH ... SELECT` 查询；拒绝 DDL、DML、多语句和未知数据表。
- 所有业务功能必须调用真实本地 API，不使用只打印日志的按钮。
- 页面和测试必须使用需求编号：2.1、2.2、2.3、2.4、2.5、2.6、3.2、3.3、3.4、5。
- Windows 启动命令调用 `npm.cmd`，不要求修改 PowerShell 执行策略。
- 后端保持 Python 3.9 兼容；前端保持 Node.js 20 及以上兼容。

---

## File Map

```text
backend/
├── requirements.txt                 # 固定 Python 依赖
├── app/
│   ├── main.py                      # FastAPI 应用与路由挂载
│   ├── config.py                    # 环境配置
│   ├── db.py                        # SQLite 会话与初始化
│   ├── models.py                    # SQLAlchemy 表模型
│   ├── schemas.py                   # API 请求/响应类型
│   ├── seed.py                      # 演示数据与需求映射
│   ├── api/                         # chat、knowledge、dashboard、requirements 路由
│   └── services/                    # analysis、sql_guard、knowledge、sync、dashboard
└── tests/                            # Pytest 行为测试
frontend/
├── package.json                     # 前端脚本和依赖
├── vite.config.ts                   # Vite、代理与测试配置
├── src/
│   ├── api/client.ts                # 类型化 API 客户端
│   ├── app/router.tsx               # 页面路由
│   ├── components/                  # 平台外壳、需求徽标、图表与状态组件
│   ├── pages/                       # 智能问数、知识库、仪表盘、需求映射
│   └── styles/                      # 视觉变量和页面样式
└── src/**/*.test.tsx                # Vitest 组件测试
docs/
├── 智能问数优化实施计划书.md         # 面向评审的正式计划书
└── 需求追踪矩阵.md                   # 石墨条目到实现和测试的映射
.env.example                         # 离线/真实模型配置示例
start-demo.ps1                       # 初始化、启动和打开浏览器
README.md                            # 安装、演示、测试与故障处理
```

### Task 1: Backend Skeleton and Health Contract

**Files:**
- Create: `backend/requirements.txt`
- Create: `backend/app/__init__.py`
- Create: `backend/app/config.py`
- Create: `backend/app/main.py`
- Create: `backend/tests/test_health.py`

**Interfaces:**
- Produces: `create_app() -> FastAPI`
- Produces: `GET /api/health -> {status, mode, database}`

- [ ] **Step 1: Write the failing health test**

```python
from fastapi.testclient import TestClient
from app.main import create_app


def test_health_reports_offline_mode():
    client = TestClient(create_app())
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "mode": "offline",
        "database": "sqlite",
    }
```

- [ ] **Step 2: Run the test and verify RED**

Run: `cd backend; py -m pytest tests/test_health.py -q`

Expected: collection fails with `ModuleNotFoundError: No module named 'app'`.

- [ ] **Step 3: Add dependencies and minimal application**

`backend/requirements.txt` pins `fastapi==0.115.6`, `uvicorn[standard]==0.34.0`, `sqlalchemy==2.0.36`, `pydantic-settings==2.7.1`, `httpx==0.28.1`, `pytest==8.3.4` and `pytest-cov==6.0.0`.

```python
# backend/app/config.py
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_mode: str = "offline"
    database_url: str = "sqlite:///./daas_demo.db"
    llm_base_url: str = ""
    llm_api_key: str = ""
    llm_model: str = ""
    model_config = SettingsConfigDict(env_file="../.env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
```

```python
# backend/app/main.py
from fastapi import FastAPI
from .config import get_settings


def create_app() -> FastAPI:
    app = FastAPI(title="极智 DAAS 智能问数优化 Demo")

    @app.get("/api/health")
    def health() -> dict:
        settings = get_settings()
        return {"status": "ok", "mode": settings.app_mode, "database": "sqlite"}

    return app


app = create_app()
```

- [ ] **Step 4: Verify GREEN**

Run: `cd backend; py -m pytest tests/test_health.py -q`

Expected: `1 passed`.

- [ ] **Step 5: Commit the backend contract**

```powershell
git add backend
git commit -m "feat: add FastAPI health contract"
```

### Task 2: SQLite Schema, Seed Data, and Requirement Catalog

**Files:**
- Create: `backend/app/db.py`
- Create: `backend/app/models.py`
- Create: `backend/app/seed.py`
- Create: `backend/tests/test_seed.py`
- Modify: `backend/app/main.py`

**Interfaces:**
- Produces: `init_database(engine: Engine) -> None`
- Produces: `seed_database(session: Session) -> None`
- Produces tables named `house_price_monthly`, `housing_transactions`, `district_population`, `commuting_metrics`, `requirement_mappings`

- [ ] **Step 1: Write a failing seed test**

```python
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session
from app.db import init_database
from app.models import HousePriceMonthly, RequirementMapping
from app.seed import seed_database


def test_seed_is_idempotent_and_covers_every_requirement():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False})
    init_database(engine)
    with Session(engine) as session:
        seed_database(session)
        seed_database(session)
        prices = session.scalar(select(func.count()).select_from(HousePriceMonthly))
        ids = set(session.scalars(select(RequirementMapping.requirement_id)))
    assert prices == 72
    assert ids == {"2.1", "2.2", "2.3", "2.4", "2.5", "2.6", "3.2", "3.3", "3.4", "5"}
```

- [ ] **Step 2: Verify RED**

Run: `cd backend; py -m pytest tests/test_seed.py -q`

Expected: import fails because `app.db` does not exist.

- [ ] **Step 3: Implement schema and deterministic seed**

Define one SQLAlchemy model per table listed in the file map. Give business rows a unique natural key: `(district, month)` for monthly tables, `(district, year)` for annual tables, and `requirement_id` for requirement mappings. Insert six districts across twelve months so the price table contains exactly 72 records. Seed mappings with page names, API paths and acceptance actions from the approved design.

```python
# backend/app/db.py
from typing import Optional
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from .config import get_settings


class Base(DeclarativeBase):
    pass


def build_engine(url: Optional[str] = None) -> Engine:
    return create_engine(url or get_settings().database_url, connect_args={"check_same_thread": False})


engine = build_engine()
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


def init_database(target: Engine = engine) -> None:
    from . import models
    Base.metadata.create_all(target)
```

- [ ] **Step 4: Verify GREEN and idempotency**

Run: `cd backend; py -m pytest tests/test_seed.py -q`

Expected: `1 passed` and a second seed call does not change counts.

- [ ] **Step 5: Commit data foundation**

```powershell
git add backend/app backend/tests/test_seed.py
git commit -m "feat: add demo schema and seed data"
```

### Task 3: Conversation Context, Clarification, and Read-Only SQL Guard

**Files:**
- Create: `backend/app/services/context.py`
- Create: `backend/app/services/sql_guard.py`
- Create: `backend/tests/test_context.py`
- Create: `backend/tests/test_sql_guard.py`

**Interfaces:**
- Produces: `merge_context(previous: QueryContext, question: str) -> QueryContext`
- Produces: `clarification_for(context: QueryContext) -> list[str]`
- Produces: `validate_readonly_sql(sql: str, allowed_tables: set[str]) -> str`

- [ ] **Step 1: Write failing context and SQL safety tests**

```python
def test_follow_up_inherits_year_and_overrides_district():
    previous = QueryContext(years=[2025], districts=["朝阳区"], metric="avg_price")
    current = merge_context(previous, "只看海淀区")
    assert current.years == [2025]
    assert current.districts == ["海淀区"]
    assert current.metric == "avg_price"


def test_incomplete_question_returns_clickable_suggestions():
    suggestions = clarification_for(QueryContext(metric="avg_price"))
    assert suggestions[0] == "分析 2025 年各行政区平均房价"
    assert len(suggestions) == 3


def test_sql_guard_rejects_write_and_multiple_statements():
    with pytest.raises(UnsafeSqlError):
        validate_readonly_sql("DELETE FROM house_price_monthly", {"house_price_monthly"})
    with pytest.raises(UnsafeSqlError):
        validate_readonly_sql("SELECT 1; SELECT 2", {"house_price_monthly"})


def test_sql_guard_accepts_known_readonly_table():
    sql = "SELECT district, AVG(avg_price) FROM house_price_monthly GROUP BY district"
    assert validate_readonly_sql(sql, {"house_price_monthly"}) == sql
```

- [ ] **Step 2: Verify RED**

Run: `cd backend; py -m pytest tests/test_context.py tests/test_sql_guard.py -q`

Expected: imports fail because both services are absent.

- [ ] **Step 3: Implement deterministic extraction and SQL validation**

Use explicit district, year and metric dictionaries for the offline demo. Normalize full-width punctuation before checking SQL. Reject forbidden keywords `INSERT`, `UPDATE`, `DELETE`, `DROP`, `ALTER`, `CREATE`, `ATTACH`, `PRAGMA`, `REPLACE`, `TRUNCATE`; reject more than one non-empty statement; require the first token to be `SELECT` or `WITH`; extract each `FROM`/`JOIN` identifier and require it in `allowed_tables`; append `LIMIT 500` when absent.

- [ ] **Step 4: Verify GREEN**

Run: `cd backend; py -m pytest tests/test_context.py tests/test_sql_guard.py -q`

Expected: `4 passed`.

- [ ] **Step 5: Commit the query safety boundary**

```powershell
git add backend/app/services backend/tests/test_context.py backend/tests/test_sql_guard.py
git commit -m "feat: add context and readonly SQL guard"
```

### Task 4: Offline Analysis Engine, Multi-Source Planner, and Chat API

**Files:**
- Create: `backend/app/schemas.py`
- Create: `backend/app/services/analysis.py`
- Create: `backend/app/services/llm.py`
- Create: `backend/app/api/chat.py`
- Create: `backend/tests/test_analysis.py`
- Create: `backend/tests/test_chat_api.py`
- Modify: `backend/app/main.py`

**Interfaces:**
- Produces: `AnalysisEngine.analyze(request: AnalysisRequest) -> AnalysisResult`
- Produces: `POST /api/chat`
- Produces: `GET /api/analysis/{analysis_id}`
- Consumes: `merge_context`, `clarification_for`, `validate_readonly_sql`, `SessionLocal`

- [ ] **Step 1: Write failing single-source, follow-up, and multi-source tests**

```python
def test_complete_question_returns_steps_chart_and_insights(client):
    response = client.post("/api/chat", json={"question": "分析 2024—2025 年各行政区平均房价变化"})
    body = response.json()
    assert response.status_code == 200
    assert body["status"] == "completed"
    assert body["requirements"] == ["2.1", "2.4", "2.5"]
    assert body["chart"]["type"] == "line"
    assert any(step["kind"] == "sql_execution" for step in body["steps"])
    assert body["suggestions"]


def test_multi_source_question_executes_multiple_queries(client):
    response = client.post("/api/chat", json={"question": "房价上涨是否与人口和通勤相关"})
    body = response.json()
    assert response.status_code == 200
    assert body["requirements"] == ["5"]
    assert len(body["queries"]) == 3
    assert {query["source"] for query in body["queries"]} == {"housing", "population", "commuting"}
```

- [ ] **Step 2: Verify RED**

Run: `cd backend; py -m pytest tests/test_analysis.py tests/test_chat_api.py -q`

Expected: `/api/chat` returns 404.

- [ ] **Step 3: Implement the offline engine and API**

Return a structured result with `status`, `conversation_id`, `analysis_id`, `answer`, `steps`, `sources`, `queries`, `table`, `chart`, `insights`, `suggestions`, `confidence`, and `requirements`. Persist conversations and analysis steps. For the cross-source question, run one aggregate query against housing, one against population, and one against commuting, merge on district, and compute Pearson-direction summaries without adding a numerical causal claim.

The OpenAI adapter must implement the same interface. It sends schema instructions to the configured compatible endpoint, parses JSON only, validates every returned SQL statement, and reports `MODEL_UNAVAILABLE` with actions `retry` and `use_offline` on transport or schema failure.

- [ ] **Step 4: Verify GREEN and the complete backend suite**

Run: `cd backend; py -m pytest -q`

Expected: every collected test passes.

- [ ] **Step 5: Commit analysis flow**

```powershell
git add backend/app backend/tests
git commit -m "feat: implement offline intelligent query flow"
```

### Task 5: Knowledge Deduplication, Relationships, and Sync

**Files:**
- Create: `backend/app/services/knowledge.py`
- Create: `backend/app/services/sync.py`
- Create: `backend/app/api/knowledge.py`
- Create: `backend/tests/test_knowledge.py`
- Create: `backend/tests/test_sync.py`
- Modify: `backend/app/main.py`

**Interfaces:**
- Produces: `fingerprint_knowledge(payload: KnowledgeCreate) -> str`
- Produces: `create_knowledge(session, payload) -> KnowledgeItem`
- Produces: `sync_table(session, table_name: str, trigger: str) -> SyncResult`
- Produces: `/api/knowledge`, `/api/knowledge/deduplicate`, `/api/sync`, `/api/sync/logs`

- [ ] **Step 1: Write failing priority and sync tests**

```python
def test_same_scope_duplicate_is_rejected(session):
    create_knowledge(session, knowledge_payload(scope="private"))
    with pytest.raises(DuplicateKnowledgeError):
        create_knowledge(session, knowledge_payload(scope="private"))


def test_private_duplicate_overrides_public_without_deleting_it(session):
    public = create_knowledge(session, knowledge_payload(scope="public"))
    private = create_knowledge(session, knowledge_payload(scope="private"))
    result = deduplicate(session, private.fingerprint)
    assert result.preferred_id == private.id
    assert result.overridden_ids == [public.id]


def test_manual_and_scheduled_sync_share_business_logic(session):
    manual = sync_table(session, "house_price_monthly", "manual")
    scheduled = sync_table(session, "house_price_monthly", "scheduled_demo")
    assert manual.rows_seen == scheduled.rows_seen == 72
    assert {manual.trigger, scheduled.trigger} == {"manual", "scheduled_demo"}
```

- [ ] **Step 2: Verify RED**

Run: `cd backend; py -m pytest tests/test_knowledge.py tests/test_sync.py -q`

Expected: service imports fail.

- [ ] **Step 3: Implement normalization, priority, links, filters, and sync logs**

Normalize text by Unicode NFKC, whitespace collapse and lowercase. Normalize SQL by removing comments, collapsing whitespace and removing a trailing semicolon. Hash `type|scope-independent-content|sorted-table-links|rule` with SHA-256. Block same-scope duplicates; preserve public and private copies across scopes; return private as preferred. Extract SQL `FROM`/`JOIN` tables into links. Sync table metadata and row counts; record `manual` or `scheduled_demo`; require explicit confirmation before table-delete linkage removes knowledge.

- [ ] **Step 4: Verify GREEN**

Run: `cd backend; py -m pytest tests/test_knowledge.py tests/test_sync.py -q`

Expected: all knowledge and sync tests pass.

- [ ] **Step 5: Commit knowledge management**

```powershell
git add backend/app backend/tests
git commit -m "feat: add knowledge priority and synchronization"
```

### Task 6: Dashboard Persistence and Requirement Mapping API

**Files:**
- Create: `backend/app/services/dashboard.py`
- Create: `backend/app/api/dashboard.py`
- Create: `backend/app/api/requirements.py`
- Create: `backend/tests/test_dashboard.py`
- Create: `backend/tests/test_requirements.py`
- Modify: `backend/app/main.py`

**Interfaces:**
- Produces: dashboard create/card/layout/share endpoints
- Produces: `GET /api/requirements`

- [ ] **Step 1: Write failing persistence and coverage tests**

```python
def test_dashboard_round_trip_preserves_layout(client):
    dashboard = client.post("/api/dashboards", json={"name": "房价洞察"}).json()
    client.post(f"/api/dashboards/{dashboard['id']}/cards", json={
        "analysis_id": "analysis-1", "title": "各区房价趋势", "chart_type": "line",
        "layout": {"x": 0, "y": 0, "w": 6, "h": 4},
    })
    body = client.get(f"/api/dashboards/{dashboard['id']}").json()
    assert body["cards"][0]["layout"] == {"x": 0, "y": 0, "w": 6, "h": 4}


def test_requirement_api_has_page_api_test_and_acceptance_for_every_item(client):
    rows = client.get("/api/requirements").json()
    assert {row["requirement_id"] for row in rows} == {"2.1", "2.2", "2.3", "2.4", "2.5", "2.6", "3.2", "3.3", "3.4", "5"}
    assert all(row["page"] and row["api"] and row["test"] and row["acceptance"] for row in rows)
```

- [ ] **Step 2: Verify RED**

Run: `cd backend; py -m pytest tests/test_dashboard.py tests/test_requirements.py -q`

Expected: dashboard and requirement routes return 404.

- [ ] **Step 3: Implement CRUD, layout patching, local share tokens, and mapping read API**

Generate an unguessable share token with `secrets.token_urlsafe(18)` and expose a read-only `/api/shared/{token}` view. Validate card layout values: `x >= 0`, `y >= 0`, `1 <= w <= 12`, `1 <= h <= 12`. Return requirement rows sorted by numeric module and submodule.

- [ ] **Step 4: Verify GREEN and backend coverage**

Run: `cd backend; py -m pytest --cov=app --cov-report=term-missing -q`

Expected: all tests pass and service-module line coverage is at least 80%.

- [ ] **Step 5: Commit dashboard and traceability API**

```powershell
git add backend/app backend/tests
git commit -m "feat: persist dashboards and requirement mappings"
```

### Task 7: React Platform Shell and Typed API Client

**Files:**
- Create: `frontend/package.json`
- Create: `frontend/index.html`
- Create: `frontend/tsconfig.json`
- Create: `frontend/vite.config.ts`
- Create: `frontend/src/main.tsx`
- Create: `frontend/src/api/client.ts`
- Create: `frontend/src/app/router.tsx`
- Create: `frontend/src/components/PlatformShell.tsx`
- Create: `frontend/src/components/RequirementBadge.tsx`
- Create: `frontend/src/styles/tokens.css`
- Create: `frontend/src/components/PlatformShell.test.tsx`

**Interfaces:**
- Produces: `api.get/post/patch/delete<T>()`
- Produces routes `/ask`, `/knowledge`, `/dashboards`, `/requirements`
- Produces `RequirementBadge({id})`

- [ ] **Step 1: Write a failing shell test**

```tsx
it('renders the DAAS shell and active intelligent query navigation', () => {
  render(<MemoryRouter initialEntries={['/ask']}><PlatformShell /></MemoryRouter>)
  expect(screen.getByText('极智｜数据分析建模平台')).toBeInTheDocument()
  expect(screen.getByRole('link', { name: '智能问数' })).toHaveAttribute('aria-current', 'page')
  expect(screen.getByRole('link', { name: '知识库管理' })).toBeInTheDocument()
})
```

- [ ] **Step 2: Install dependencies and verify RED**

Run: `cd frontend; npm.cmd install; npm.cmd test -- --run src/components/PlatformShell.test.tsx`

Expected: test compilation fails because `PlatformShell` is absent.

- [ ] **Step 3: Implement the shell, router, tokens, and client**

Use CSS variables `--topbar:#111923`, `--primary:#0878df`, `--surface:#ffffff`, `--canvas:#f5f7fa`, `--border:#dfe5ec`, `--text:#1f2937`. The shell has a 52px top bar, a 168px left navigation, a flexible main region, and a 300px optional context panel. Requirement badges link to `/requirements?selected={id}`.

- [ ] **Step 4: Verify GREEN and production compilation**

Run: `cd frontend; npm.cmd test -- --run; npm.cmd run build`

Expected: shell test passes and Vite writes `frontend/dist`.

- [ ] **Step 5: Commit frontend foundation**

```powershell
git add frontend
git commit -m "feat: add DAAS React platform shell"
```

### Task 8: Intelligent Query Workbench

**Files:**
- Create: `frontend/src/pages/AskPage.tsx`
- Create: `frontend/src/components/ThinkingTimeline.tsx`
- Create: `frontend/src/components/DataSourcePanel.tsx`
- Create: `frontend/src/components/ResultChart.tsx`
- Create: `frontend/src/components/SuggestionChips.tsx`
- Create: `frontend/src/pages/AskPage.test.tsx`
- Modify: `frontend/src/app/router.tsx`

**Interfaces:**
- Consumes: `POST /api/chat`, `GET /api/analysis/{id}`
- Produces: complete UI paths for 2.1, 2.2, 2.3, 2.4, 2.5 and 5

- [ ] **Step 1: Write failing interaction tests**

```tsx
it('shows clarification suggestions without a result chart', async () => {
  server.use(http.post('/api/chat', () => HttpResponse.json({
    status: 'needs_clarification', requirements: ['2.2'],
    suggestions: ['分析 2025 年各行政区平均房价', '分析 2024—2025 年房价趋势', '分析海淀区平均房价'],
  })))
  renderAskPage()
  await userEvent.type(screen.getByRole('textbox'), '分析房价')
  await userEvent.click(screen.getByRole('button', { name: '发送' }))
  expect(await screen.findByText('分析 2025 年各行政区平均房价')).toBeInTheDocument()
  expect(screen.queryByTestId('result-chart')).not.toBeInTheDocument()
})


it('expands steps and adds the generated chart to a dashboard', async () => {
  renderAskPageWithCompletedAnalysis()
  await userEvent.click(screen.getByRole('button', { name: '查看思考过程' }))
  expect(await screen.findByText('SQL 执行')).toBeInTheDocument()
  await userEvent.click(screen.getByRole('button', { name: '加入仪表盘' }))
  expect(await screen.findByText('已加入“房价洞察”')).toBeInTheDocument()
})
```

- [ ] **Step 2: Verify RED**

Run: `cd frontend; npm.cmd test -- --run src/pages/AskPage.test.tsx`

Expected: module import fails because `AskPage` is absent.

- [ ] **Step 3: Implement the workbench states**

Implement empty, submitting, needs-clarification, completed, no-data, SQL-rejected and model-unavailable states. Render only auditable business steps, never hidden chain-of-thought. Keep conversation ID for follow-ups. Render source table, updated date, fields, time range and confidence in the right panel. Support table/line/bar chart switching without refetching data.

- [ ] **Step 4: Verify GREEN**

Run: `cd frontend; npm.cmd test -- --run src/pages/AskPage.test.tsx`

Expected: both tests pass.

- [ ] **Step 5: Commit workbench**

```powershell
git add frontend/src
git commit -m "feat: build intelligent query workbench"
```

### Task 9: Knowledge, Dashboard, and Requirement Mapping Pages

**Files:**
- Create: `frontend/src/pages/KnowledgePage.tsx`
- Create: `frontend/src/pages/DashboardPage.tsx`
- Create: `frontend/src/pages/RequirementsPage.tsx`
- Create: `frontend/src/pages/KnowledgePage.test.tsx`
- Create: `frontend/src/pages/DashboardPage.test.tsx`
- Create: `frontend/src/pages/RequirementsPage.test.tsx`
- Modify: `frontend/src/app/router.tsx`

**Interfaces:**
- Consumes: knowledge, sync, dashboard and requirement APIs from Tasks 5–6
- Produces: complete UI paths for 2.6, 3.2, 3.3 and 3.4

- [ ] **Step 1: Write failing page tests**

```tsx
it('shows private knowledge as preferred when public content conflicts', async () => {
  renderKnowledgePageWithConflict()
  expect(await screen.findByText('私有库优先')).toBeInTheDocument()
  expect(screen.getByText('公开条目被覆盖')).toBeInTheDocument()
})


it('filters mappings by requirement number and exposes acceptance action', async () => {
  renderRequirementsPage()
  await userEvent.type(screen.getByRole('searchbox'), '3.3')
  expect(await screen.findByText('数据同步机制')).toBeInTheDocument()
  expect(screen.getByText('手动同步、模拟定时同步、确认删除联动')).toBeInTheDocument()
})
```

- [ ] **Step 2: Verify RED**

Run: `cd frontend; npm.cmd test -- --run src/pages/KnowledgePage.test.tsx src/pages/DashboardPage.test.tsx src/pages/RequirementsPage.test.tsx`

Expected: page imports fail.

- [ ] **Step 3: Implement all three pages**

Knowledge page includes tabs for entries, table sync, SQL models, tags/search and sync logs. Dashboard page persists card position and size through explicit move/resize controls, refreshes card data, removes cards and opens the local read-only share route. Requirements page shows columns for 石墨条目、问题、解决方案、页面、接口、测试、验收动作、状态 and filters by module, priority and keyword.

- [ ] **Step 4: Verify GREEN and full frontend suite**

Run: `cd frontend; npm.cmd test -- --run; npm.cmd run build`

Expected: all tests pass and production build succeeds.

- [ ] **Step 5: Commit remaining pages**

```powershell
git add frontend/src
git commit -m "feat: add knowledge dashboard and traceability pages"
```

### Task 10: Formal Plan Book, One-Click Startup, and Final Acceptance

**Files:**
- Create: `.env.example`
- Create: `start-demo.ps1`
- Create: `README.md`
- Create: `docs/智能问数优化实施计划书.md`
- Create: `docs/需求追踪矩阵.md`
- Create: `backend/tests/test_demo_scenarios.py`

**Interfaces:**
- Produces: `start-demo.ps1 [-NoBrowser] [-Mode offline|llm]`
- Produces: two user-facing Markdown deliverables

- [ ] **Step 1: Write failing end-to-end API scenario tests**

```python
@pytest.mark.parametrize("question,requirement", [
    ("分析房价", "2.2"),
    ("分析 2024—2025 年各行政区平均房价变化", "2.4"),
    ("房价上涨是否与人口和通勤相关", "5"),
])
def test_demo_questions_cover_documented_paths(client, question, requirement):
    body = client.post("/api/chat", json={"question": question}).json()
    assert requirement in body["requirements"]


def test_every_requirement_has_a_documented_demo_action(client):
    rows = client.get("/api/requirements").json()
    assert len(rows) == 10
    assert all(row["acceptance"] for row in rows)
```

- [ ] **Step 2: Verify the new scenario tests RED if any trace entry is missing**

Run: `cd backend; py -m pytest tests/test_demo_scenarios.py -q`

Expected before completing seed mappings: the coverage assertion identifies the missing requirement or acceptance action; after Tasks 2–9 it may already pass, in which case temporarily remove one mapping, verify the expected failure, then restore it.

- [ ] **Step 3: Write startup and environment files**

`.env.example` contains `APP_MODE=offline`, empty `LLM_BASE_URL`, `LLM_API_KEY`, `LLM_MODEL`, and `DATABASE_URL=sqlite:///./daas_demo.db`.

`start-demo.ps1` must:

1. stop on errors with `$ErrorActionPreference = 'Stop'`;
2. verify `py`, `node` and `npm.cmd` are available;
3. create `backend/.venv` if absent and install `backend/requirements.txt`;
4. run the database seed command;
5. install frontend packages only when `node_modules` is absent;
6. start Uvicorn on port 8000 and Vite on port 5173 using `Start-Process -WindowStyle Hidden`;
7. wait for `/api/health` and the Vite URL with bounded retries;
8. open `http://localhost:5173/ask` unless `-NoBrowser` is set;
9. print both process IDs and stop instructions.

- [ ] **Step 4: Write the formal plan book and traceability document**

The plan book contains: 项目背景、现状问题、建设目标、需求逐项解决方案、总体架构、数据与安全、实施阶段、人员与职责建议、四周排期、风险与缓解措施、验收指标、演示脚本、后续接入极智 DAAS 的适配点。Each requirement section includes the matching Demo page, API, test and acceptance action. The standalone traceability document repeats the ten-row mapping in review-friendly table form.

- [ ] **Step 5: Write README**

Document prerequisites, one-click startup, manual backend/frontend startup, offline and real-model configuration, five demo scripts, test commands, build command, ports, database reset, PowerShell execution-policy workaround using `powershell -ExecutionPolicy Bypass -File .\start-demo.ps1`, and the known non-production boundaries.

- [ ] **Step 6: Run fresh verification**

Run:

```powershell
cd backend
py -m pytest --cov=app --cov-report=term-missing -q
cd ..\frontend
npm.cmd test -- --run
npm.cmd run build
cd ..
powershell -ExecutionPolicy Bypass -File .\start-demo.ps1 -NoBrowser
```

Expected: backend tests have zero failures, frontend tests have zero failures, Vite build exits 0, health endpoint returns `status=ok`, and both local services start.

- [ ] **Step 7: Execute the five acceptance paths manually**

1. Incomplete question → recommendations without SQL.
2. Complete price question → steps, source, SQL, chart, insights, suggestion and dashboard save.
3. Follow-up “只看海淀区” → inherited year and overridden district.
4. Cross-source question → three SQL plans and one merged result.
5. Duplicate knowledge → same-scope rejection, private-over-public priority, sync log and confirmed delete linkage.

Record the result of each path in the README acceptance section with the execution date `2026-07-14`.

- [ ] **Step 8: Commit documentation and runnable delivery**

```powershell
git add .env.example start-demo.ps1 README.md docs backend/tests/test_demo_scenarios.py
git commit -m "docs: deliver intelligent query demo plan and runbook"
```
