# Low-Coupling Refactor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将后端会话服务、前端大页面和房价业务域配置拆成低耦合模块，并保持现有功能可运行。

**Architecture:** 采用“兼容入口 + 内部拆分”的方式。后端把 `conversation.py` 迁移为 `conversation/` 包并在 `__init__.py` 继续导出原函数；前端保留原页面文件作为 re-export 入口，实际实现迁移到 `pages/query` 与 `pages/dashboard` 子目录。

**Tech Stack:** FastAPI, SQLite, pytest, React, TypeScript, Vitest, Vite, Chart.js。

## Global Constraints

- 不改变现有 API 路径。
- 不改变 `.env` 和 DeepSeek 配置字段。
- 不新增全局状态管理库。
- 每个任务完成后运行相关测试。
- 旧导入路径必须保持兼容。
- 本次优先重构结构，不新增业务功能。

---

## File Structure

### Backend

- Create: `backend/app/domain/__init__.py`
- Create: `backend/app/domain/config.py`
- Create: `backend/app/domain/real_estate.py`
- Delete: `backend/app/services/conversation.py`
- Create: `backend/app/services/conversation/__init__.py`
- Create: `backend/app/services/conversation/service.py`
- Create: `backend/app/services/conversation/context.py`
- Create: `backend/app/services/conversation/charting.py`
- Create: `backend/app/services/conversation/trace.py`
- Create: `backend/app/services/conversation/insights.py`
- Create: `backend/app/services/conversation/history.py`
- Create: `backend/app/services/conversation/sql_repair.py`
- Modify: `backend/tests/test_chat_api.py`

### Frontend Query

- Modify: `frontend/src/pages/QueryWorkspace.tsx`
- Create: `frontend/src/pages/query/QueryWorkspace.tsx`
- Create: `frontend/src/pages/query/components/ConversationHistory.tsx`
- Create: `frontend/src/pages/query/components/ModelConfigStrip.tsx`
- Create: `frontend/src/pages/query/components/QueryComposer.tsx`
- Create: `frontend/src/pages/query/components/QueryResult.tsx`
- Create: `frontend/src/pages/query/components/LiveThinkingCard.tsx`
- Create: `frontend/src/pages/query/components/AnalysisSidePanel.tsx`
- Create: `frontend/src/pages/query/hooks/useConversation.ts`
- Create: `frontend/src/pages/query/hooks/useModelSettings.ts`
- Create: `frontend/src/pages/query/hooks/useQuestionSuggestions.ts`
- Create: `frontend/src/pages/query/queryUtils.ts`
- Modify: `frontend/src/test/query-workspace.test.tsx`

### Frontend Dashboard

- Modify: `frontend/src/pages/DashboardWorkspace.tsx`
- Create: `frontend/src/pages/dashboard/DashboardWorkspace.tsx`
- Create: `frontend/src/pages/dashboard/components/DashboardCreateForm.tsx`
- Create: `frontend/src/pages/dashboard/components/DashboardManagementBar.tsx`
- Create: `frontend/src/pages/dashboard/components/DashboardFilters.tsx`
- Create: `frontend/src/pages/dashboard/components/DashboardGrid.tsx`
- Create: `frontend/src/pages/dashboard/components/DashboardCardView.tsx`
- Create: `frontend/src/pages/dashboard/hooks/useDashboardState.ts`
- Create: `frontend/src/pages/dashboard/hooks/useDashboardDrag.ts`
- Create: `frontend/src/pages/dashboard/dashboardUtils.ts`
- Modify: `frontend/src/test/dashboard-workspace.test.tsx`

---

### Task 1: Extract business domain configuration

**Files:**
- Create: `backend/app/domain/__init__.py`
- Create: `backend/app/domain/config.py`
- Create: `backend/app/domain/real_estate.py`
- Modify: `backend/app/services/conversation.py`
- Test: `backend/tests/test_chat_api.py`

**Interfaces:**
- Produces: `get_default_domain_config() -> DomainConfig`
- Produces: `DomainConfig.allowed_tables: tuple[str, ...]`
- Produces: `DomainConfig.districts: tuple[str, ...]`
- Produces: `DomainConfig.chart_field_priority: tuple[str, ...]`
- Produces: `DomainConfig.tool_labels: dict[str, str]`

- [ ] **Step 1: Add failing coverage for domain config import**

Add this test to `backend/tests/test_chat_api.py`:

```python
def test_default_domain_config_exposes_real_estate_tables():
    from app.domain import get_default_domain_config

    config = get_default_domain_config()

    assert "house_price_monthly" in config.allowed_tables
    assert "海淀区" in config.districts
    assert "avg_price" in config.chart_field_priority
    assert config.tool_labels["knowledge_search"] == "检索问数知识"
```

- [ ] **Step 2: Run the focused test and verify it fails**

Run:

```powershell
python -m pytest backend/tests/test_chat_api.py::test_default_domain_config_exposes_real_estate_tables -q
```

Expected: FAIL because `app.domain` does not exist.

- [ ] **Step 3: Create the domain config files**

Create `backend/app/domain/config.py` with:

```python
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DomainConfig:
    allowed_tables: tuple[str, ...]
    districts: tuple[str, ...]
    relative_year_offsets: dict[str, int]
    chart_field_priority: tuple[str, ...]
    tool_labels: dict[str, str]
    field_units: dict[str, str]
```

Create `backend/app/domain/real_estate.py` by moving the existing constants from `conversation.py` into:

```python
from __future__ import annotations

from .config import DomainConfig


REAL_ESTATE_DOMAIN = DomainConfig(
    allowed_tables=(...),
    districts=(...),
    relative_year_offsets={...},
    chart_field_priority=(...),
    tool_labels={...},
    field_units={...},
)
```

Create `backend/app/domain/__init__.py` with:

```python
from .config import DomainConfig
from .real_estate import REAL_ESTATE_DOMAIN


def get_default_domain_config() -> DomainConfig:
    return REAL_ESTATE_DOMAIN


__all__ = ["DomainConfig", "REAL_ESTATE_DOMAIN", "get_default_domain_config"]
```

- [ ] **Step 4: Wire existing conversation code to domain config**

In `backend/app/services/conversation.py`, replace direct constants with:

```python
from app.domain import get_default_domain_config

DOMAIN_CONFIG = get_default_domain_config()
ALLOWED_TABLES = DOMAIN_CONFIG.allowed_tables
DISTRICTS = DOMAIN_CONFIG.districts
RELATIVE_YEAR_OFFSETS = DOMAIN_CONFIG.relative_year_offsets
CHART_FIELD_PRIORITY = DOMAIN_CONFIG.chart_field_priority
TOOL_LABELS = DOMAIN_CONFIG.tool_labels
```

Update `_field_unit()` to read `DOMAIN_CONFIG.field_units`.

- [ ] **Step 5: Run backend tests**

Run:

```powershell
python -m pytest backend/tests -q
```

Expected: all tests pass.

- [ ] **Step 6: Commit**

```powershell
git add backend/app/domain backend/app/services/conversation.py backend/tests/test_chat_api.py
git commit -m "refactor: extract real estate domain config"
```

---

### Task 2: Split backend conversation service

**Files:**
- Delete: `backend/app/services/conversation.py`
- Create: `backend/app/services/conversation/__init__.py`
- Create: `backend/app/services/conversation/service.py`
- Create: `backend/app/services/conversation/context.py`
- Create: `backend/app/services/conversation/charting.py`
- Create: `backend/app/services/conversation/trace.py`
- Create: `backend/app/services/conversation/insights.py`
- Create: `backend/app/services/conversation/history.py`
- Create: `backend/app/services/conversation/sql_repair.py`
- Test: `backend/tests/test_chat_api.py`

**Interfaces:**
- Produces: `run_chat(request: ChatRequest) -> ChatResponse`
- Produces: `get_analysis(task_id: str) -> AnalysisResponse`
- Produces: `list_conversations() -> list[ConversationSummary]`
- Produces: `get_conversation_history(conversation_id: str) -> ConversationHistoryResponse`

- [ ] **Step 1: Add import compatibility test**

Add this test:

```python
def test_conversation_package_keeps_public_imports():
    from app.services.conversation import (
        get_analysis,
        get_conversation_history,
        list_conversations,
        run_chat,
    )

    assert callable(run_chat)
    assert callable(get_analysis)
    assert callable(list_conversations)
    assert callable(get_conversation_history)
```

- [ ] **Step 2: Run focused test and verify current behavior**

Run:

```powershell
python -m pytest backend/tests/test_chat_api.py::test_conversation_package_keeps_public_imports -q
```

Expected: PASS before migration, and must remain PASS after migration.

- [ ] **Step 3: Move context helpers**

Move these functions from old `conversation.py` into `conversation/context.py`:

```python
merge_context
_normalize_known_district_literals
_selected_fields_sql
_scope_sql_to_single_year_context
_prepare_query_for_context
```

Import `DISTRICTS` and `RELATIVE_YEAR_OFFSETS` from `app.domain.get_default_domain_config()`.

- [ ] **Step 4: Move chart helpers**

Move these functions into `conversation/charting.py`:

```python
_is_number
_chart_title
_pick_y_fields
_repair_chart
_field_unit
_recommend_reason
_enrich_chart_spec
```

Import `CHART_FIELD_PRIORITY` and field units from domain config.

- [ ] **Step 5: Move SQL repair helper**

Move `_apply_sql_repair` into `conversation/sql_repair.py`.

- [ ] **Step 6: Move insight helpers**

Move these functions into `conversation/insights.py`:

```python
_result_insights
_used_questions_and_recommendations
_recommendation_pool
_dedupe_recommendations
```

- [ ] **Step 7: Move trace helpers**

Move these functions into `conversation/trace.py`:

```python
_find_step
_step_output
_step_failed
_tables_from_sql
_chart_reason
_friendly_input_summary
_friendly_output_summary
_friendly_chart_reason
_prime_agent_trace
_finalize_agent_trace
```

Import `TOOL_LABELS` from domain config.

- [ ] **Step 8: Move history helpers**

Move these functions into `conversation/history.py`:

```python
create_conversation
_load_context
get_analysis
list_conversations
get_conversation_history
```

- [ ] **Step 9: Keep main orchestration in service.py**

Move these functions into `conversation/service.py`:

```python
utc_now
_dataset
select_analysis_engine
run_chat
```

Import helpers from `context.py`, `charting.py`, `trace.py`, `insights.py`, `history.py`, and `sql_repair.py`.

- [ ] **Step 10: Add compatibility exports**

Create `backend/app/services/conversation/__init__.py`:

```python
from .history import get_analysis, get_conversation_history, list_conversations
from .service import run_chat

__all__ = [
    "run_chat",
    "get_analysis",
    "list_conversations",
    "get_conversation_history",
]
```

- [ ] **Step 11: Run backend tests**

Run:

```powershell
python -m pytest backend/tests -q
```

Expected: all tests pass.

- [ ] **Step 12: Commit**

```powershell
git add backend/app/services/conversation backend/app/domain backend/tests/test_chat_api.py
git add -u backend/app/services/conversation.py
git commit -m "refactor: split conversation service modules"
```

---

### Task 3: Split QueryWorkspace frontend page

**Files:**
- Modify: `frontend/src/pages/QueryWorkspace.tsx`
- Create: `frontend/src/pages/query/QueryWorkspace.tsx`
- Create: `frontend/src/pages/query/components/ConversationHistory.tsx`
- Create: `frontend/src/pages/query/components/ModelConfigStrip.tsx`
- Create: `frontend/src/pages/query/components/QueryComposer.tsx`
- Create: `frontend/src/pages/query/components/QueryResult.tsx`
- Create: `frontend/src/pages/query/components/LiveThinkingCard.tsx`
- Create: `frontend/src/pages/query/components/AnalysisSidePanel.tsx`
- Create: `frontend/src/pages/query/hooks/useConversation.ts`
- Create: `frontend/src/pages/query/hooks/useModelSettings.ts`
- Create: `frontend/src/pages/query/hooks/useQuestionSuggestions.ts`
- Create: `frontend/src/pages/query/queryUtils.ts`
- Test: `frontend/src/test/query-workspace.test.tsx`

**Interfaces:**
- Produces: `export function QueryWorkspace()`
- Produces: `export const liveThinkingSteps`
- Keeps: `frontend/src/pages/QueryWorkspace.tsx` re-export compatibility.

- [ ] **Step 1: Move pure utilities first**

Move `liveThinkingSteps` and pure formatting helpers into `frontend/src/pages/query/queryUtils.ts`.

- [ ] **Step 2: Re-export utilities from old entry**

Replace `frontend/src/pages/QueryWorkspace.tsx` with:

```typescript
export { QueryWorkspace } from './query/QueryWorkspace';
export { liveThinkingSteps } from './query/queryUtils';
```

- [ ] **Step 3: Extract model config UI**

Create `ModelConfigStrip.tsx` with props:

```typescript
type ModelConfigStripProps = {
  statusLabel: string;
  isConfigured: boolean;
  onOpenConfig: () => void;
};
```

- [ ] **Step 4: Extract conversation history UI**

Create `ConversationHistory.tsx` with props:

```typescript
type ConversationHistoryProps = {
  conversations: ConversationSummary[];
  activeConversationId: string | null;
  onSelectConversation: (id: string) => void;
  onRefresh: () => void;
};
```

- [ ] **Step 5: Extract query input UI**

Create `QueryComposer.tsx` with props:

```typescript
type QueryComposerProps = {
  question: string;
  isLoading: boolean;
  suggestions: string[];
  onQuestionChange: (value: string) => void;
  onSubmit: () => void;
  onSuggestionClick: (question: string) => void;
};
```

- [ ] **Step 6: Extract result and thinking components**

Move Agent step rendering into `LiveThinkingCard.tsx`.
Move chart/table/result actions into `QueryResult.tsx`.
Move right-side SQL/source panel into `AnalysisSidePanel.tsx`.

- [ ] **Step 7: Extract hooks**

Move conversation loading and sending logic into `useConversation.ts`.
Move API configuration state into `useModelSettings.ts`.
Move recommendation question logic into `useQuestionSuggestions.ts`.

- [ ] **Step 8: Run frontend query tests**

Run:

```powershell
npm.cmd --prefix frontend run test:run -- query-workspace
```

Expected: query workspace tests pass.

- [ ] **Step 9: Run full frontend verification**

Run:

```powershell
npm.cmd --prefix frontend run test:run
npm.cmd --prefix frontend run build
```

Expected: tests and build pass.

- [ ] **Step 10: Commit**

```powershell
git add frontend/src/pages/QueryWorkspace.tsx frontend/src/pages/query frontend/src/test/query-workspace.test.tsx
git commit -m "refactor: split query workspace components"
```

---

### Task 4: Split DashboardWorkspace frontend page

**Files:**
- Modify: `frontend/src/pages/DashboardWorkspace.tsx`
- Create: `frontend/src/pages/dashboard/DashboardWorkspace.tsx`
- Create: `frontend/src/pages/dashboard/components/DashboardCreateForm.tsx`
- Create: `frontend/src/pages/dashboard/components/DashboardManagementBar.tsx`
- Create: `frontend/src/pages/dashboard/components/DashboardFilters.tsx`
- Create: `frontend/src/pages/dashboard/components/DashboardGrid.tsx`
- Create: `frontend/src/pages/dashboard/components/DashboardCardView.tsx`
- Create: `frontend/src/pages/dashboard/hooks/useDashboardState.ts`
- Create: `frontend/src/pages/dashboard/hooks/useDashboardDrag.ts`
- Create: `frontend/src/pages/dashboard/dashboardUtils.ts`
- Test: `frontend/src/test/dashboard-workspace.test.tsx`

**Interfaces:**
- Produces: `export function DashboardWorkspace()`
- Keeps: `frontend/src/pages/DashboardWorkspace.tsx` re-export compatibility.

- [ ] **Step 1: Move dashboard pure helpers**

Move grid, filter and chart-type helper functions into `dashboardUtils.ts`.

- [ ] **Step 2: Re-export old entry**

Replace `frontend/src/pages/DashboardWorkspace.tsx` with:

```typescript
export { DashboardWorkspace } from './dashboard/DashboardWorkspace';
```

- [ ] **Step 3: Extract management components**

Move dashboard selector and creation form into:

```text
DashboardManagementBar.tsx
DashboardCreateForm.tsx
```

- [ ] **Step 4: Extract filters**

Move year/region/metric filters into `DashboardFilters.tsx`.

- [ ] **Step 5: Extract card grid and card view**

Move two-column grid and drag placeholder logic into:

```text
DashboardGrid.tsx
DashboardCardView.tsx
useDashboardDrag.ts
```

- [ ] **Step 6: Extract state hook**

Move dashboard loading, selection, creation and update logic into `useDashboardState.ts`.

- [ ] **Step 7: Run dashboard tests**

Run:

```powershell
npm.cmd --prefix frontend run test:run -- dashboard-workspace
```

Expected: dashboard workspace tests pass.

- [ ] **Step 8: Run full frontend verification**

Run:

```powershell
npm.cmd --prefix frontend run test:run
npm.cmd --prefix frontend run build
```

Expected: tests and build pass.

- [ ] **Step 9: Commit**

```powershell
git add frontend/src/pages/DashboardWorkspace.tsx frontend/src/pages/dashboard frontend/src/test/dashboard-workspace.test.tsx
git commit -m "refactor: split dashboard workspace components"
```

---

### Task 5: Final integration verification

**Files:**
- Modify only if tests reveal broken imports.

**Interfaces:**
- Confirms all public behavior is still available.

- [ ] **Step 1: Run backend verification**

```powershell
python -m pytest backend/tests -q
```

Expected: all backend tests pass.

- [ ] **Step 2: Run frontend verification**

```powershell
npm.cmd --prefix frontend run test:run
npm.cmd --prefix frontend run build
```

Expected: all frontend tests pass and build succeeds.

- [ ] **Step 3: Manual smoke test**

Start the project:

```powershell
Start-Process powershell -ArgumentList "-NoExit","-Command","cd 'C:\Users\iphon\Documents\智慧足迹-极智DAAS-实习\.worktrees\intelligent-query-demo'; python -m uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000"
Start-Process powershell -ArgumentList "-NoExit","-Command","cd 'C:\Users\iphon\Documents\智慧足迹-极智DAAS-实习\.worktrees\intelligent-query-demo\frontend'; npm run dev -- --host 127.0.0.1"
```

Open:

```text
http://127.0.0.1:5173
```

Check:

1. 智慧问数可以发送问题并返回图表。
2. 历史会话面板可以打开旧会话。
3. 数据源页布局没有左移。
4. 仪表盘可以新建自定义名称。
5. 仪表盘图表切换、筛选和拖动正常。

- [ ] **Step 4: Commit final cleanup if needed**

```powershell
git status --short
git add <changed-files>
git commit -m "chore: verify low-coupling refactor"
```

