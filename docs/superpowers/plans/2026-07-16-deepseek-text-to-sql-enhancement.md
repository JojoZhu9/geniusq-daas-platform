# DeepSeek Text-to-SQL Enhancement Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add DeepSeek-backed Text-to-SQL with keyword knowledge retrieval, safe SQL execution, frontend transparency, and feedback-to-knowledge capture.

**Architecture:** Keep the existing `/api/chat` orchestration and `AnalysisPlan` response shape. Add focused services for retrieval, DeepSeek-compatible model calls, engine selection, and feedback persistence; the existing SQL guard remains the execution gate.

**Tech Stack:** FastAPI, SQLAlchemy, Pydantic, httpx, SQLite, React, TypeScript, Vitest, Pytest.

## Global Constraints

- Do not commit a real DeepSeek API key.
- Offline mode must remain the default and continue to run without network access.
- DeepSeek-generated SQL is untrusted and must pass the existing read-only SQL guard.
- Do not introduce vector databases, file upload training, Python script generation, or a full Data Formulator workspace in this phase.
- Use mock clients in tests; automated tests must not call the real DeepSeek API.

---

### Task 1: Configuration, Schemas, and Retrieval

**Files:**
- Modify: `backend/app/config.py`
- Modify: `backend/app/schemas.py`
- Create: `backend/app/services/retrieval.py`
- Test: `backend/tests/test_retrieval.py`

**Interfaces:**
- Produces: `retrieve_relevant_knowledge(session: Session, question: str, limit: int = 5) -> list[RetrievedKnowledge]`
- Produces: `RetrievedKnowledge`, `TextToSqlResult`

- [x] Write failing tests for keyword retrieval and private-priority ordering.
- [x] Implement config fields and retrieval service.
- [x] Run targeted backend tests.

### Task 2: DeepSeek Text-to-SQL Service

**Files:**
- Create: `backend/app/services/text_to_sql.py`
- Test: `backend/tests/test_text_to_sql.py`

**Interfaces:**
- Produces: `DeepSeekTextToSqlService.generate(question: str, context: QueryContext, knowledge: list[RetrievedKnowledge]) -> TextToSqlResult`
- Produces: `parse_model_json(content: str) -> dict[str, Any]`

- [x] Write failing tests for JSON parsing, fenced JSON parsing, malformed output, and mock DeepSeek calls.
- [x] Implement prompt construction, httpx client injection, and output normalization.
- [x] Run targeted backend tests.

### Task 3: Chat Engine Selection, SQL Safety Metadata, and Feedback

**Files:**
- Modify: `backend/app/services/conversation.py`
- Modify: `backend/app/api/chat.py`
- Modify: `backend/app/seed.py`
- Create: `backend/app/services/feedback.py`
- Test: `backend/tests/test_deepseek_chat.py`

**Interfaces:**
- Produces: `select_analysis_engine(session: Session) -> AnalysisEngine`
- Produces: `save_analysis_feedback(session: Session, analysis_id: str, payload: dict[str, Any]) -> dict[str, Any]`
- Produces: `POST /api/analysis/{analysis_id}/feedback`

- [x] Write failing tests for missing API key, safe mock DeepSeek query execution, dangerous SQL rejection, and feedback saved as SQL knowledge.
- [x] Implement DeepSeek engine and feedback persistence.
- [x] Run targeted backend tests.

### Task 4: Frontend Metadata and Feedback UI

**Files:**
- Modify: `frontend/src/types.ts`
- Modify: `frontend/src/pages/QueryWorkspace.tsx`
- Test: `frontend/src/test/query-workspace.test.tsx`

**Interfaces:**
- Consumes: `metadata.mode`, `metadata.used_knowledge`, `metadata.model_reasoning`, `metadata.confidence`, `metadata.sql_validation_status`
- Produces: feedback POST to `/api/analysis/{analysis_id}/feedback`

- [x] Write failing tests for metadata display and feedback click.
- [x] Implement UI cards and feedback actions.
- [x] Run targeted frontend tests.

### Task 5: Documentation and Full Verification

**Files:**
- Modify: `.env.example` if present, otherwise create it.
- Modify: `README.md`

**Interfaces:**
- Produces: documented DeepSeek configuration placeholders only.

- [x] Add DeepSeek mode instructions without real key.
- [x] Run backend tests, frontend tests, and frontend build.
- [x] Commit verified implementation.

