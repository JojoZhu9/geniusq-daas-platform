# GeniusQ DaaS Intelligent Query Demo

[中文](#中文说明) | [English](#english)

## 中文说明

GeniusQ DaaS Intelligent Query Demo 是一个可在本地运行的小型全栈演示项目，用于展示面向企业数据平台的智能问数体验。项目支持自然语言提问、知识检索增强、DeepSeek Text-to-SQL、只读 SQL 安全校验、本地 SQLite 查询、自动图表生成、仪表盘保存与本地只读分享。

本项目不连接生产数据，演示数据由本地 SQLite 自动生成，适合用于产品方案展示、技术可行性说明和后续平台集成前的原型验证。

### 当前阶段状态

当前阶段已完成：

- 本地 FastAPI + React/Vite 全栈 Demo。
- DeepSeek Text-to-SQL 接入，并保留离线规则引擎作为兜底模式。
- 知识检索增强：生成 SQL 前会检索私有/公共知识、SQL 示例和可用表结构。
- 只读 SQL 防线：仅允许单条 `SELECT` / `WITH` 查询，限制授权表和最大返回行数。
- 问数过程展示：生成结果时逐步展示理解问题、合并上下文、检索知识、选择表字段、调用模型、校验 SQL、执行查询和生成图表。
- 智能推荐问题：简单问题会推荐 3 个可问问题；完成分析后会结合对话历史推荐 3 个不重复的后续问题。
- 图表可靠性修复：当模型返回的图表字段与 SQL 结果不一致时，后端会按实际结果字段自动修复图表配置。
- 扩充演示数据库：覆盖房价、租金、挂牌量、空置率、成交、新房/二手、人口、收入、家庭数、通勤、地铁覆盖率、就业密度等维度。
- 页面配置 DeepSeek API Key：用户可在演示页面填写 Key，本次本地后端运行时生效；Key 不会回传显示，也不会写入仓库。
- 仪表盘：支持两列布局、图表保存、拖拽排序、空白落点占位提示、刷新、移除和本地只读分享。

### 技术架构

```text
React / Vite / TypeScript
        │
        ▼
FastAPI REST API
        │
        ├── Conversation & reasoning workflow
        ├── Knowledge retrieval
        ├── DeepSeek Text-to-SQL
        ├── SQL guard
        ├── Chart repair / fallback
        └── Dashboard service
        │
        ▼
SQLite demo database
```

### 项目结构

```text
backend/        FastAPI 后端、SQLite seed、SQL Guard、问数/知识库/仪表盘 API
frontend/       React + Vite 前端页面与组件
docs/           计划书、设计文档和阶段交付文档
start-demo.ps1  Windows 一键启动脚本
```

### 运行环境

- Windows 10/11
- PowerShell 5.1+
- Python 3.9+
- Node.js 18+

### 一键启动

在项目根目录执行：

```powershell
powershell -ExecutionPolicy Bypass -File .\start-demo.ps1
```

只启动服务、不自动打开浏览器：

```powershell
powershell -ExecutionPolicy Bypass -File .\start-demo.ps1 -NoBrowser
```

依赖已经安装时可跳过依赖检查：

```powershell
powershell -ExecutionPolicy Bypass -File .\start-demo.ps1 -NoBrowser -SkipInstall
```

默认访问地址：

- 前端：[http://127.0.0.1:5173](http://127.0.0.1:5173)
- 后端健康检查：[http://127.0.0.1:8000/api/health](http://127.0.0.1:8000/api/health)
- OpenAPI 文档：[http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

### 手动启动

终端一：

```powershell
python -m pip install -e "backend[test]"
python -m uvicorn app.main:app --app-dir .\backend --host 127.0.0.1 --port 8000
```

终端二：

```powershell
cd frontend
npm.cmd ci
npm.cmd run dev -- --port 5173
```

### DeepSeek 配置

项目默认可使用离线演示模式：

```dotenv
LLM_MODE=offline
```

如果希望启用真实 DeepSeek Text-to-SQL，有两种方式：

1. 在页面点击“配置 DeepSeek API”，填入 API Key 和模型名。
2. 在本地创建 `.env` 文件：

```dotenv
LLM_MODE=deepseek
DEEPSEEK_API_KEY=your-deepseek-api-key
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-v4-flash
```

真实 Key 只应保存在本地，不要提交到 GitHub。无论模型如何生成 SQL，后端都会先执行结构化解析和只读 SQL 校验，通过后才会查询本地 SQLite。

项目也保留 OpenAI-compatible 模型服务的配置边界，便于后续替换或扩展其他大模型网关：

```dotenv
LLM_MODE=openai-compatible
LLM_BASE_URL=https://example.com/v1
LLM_API_KEY=your-key
LLM_MODEL=your-model
```

### 可测试问题示例

```text
分析2025年各区平均房价趋势
分析2025年海淀区和朝阳区租金趋势
哪个区挂牌量最高，空置率如何
房价是否和地铁覆盖率、就业密度相关
对比2024年和2025年各区房价变化
```

### 验证命令

```powershell
python -m pytest backend/tests -q
cd frontend
npm.cmd run test:run
npm.cmd run build
```

当前阶段验证结果：

- 后端测试：48 passed
- 前端测试：22 passed
- 前端生产构建：passed

### 常见问题

- 页面提示后端不可用：先访问 `/api/health`，确认后端是否启动。
- 图表为空或字段不匹配：当前版本后端会自动校验并修复图表字段；如仍出现问题，可刷新页面或重新提问。
- 想重置演示数据：停止服务后删除根目录 `daas_demo.db`，再次启动会自动重建。
- DeepSeek 不生效：检查页面配置或 `.env` 中的 `LLM_MODE`、`DEEPSEEK_API_KEY`、`DEEPSEEK_BASE_URL` 和 `DEEPSEEK_MODEL`。

## English

GeniusQ DaaS Intelligent Query Demo is a local full-stack demo for intelligent data querying in an enterprise data-platform scenario. It supports natural-language questions, retrieval-augmented knowledge context, DeepSeek Text-to-SQL, read-only SQL validation, local SQLite execution, automatic chart generation, dashboard saving, and local read-only sharing.

The project does not connect to production data. Demo data is generated locally in SQLite, making the project suitable for product walkthroughs, technical feasibility validation, and pre-integration prototyping.

### Current Stage

The current stage includes:

- A local FastAPI + React/Vite full-stack demo.
- DeepSeek Text-to-SQL integration with an offline rule-based fallback mode.
- Retrieval-augmented SQL generation using private/public knowledge, SQL examples, and available table schemas.
- Read-only SQL guardrails: only single-statement `SELECT` / `WITH` queries are allowed, with authorized-table checks and row limits.
- Step-by-step reasoning progress while generating results.
- Smart recommendations: simple questions produce three suggested questions, and completed analyses produce three non-repeated follow-up questions based on conversation history.
- Chart reliability repair: if model-suggested chart fields do not match SQL result fields, the backend rebuilds a valid chart configuration from actual result columns.
- Enriched demo database dimensions: house price, rent, listing count, vacancy rate, transactions, new/second-hand housing, population, income, households, commute, metro coverage, and employment density.
- In-page DeepSeek API configuration: users can enter an API key for the current local backend runtime; the key is not echoed to the browser and is not written to the repository.
- Dashboard features: two-column layout, chart saving, drag-and-drop ordering, blank-drop placeholders, refresh, removal, and local read-only sharing.

### Architecture

```text
React / Vite / TypeScript
        │
        ▼
FastAPI REST API
        │
        ├── Conversation & reasoning workflow
        ├── Knowledge retrieval
        ├── DeepSeek Text-to-SQL
        ├── SQL guard
        ├── Chart repair / fallback
        └── Dashboard service
        │
        ▼
SQLite demo database
```

### Project Structure

```text
backend/        FastAPI backend, SQLite seed data, SQL Guard, query/knowledge/dashboard APIs
frontend/       React + Vite frontend pages and components
docs/           Plans, design documents, and stage deliverables
start-demo.ps1  Windows one-command launcher
```

### Requirements

- Windows 10/11
- PowerShell 5.1+
- Python 3.9+
- Node.js 18+

### Quick Start

Run from the repository root:

```powershell
powershell -ExecutionPolicy Bypass -File .\start-demo.ps1
```

Start services without opening a browser:

```powershell
powershell -ExecutionPolicy Bypass -File .\start-demo.ps1 -NoBrowser
```

Skip dependency checks if dependencies are already installed:

```powershell
powershell -ExecutionPolicy Bypass -File .\start-demo.ps1 -NoBrowser -SkipInstall
```

Default URLs:

- Frontend: [http://127.0.0.1:5173](http://127.0.0.1:5173)
- Backend health check: [http://127.0.0.1:8000/api/health](http://127.0.0.1:8000/api/health)
- OpenAPI docs: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

### Manual Start

Terminal 1:

```powershell
python -m pip install -e "backend[test]"
python -m uvicorn app.main:app --app-dir .\backend --host 127.0.0.1 --port 8000
```

Terminal 2:

```powershell
cd frontend
npm.cmd ci
npm.cmd run dev -- --port 5173
```

### DeepSeek Configuration

The default mode can run fully offline:

```dotenv
LLM_MODE=offline
```

To enable real DeepSeek Text-to-SQL, choose either option:

1. Click “Configure DeepSeek API” in the UI and enter the API key and model name.
2. Create a local `.env` file:

```dotenv
LLM_MODE=deepseek
DEEPSEEK_API_KEY=your-deepseek-api-key
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-v4-flash
```

Real keys should stay local and must not be committed to GitHub. SQL generated by the model is still parsed and validated by the backend read-only SQL guard before querying local SQLite.

The project also keeps an OpenAI-compatible configuration boundary for future model gateways:

```dotenv
LLM_MODE=openai-compatible
LLM_BASE_URL=https://example.com/v1
LLM_API_KEY=your-key
LLM_MODEL=your-model
```

### Sample Questions

```text
Analyze average house-price trends by district in 2025
Analyze rent trends in Haidian and Chaoyang in 2025
Which district has the highest listing count and what is its vacancy rate?
Is house price related to metro coverage and employment density?
Compare district-level house-price changes between 2024 and 2025
```

### Validation

```powershell
python -m pytest backend/tests -q
cd frontend
npm.cmd run test:run
npm.cmd run build
```

Current validation result:

- Backend tests: 48 passed
- Frontend tests: 22 passed
- Production build: passed

### Troubleshooting

- Backend unavailable: open `/api/health` and confirm the service is running.
- Empty or mismatched charts: the current backend validates and repairs chart fields automatically; refresh or ask again if needed.
- Reset demo data: stop services, delete `daas_demo.db` in the repository root, and restart.
- DeepSeek not active: check the UI configuration or `.env` values for `LLM_MODE`, `DEEPSEEK_API_KEY`, `DEEPSEEK_BASE_URL`, and `DEEPSEEK_MODEL`.
