# GeniusQ DaaS Intelligent Query Demo

[中文](#中文说明) | [English](#english)

## 中文说明

GeniusQ DaaS Intelligent Query Demo 是一个可在本地运行的小型全栈演示项目，用来展示企业数据平台中的“智能问数”体验。用户可以用自然语言提问，系统会结合知识库、数据表结构和 DeepSeek Text-to-SQL 生成只读 SQL，再查询本地 SQLite 演示库，自动生成图表、结论、追问建议和仪表盘。

项目不依赖真实生产数据，演示数据由本地 SQLite 自动生成，适合用于产品能力展示、技术方案说明和后续平台化开发前的原型验证。

### 功能模块

#### 1. 智能问数工作台

用户输入自然语言问题后，系统会展示类似 Agent 的逐步执行过程，包括理解问题、合并上下文、检索知识、选择表字段、生成 SQL、校验 SQL、执行查询和生成图表。结果区会展示只读 SQL、数据来源、图表、分析结论和后续追问建议。

![智能问数结果](docs/assets/readme/query-result.png)

核心能力：

- DeepSeek Text-to-SQL，并支持本地离线规则兜底。
- 多轮上下文理解，例如“再看一下海淀区”“只保留 2025 年”。
- SQL 只读安全校验，只允许执行 `SELECT` / `WITH` 查询。
- 自动图表推荐，并允许用户切换折线图、柱状图、饼图、散点图、堆叠柱状图和表格。
- 根据当前问题和历史对话推荐 3 个不重复的后续问题。
- 历史会话自动保存，支持恢复单个会话、删除单条历史和清空全部历史。

#### 2. 数据源管理

数据源页面直接读取当前 SQLite 数据库结构，展示可查询数据表、字段、字段含义、字段类型、用途、示例值和样例数据。每张表都会提供“这张表可以这样问”的推荐问题，可一键跳转回智能问数页面并自动填入问题。

![数据源管理](docs/assets/readme/datasource.png)

核心能力：

- 自动读取当前数据库表结构。
- 仅展示适合用户查询的业务数据表。
- 标注字段角色：筛选 / 分组维度、可聚合指标、文本说明等。
- 根据数据表结构生成可点击的推荐问题。

#### 3. 知识库管理

知识库页面用于管理 Text-to-SQL 前的检索增强内容，包括业务口径、SQL 示例、字段说明和表关系信息。系统在生成 SQL 前会检索相关知识，帮助模型更准确地理解字段含义和业务约束。

![知识库管理](docs/assets/readme/knowledge.png)

核心能力：

- 管理私有 / 公共知识条目。
- 按标签、类型、范围筛选知识。
- 维护知识与数据表之间的关联关系。
- 支持模型同步、字段同步和冲突提示。

#### 4. 仪表盘

问数结果可以保存为仪表盘卡片。仪表盘支持两列布局、卡片拖动排序、图表类型切换、筛选器、刷新、移除、本地只读分享和重命名。

![仪表盘](docs/assets/readme/dashboard.png)

核心能力：

- 新建自定义名称的仪表盘，并支持后续重命名。
- 将问数图表保存为看板卡片。
- 支持折线图、柱状图、饼图、散点图、堆叠柱状图和表格。
- 支持年份、区域、指标筛选。
- 生成本地只读分享页。

#### 5. 运行配置

运行配置页面用于查看当前模型模式，并配置 / 测试 DeepSeek API。API Key 只会提交给本地后端在运行时使用，页面不会回显完整密钥，也不会提交到 Git 仓库。

![运行配置](docs/assets/readme/settings.png)

核心能力：

- 显示当前模式：离线规则模式或 DeepSeek 在线模式。
- 以脱敏方式显示 API Key。
- 配置 Base URL、Model 和 API Key。
- 测试 DeepSeek 连接，失败时展示明确错误提示。

### 项目架构

```text
Frontend: React + Vite + TypeScript
├─ Query Workspace
│  ├─ 智能问数主流程
│  ├─ 历史会话面板
│  ├─ 模型配置入口
│  └─ 图表结果与追问建议
├─ DataSource Workspace
│  └─ 数据库结构、字段说明、样例数据和推荐问题
├─ Knowledge Workspace
│  └─ 知识条目、标签筛选和表关系维护
├─ Dashboard Workspace
│  ├─ 仪表盘管理、重命名
│  ├─ 卡片布局、拖拽排序
│  └─ 图表切换、筛选和分享
└─ Settings Workspace
   └─ DeepSeek API 配置和连接测试

REST API

Backend: FastAPI + SQLAlchemy
├─ api/
│  ├─ chat.py          会话、问数、历史删除 / 清空
│  ├─ dashboards.py    仪表盘、卡片、重命名、分享
│  ├─ datasource.py    数据源结构和样例数据
│  ├─ knowledge.py     知识库管理
│  └─ model_settings.py 模型运行配置
├─ services/
│  ├─ conversation_*   会话编排、历史、上下文、SQL 修复、执行轨迹
│  ├─ text_to_sql.py   DeepSeek Text-to-SQL 调用
│  ├─ sql_guard.py     只读 SQL 校验
│  ├─ datasource.py    SQLite schema introspection
│  ├─ knowledge.py     知识检索与同步
│  └─ dashboards.py    仪表盘和卡片服务
└─ domain/
   └─ real_estate.py   房价演示业务域配置

SQLite demo database
└─ backend/runtime/daas_demo.db
   ├─ house_price_monthly
   ├─ housing_transactions
   ├─ district_population
   ├─ commuting_metrics
   ├─ knowledge_items
   ├─ semantic_metrics
   ├─ conversations / messages / analysis_runs
   └─ dashboards / dashboard_cards / share_links
```

### 目录结构

```text
backend/
  app/
    api/          FastAPI 路由
    domain/       业务域配置
    services/     问数、知识库、SQL、安全校验、仪表盘和数据源服务
    config.py     环境变量和运行配置
    db.py         SQLAlchemy engine/session
    seed.py       SQLite schema 和演示数据
  data/           可随项目携带的演示数据库包
  runtime/        本地运行时数据库
  tests/          后端测试

frontend/
  src/
    pages/        智能问数、数据源、知识库、仪表盘、运行配置页面
    components/   图表、时间线、徽章、数据源卡片等组件
    utils/        仪表盘筛选等工具函数
    test/         前端测试

docs/
  assets/readme/  README 截图
  superpowers/    设计文档与实施计划

start-demo.ps1    Windows 一键启动脚本
```

### 运行方式

推荐在项目根目录执行：

```powershell
powershell -ExecutionPolicy Bypass -File .\start-demo.ps1
```

也可以分别启动后端和前端：

```powershell
python -m uvicorn backend.app.main:app --reload --port 8000
npm --prefix frontend install
npm --prefix frontend run dev
```

访问地址：

- 前端：http://127.0.0.1:5173
- 后端 API：http://127.0.0.1:8000

### DeepSeek 配置

默认不配置 API Key 时会使用离线规则模式：

```env
LLM_MODE=offline
```

如果需要启用 DeepSeek，可以在页面中的“配置 DeepSeek API”或“运行配置”页面填写，也可以在本地 `.env` 中配置：

```env
LLM_MODE=deepseek
DEEPSEEK_API_KEY=sk-...
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-v4-flash
```

不配置 DeepSeek 时，系统会使用本地离线规则继续演示。

### 测试

```powershell
python -m pytest backend/tests -q
npm --prefix frontend run test:run
npm --prefix frontend run build
```

---

## English

GeniusQ DaaS Intelligent Query Demo is a locally runnable full-stack demo for an intelligent business data query experience. Users ask questions in natural language; the system combines knowledge retrieval, table schema context, and DeepSeek Text-to-SQL to produce read-only SQL, query a local SQLite demo database, and generate charts, conclusions, follow-up suggestions, and dashboards.

The project does not depend on production data. Demo data is generated locally in SQLite, making it suitable for product demos, technical walkthroughs, and prototype validation before deeper platform integration.

### Feature Modules

#### 1. Intelligent Query Workspace

After a user asks a natural-language question, the system displays an Agent-like execution flow: understanding the question, merging context, retrieving knowledge, selecting tables and fields, generating SQL, validating SQL, executing the query, and producing chart suggestions. The result area includes read-only SQL, data lineage, charts, conclusions, and suggested follow-up questions.

![Intelligent query result](docs/assets/readme/query-result.png)

Key capabilities:

- DeepSeek Text-to-SQL with local offline rule-based fallback.
- Multi-turn context understanding, such as “now only show Haidian” or “keep 2025 only”.
- Read-only SQL guardrails; only `SELECT` / `WITH` queries are allowed.
- Automatic chart recommendation with manual switching between line, bar, pie, scatter, stacked bar, and table views.
- Three non-duplicated follow-up question suggestions based on the current question and conversation history.
- Conversation history is saved automatically, with support for restoring one conversation, deleting one history item, and clearing all history.

#### 2. Data Source Management

The data source page reads the current SQLite schema directly and displays queryable business tables, fields, meanings, data types, purposes, sample values, and sample rows. Each table also provides clickable suggested questions that can jump back to the intelligent query workspace.

![Data source management](docs/assets/readme/datasource.png)

Key capabilities:

- Automatically introspects the current database schema.
- Shows only user-queryable business tables.
- Labels field roles: filter/grouping dimensions, aggregatable metrics, text descriptions, and more.
- Generates clickable suggested questions from table schemas.

#### 3. Knowledge Management

The knowledge page manages retrieval-augmented context for Text-to-SQL, including business definitions, SQL examples, field descriptions, and table relationships. Before generating SQL, the system retrieves related knowledge to help the model understand business meanings and constraints.

![Knowledge management](docs/assets/readme/knowledge.png)

Key capabilities:

- Manages private and public knowledge entries.
- Filters knowledge by tags, type, and scope.
- Maintains links between knowledge entries and data tables.
- Supports model sync, field sync, and conflict hints.

#### 4. Dashboard

Analysis results can be saved as dashboard cards. Dashboards support two-column layout, drag-and-drop ordering, chart type switching, filters, refresh, removal, local read-only sharing, and renaming.

![Dashboard](docs/assets/readme/dashboard.png)

Key capabilities:

- Creates dashboards with custom names and supports renaming later.
- Saves intelligent query charts as dashboard cards.
- Supports line, bar, pie, scatter, stacked bar, and table views.
- Provides year, region, and metric filters.
- Generates a local read-only share page.

#### 5. Runtime Settings

The runtime settings page shows the active model mode and configures/tests the DeepSeek API. The API key is only submitted to the local backend at runtime; the page never displays the full key and the key should not be committed to Git.

![Runtime settings](docs/assets/readme/settings.png)

Key capabilities:

- Shows the active mode: offline rules or DeepSeek online mode.
- Displays the API key in masked form.
- Configures Base URL, model, and API key.
- Tests DeepSeek connectivity and shows clear errors when the test fails.

### Architecture

```text
Frontend: React + Vite + TypeScript
├─ Query Workspace
│  ├─ Main intelligent query flow
│  ├─ Conversation history panel
│  ├─ Model configuration entry
│  └─ Chart results and follow-up suggestions
├─ DataSource Workspace
│  └─ Database schema, field descriptions, sample rows, suggested questions
├─ Knowledge Workspace
│  └─ Knowledge entries, tag filters, table relationships
├─ Dashboard Workspace
│  ├─ Dashboard management and renaming
│  ├─ Card layout and drag-and-drop ordering
│  └─ Chart switching, filters, and sharing
└─ Settings Workspace
   └─ DeepSeek API setup and connection test

REST API

Backend: FastAPI + SQLAlchemy
├─ api/
│  ├─ chat.py           Conversations, queries, history delete / clear
│  ├─ dashboards.py     Dashboards, cards, rename, sharing
│  ├─ datasource.py     Schema and sample data
│  ├─ knowledge.py      Knowledge management
│  └─ model_settings.py Model runtime settings
├─ services/
│  ├─ conversation_*    Conversation orchestration, history, context, SQL repair, traces
│  ├─ text_to_sql.py    DeepSeek Text-to-SQL integration
│  ├─ sql_guard.py      Read-only SQL validation
│  ├─ datasource.py     SQLite schema introspection
│  ├─ knowledge.py      Knowledge retrieval and sync
│  └─ dashboards.py     Dashboard and card services
└─ domain/
   └─ real_estate.py    Real-estate demo domain configuration

SQLite demo database
└─ backend/runtime/daas_demo.db
   ├─ house_price_monthly
   ├─ housing_transactions
   ├─ district_population
   ├─ commuting_metrics
   ├─ knowledge_items
   ├─ semantic_metrics
   ├─ conversations / messages / analysis_runs
   └─ dashboards / dashboard_cards / share_links
```

### Project Structure

```text
backend/
  app/
    api/          FastAPI routers
    domain/       Business domain configuration
    services/     Query, knowledge, SQL, guardrail, dashboard, and datasource services
    config.py     Environment and runtime settings
    db.py         SQLAlchemy engine/session
    seed.py       SQLite schema and demo data
  data/           Portable demo database package
  runtime/        Local runtime database
  tests/          Backend tests

frontend/
  src/
    pages/        Query, datasource, knowledge, dashboard, and settings pages
    components/   Charts, timeline, badges, datasource cards
    utils/        Dashboard filters and helpers
    test/         Frontend tests

docs/
  assets/readme/  README screenshots
  superpowers/    Design documents and implementation plans

start-demo.ps1    Windows one-click startup script
```

### Run Locally

Recommended from the project root:

```powershell
powershell -ExecutionPolicy Bypass -File .\start-demo.ps1
```

You can also start backend and frontend separately:

```powershell
python -m uvicorn backend.app.main:app --reload --port 8000
npm --prefix frontend install
npm --prefix frontend run dev
```

URLs:

- Frontend: http://127.0.0.1:5173
- Backend API: http://127.0.0.1:8000

### DeepSeek Configuration

By default, the project runs with offline rules when no API key is configured:

```env
LLM_MODE=offline
```

To enable DeepSeek, fill it in from “Configure DeepSeek API” / “Runtime Settings”, or configure a local `.env` file:

```env
LLM_MODE=deepseek
DEEPSEEK_API_KEY=sk-...
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-v4-flash
```

Without DeepSeek credentials, the system continues to work in offline rule-based demo mode.

### Tests

```powershell
python -m pytest backend/tests -q
npm --prefix frontend run test:run
npm --prefix frontend run build
```
