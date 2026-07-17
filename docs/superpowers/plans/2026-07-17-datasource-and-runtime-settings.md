# Datasource And Runtime Settings Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a real datasource structure page and a productized DeepSeek/runtime settings experience.

**Architecture:** Backend exposes read-only datasource inspection APIs backed by the active SQLite database, plus model settings APIs that return masked configuration and can test DeepSeek connectivity. Frontend adds a datasource page and settings page that consume those APIs without exposing full secrets.

**Tech Stack:** FastAPI, SQLAlchemy, SQLite, React, TypeScript, Vite, Vitest, React Testing Library.

## Global Constraints

- Do not expose full API keys in API responses or UI.
- Datasource inspection is read-only.
- Runtime DB files remain under `backend/runtime/` and ignored by git.
- DeepSeek remains optional; offline mode must still work.

---

### Task 1: Backend datasource inspection API

**Files:**
- Create: `backend/app/services/datasource.py`
- Create: `backend/app/api/datasource.py`
- Modify: `backend/app/main.py`
- Test: `backend/tests/test_datasource_api.py`

**Interfaces:**
- Produces: `GET /api/datasource/overview`, `GET /api/datasource/tables`, `GET /api/datasource/tables/{table_name}`.

- [ ] Write failing API tests for overview, table list, table detail, and hidden system tables.
- [ ] Implement read-only SQLite inspection service.
- [ ] Register FastAPI router.
- [ ] Run backend datasource tests.

### Task 2: Backend model settings and DeepSeek connectivity API

**Files:**
- Modify: `backend/app/api/settings.py`
- Test: `backend/tests/test_settings_api.py`

**Interfaces:**
- Produces: masked fields in `GET /api/model-settings`.
- Produces: `POST /api/model-settings/deepseek/test`.

- [ ] Write failing tests for masked key and no-key friendly test response.
- [ ] Implement key masking and connectivity test endpoint.
- [ ] Run settings tests.

### Task 3: Frontend datasource and runtime settings pages

**Files:**
- Modify: `frontend/src/layout/PlatformShell.tsx`
- Modify: `frontend/src/app.tsx`
- Modify: `frontend/src/types.ts`
- Create: `frontend/src/pages/DataSourceWorkspace.tsx`
- Create: `frontend/src/pages/SettingsWorkspace.tsx`
- Modify: `frontend/src/styles.css`
- Test: frontend page/component tests.

**Interfaces:**
- Consumes: datasource and model settings APIs from Tasks 1 and 2.

- [ ] Add navigation entries for 数据源管理 and 运行配置.
- [ ] Build datasource page with overview, tables, columns, samples, and suggested questions.
- [ ] Build settings page with status, masked key, update form, and test connection.
- [ ] Run frontend tests and build.

### Task 4: Final verification

**Files:**
- No production files unless verification finds issues.

- [ ] Run all backend tests.
- [ ] Run frontend tests.
- [ ] Run frontend build.
- [ ] Commit verified changes.
