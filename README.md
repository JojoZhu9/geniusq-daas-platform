# GeniusQ DaaS Platform Intelligent Query Demo

[中文](#中文说明) | [English](#english)

## 中文说明

GeniusQ DaaS Platform Intelligent Query Demo 是一个实习期间完成的小型本地演示项目，用于展示智能问数、知识治理、仪表盘分析和本地分享等核心交互。项目不连接生产数据、不依赖线上服务，通过 FastAPI、SQLite、React 和 TypeScript 搭建一个可在 Windows 本地运行的全栈 Demo。

### 项目内容

- `backend/`：FastAPI 服务、本地 SQLite 数据、离线分析逻辑、只读 SQL 校验和自动化测试。
- `frontend/`：React/Vite 前端，包含智能问数、知识库管理、仪表盘和映射页面。
- `docs/智能问数优化实施计划书.md`：Markdown 版计划书。
- `docs/智能问数优化实施计划书.docx`：Word 版计划书。
- `start-demo.ps1`：Windows 一键启动脚本。

### 运行环境

- Windows 10/11 与 PowerShell 5.1+
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

依赖已经安装时可跳过安装检查：

```powershell
powershell -ExecutionPolicy Bypass -File .\start-demo.ps1 -NoBrowser -SkipInstall
```

默认端口被占用时可临时指定其他端口：

```powershell
powershell -ExecutionPolicy Bypass -File .\start-demo.ps1 -BackendPort 18001 -FrontendPort 15174
```

启动地址：

- 前端：[http://127.0.0.1:5173](http://127.0.0.1:5173)
- 后端健康检查：[http://127.0.0.1:8000/api/health](http://127.0.0.1:8000/api/health)
- OpenAPI：[http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

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

### 功能范围

- 智能问数：支持自然语言提问、澄清建议、业务步骤展示、数据来源、只读 SQL、图表切换和结果洞察。
- 多轮追问：保留上下文，并允许用户在后续问题中覆盖年份、区域和指标。
- 多源分析：可以把涉及多个数据主题的问题拆成多条查询，再汇总成统一解释。
- 知识库管理：支持知识查重、私有优先、标签筛选、数据表关联、同步记录和删除影响确认。
- 仪表盘：支持图表保存、两列布局、拖拽排序、空白落点提示、尺寸调整、刷新、移除和本地只读分享。
- 映射页面：用于展示功能项、页面、接口和人工验收动作之间的关系。

### 自动验证

```powershell
python -m pytest backend/tests -v --cov=app --cov-report=term-missing
cd frontend
npm.cmd run test:run
npm.cmd run build
```

端到端验证：

```powershell
cd frontend
npx.cmd playwright install chromium
npm.cmd run e2e
```

### 模型模式

默认使用完全离线的确定性演示模式，不需要网络或 API Key：

```dotenv
LLM_MODE=offline
```

如需启用真实 DeepSeek Text-to-SQL，可在本地复制 `.env.example` 为 `.env`，并填写自己的 Key：

```dotenv
LLM_MODE=deepseek
DEEPSEEK_API_KEY=your-deepseek-api-key
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-v4-flash
```

真实 Key 只应保存在本地 `.env`，不要提交到 GitHub。DeepSeek 官方文档当前推荐的模型名包括 `deepseek-v4-flash` 和 `deepseek-v4-pro`；如果你希望更强的推理能力，可以把 `DEEPSEEK_MODEL` 改成 `deepseek-v4-pro`。DeepSeek 生成的 SQL 会先经过后端只读 SQL 校验，只有通过校验后才会查询本地 SQLite。

项目也保留 OpenAI 兼容配置边界，后续接入其他模型服务时可使用：

```dotenv
LLM_MODE=openai-compatible
LLM_BASE_URL=https://example.com/v1
LLM_API_KEY=your-key
LLM_MODEL=your-model
```

浏览器端不会接收、显示或保存模型密钥；模型输出接入后仍应通过后端结构校验与只读 SQL 防线。

### 常见问题

- `python`、`node` 或 `npm.cmd` 不存在：安装对应运行时并重新打开 PowerShell。
- 8000/5173 端口被占用：关闭占用端口的旧 Demo 进程后重试，或使用 `-BackendPort` / `-FrontendPort`。
- 页面提示后端不可用：先访问 `/api/health`，确认返回 `{"status":"ok","mode":"offline"}`。
- 需要重置演示状态：停止服务后删除根目录的 `daas_demo.db`，再次启动会自动重建样例数据。

## English

GeniusQ DaaS Platform Intelligent Query Demo is a small local demo project completed during an internship. It showcases core interactions around intelligent querying, knowledge governance, analytical dashboards, and local read-only sharing. The project does not connect to production data or rely on online services. It uses FastAPI, SQLite, React, and TypeScript to provide a Windows-local full-stack demo.

### Project Contents

- `backend/`: FastAPI service, local SQLite data, offline analysis logic, read-only SQL validation, and automated tests.
- `frontend/`: React/Vite frontend with Intelligent Query, Knowledge Base, Dashboard, and Mapping pages.
- `docs/智能问数优化实施计划书.md`: implementation plan in Markdown.
- `docs/智能问数优化实施计划书.docx`: implementation plan in Word format.
- `start-demo.ps1`: one-command Windows launcher.

### Prerequisites

- Windows 10/11 with PowerShell 5.1+
- Python 3.9+
- Node.js 18+

### Quick Start

Run from the repository root:

```powershell
powershell -ExecutionPolicy Bypass -File .\start-demo.ps1
```

Start services without opening the browser:

```powershell
powershell -ExecutionPolicy Bypass -File .\start-demo.ps1 -NoBrowser
```

Skip dependency checks when dependencies are already installed:

```powershell
powershell -ExecutionPolicy Bypass -File .\start-demo.ps1 -NoBrowser -SkipInstall
```

Use custom ports when the defaults are occupied:

```powershell
powershell -ExecutionPolicy Bypass -File .\start-demo.ps1 -BackendPort 18001 -FrontendPort 15174
```

Default URLs:

- Frontend: [http://127.0.0.1:5173](http://127.0.0.1:5173)
- Backend health check: [http://127.0.0.1:8000/api/health](http://127.0.0.1:8000/api/health)
- OpenAPI: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

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

### Feature Scope

- Intelligent Query: natural-language questions, clarification suggestions, business step display, data sources, read-only SQL, chart switching, and result insights.
- Multi-turn follow-up: preserve context and allow later questions to override year, district, and metric.
- Multi-source analysis: split questions across multiple data topics and summarize them into one explanation.
- Knowledge management: knowledge deduplication, private-priority rules, tag filtering, data-table linkage, sync records, and delete-impact confirmation.
- Dashboard: chart saving, two-column layout, drag-and-drop ordering, blank drop placeholders, resizing, refresh, removal, and local read-only sharing.
- Mapping page: shows relationships between features, pages, APIs, and manual acceptance actions.

### Validation

```powershell
python -m pytest backend/tests -v --cov=app --cov-report=term-missing
cd frontend
npm.cmd run test:run
npm.cmd run build
```

End-to-end validation:

```powershell
cd frontend
npx.cmd playwright install chromium
npm.cmd run e2e
```

### Model Mode

The default path is fully offline and deterministic, with no network or API key required:

```dotenv
LLM_MODE=offline
```

To enable real DeepSeek Text-to-SQL, copy `.env.example` to `.env` locally and fill in your own key:

```dotenv
LLM_MODE=deepseek
DEEPSEEK_API_KEY=your-deepseek-api-key
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-v4-flash
```

The real key should stay only in your local `.env` and must not be committed to GitHub. The current DeepSeek docs recommend model names such as `deepseek-v4-flash` and `deepseek-v4-pro`; use `deepseek-v4-pro` if you want stronger reasoning. SQL generated by DeepSeek still goes through the backend read-only SQL guard before it can query the local SQLite database.

The project also keeps an OpenAI-compatible integration boundary for future model-service integration:

```dotenv
LLM_MODE=openai-compatible
LLM_BASE_URL=https://example.com/v1
LLM_API_KEY=your-key
LLM_MODEL=your-model
```

The browser never receives, displays, or stores model credentials. Future model output should still pass backend structure validation and read-only SQL guardrails.

### Troubleshooting

- `python`, `node`, or `npm.cmd` is missing: install the runtime and reopen PowerShell.
- Port 8000 or 5173 is occupied: stop the old demo process or use `-BackendPort` / `-FrontendPort`.
- The frontend reports that the backend is unavailable: open `/api/health` and verify `{"status":"ok","mode":"offline"}`.
- To reset demo state: stop services, delete `daas_demo.db` in the repository root, and restart the demo.
