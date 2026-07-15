# GeniusQ DaaS Platform Intelligent Query Demo

[中文](#中文说明) | [English](#english)

## 中文说明

GeniusQ DaaS Platform Intelligent Query Demo 是“智能问数优化需求 0714”的实习交付项目，包含一份实施计划书和一个可在 Windows 本地运行的全栈 Demo。项目不修改生产平台源码、不连接生产数据，通过 FastAPI、SQLite、React 和 TypeScript 复刻平台式工作流，用于验证智能问数、知识治理、仪表盘与需求追踪的产品和工程可行性。

### 交付物

- `docs/智能问数优化实施计划书.md`：Markdown 版实施计划书。
- `docs/智能问数优化实施计划书.docx`：Word 版实施计划书。
- `docs/需求追踪矩阵.md`：15 个需求编号到页面、API、测试和验收动作的映射。
- `backend/`：FastAPI、SQLite、离线分析引擎、只读 SQL、安全边界与 Pytest。
- `frontend/`：React/Vite 平台壳与智能问数、知识库、仪表盘、需求映射工作区。
- `start-demo.ps1`：依赖检查、初始化、健康检查和浏览器打开的一键启动脚本。

### 环境要求

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

- 智能问数：澄清建议、可审计业务步骤、数据来源、只读 SQL、图表切换、洞察和推荐追问。
- 多轮追问：继承并显式覆盖年份、区域和指标上下文。
- 多源分析：将房产、人口、通勤问题拆成多条只读 SQL 并汇总解释。
- 知识治理：指纹查重、私有优先、公开/私有覆盖关系、标签筛选、数据表关联、同步审计和删除联动。
- 仪表盘：图表保存、两列布局、拖拽排序、空白落点提示、尺寸调整、刷新、移除和本地只读分享。
- 需求映射：需求编号、模块、优先级、页面和验收动作可追踪。

### 推荐演示脚本

1. 在“智能问数”输入“分析房价”，查看三条自动澄清建议（2.2）。
2. 点击“分析2025年各区平均房价”，展开可审计步骤，查看数据来源、Skill、只读 SQL、图表和洞察（2.1、2.4、2.5）。
3. 继续问“只看海淀区”，验证年份与指标上下文被继承（2.3）。
4. 提问“2025年房价上涨是否与人口和通勤相关”，验证问题被拆成两条跨源 SQL 并综合解释（5）。
5. 在“知识库管理”查看“行政区房价口径”，验证私有知识覆盖公开知识；分别触发手动与模拟定时同步（3.2-3.4）。
6. 从问数结果加入“房价分析看板”，在“我的仪表盘”拖动卡片、放大卡片、刷新验证持久化；复制分享链接后打开只读看板（2.6）。
7. 打开“需求映射”，按模块或优先级筛选，并展开每项验收动作。

“思考过程”仅表示意图识别、数据选择、Skill 调用、SQL 校验执行和结果生成等可审计业务步骤，不展示模型隐藏链路推理。

### 自动验证

```powershell
python -m pytest backend/tests -v --cov=app --cov-report=term-missing
cd frontend
npm.cmd run test:run
npm.cmd run build
```

端到端验收（首次需要安装 Chromium）：

```powershell
cd frontend
npx.cmd playwright install chromium
npm.cmd run e2e
```

### 模型模式

默认完全离线，验收不需要网络或 API Key：

```dotenv
LLM_MODE=offline
```

项目保留 OpenAI 兼容配置边界，后续与公司模型网关集成时使用：

```dotenv
LLM_MODE=openai-compatible
LLM_BASE_URL=https://example.com/v1
LLM_API_KEY=your-key
LLM_MODEL=your-model
```

当前交付的确定性验收路径统一使用离线引擎。浏览器端不会接收、显示或保存模型密钥；真实模型输出接入后仍必须通过相同的结构校验与只读 SQL 防线。

### 常见问题

- `python`、`node` 或 `npm.cmd` 不存在：安装对应运行时并重新打开 PowerShell。
- 8000/5173 端口被占用：关闭占用端口的旧 Demo 进程后重试，或使用 `-BackendPort` / `-FrontendPort`。
- 页面提示后端不可用：先访问 `/api/health`，确认返回 `{"status":"ok","mode":"offline"}`。
- 需要重置演示状态：停止服务后删除根目录的 `daas_demo.db`，再次启动会自动重建确定性样例数据。

## English

GeniusQ DaaS Platform Intelligent Query Demo is an internship delivery project based on the "Intelligent Query Optimization Requirements 0714" brief. It includes an implementation plan and a Windows-local full-stack demo. The project does not modify production platform source code or connect to production data. Instead, it uses FastAPI, SQLite, React, and TypeScript to reproduce the key platform workflow and validate product and engineering feasibility.

### Deliverables

- `docs/智能问数优化实施计划书.md`: implementation plan in Markdown.
- `docs/智能问数优化实施计划书.docx`: implementation plan in Word format.
- `docs/需求追踪矩阵.md`: mapping from the 15 requirements to pages, APIs, tests, and manual acceptance checks.
- `backend/`: FastAPI, SQLite, offline analysis engine, read-only SQL guardrails, and Pytest coverage.
- `frontend/`: React/Vite platform shell with Intelligent Query, Knowledge Base, Dashboard, and Requirement Mapping workspaces.
- `start-demo.ps1`: one-command Windows launcher for dependency checks, initialization, health checks, and browser opening.

### Requirements

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

- Intelligent Query: clarification suggestions, auditable business steps, data sources, read-only SQL, chart switching, insights, and follow-up prompts.
- Multi-turn context: inherit and override year, district, and metric context.
- Multi-source analysis: split housing, population, and commuting questions into multiple read-only SQL queries and summarize them.
- Knowledge governance: fingerprint deduplication, private-priority knowledge, public/private override relationships, tag filtering, table linkage, sync audit logs, and delete impact confirmation.
- Dashboard: save charts, two-column layout, drag-and-drop ordering, blank drop placeholders, resize, refresh, remove, and local read-only sharing.
- Requirement mapping: trace requirement IDs, modules, priority, pages, and acceptance actions.

### Suggested Demo Script

1. Enter "分析房价" in Intelligent Query and review three clarification suggestions (2.2).
2. Click "分析2025年各区平均房价"; expand auditable steps and inspect data sources, Skill execution, read-only SQL, charts, and insights (2.1, 2.4, 2.5).
3. Ask "只看海淀区" to verify inherited year and metric context (2.3).
4. Ask "2025年房价上涨是否与人口和通勤相关" to verify multi-source SQL planning and summary (5).
5. In Knowledge Base, inspect "行政区房价口径", verify private knowledge overrides public knowledge, and trigger manual and simulated scheduled sync (3.2-3.4).
6. Add a query result to "房价分析看板"; drag, resize, refresh, and verify persistence; copy the share link and open the read-only dashboard (2.6).
7. Open Requirement Mapping, filter by module or priority, and expand acceptance actions.

The "thinking process" is an auditable business execution timeline. It does not expose hidden model chain-of-thought.

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

The default delivery path is fully offline and deterministic:

```dotenv
LLM_MODE=offline
```

The project also keeps an OpenAI-compatible integration boundary for future model gateway integration:

```dotenv
LLM_MODE=openai-compatible
LLM_BASE_URL=https://example.com/v1
LLM_API_KEY=your-key
LLM_MODEL=your-model
```

The browser never receives, displays, or stores model credentials. Future model output must still pass the same structured validation and read-only SQL guardrails.

### Troubleshooting

- `python`, `node`, or `npm.cmd` is missing: install the runtime and reopen PowerShell.
- Port 8000 or 5173 is occupied: stop the old demo process or use `-BackendPort` / `-FrontendPort`.
- The frontend reports that the backend is unavailable: open `/api/health` and verify `{"status":"ok","mode":"offline"}`.
- To reset demo state: stop services, delete `daas_demo.db` in the repository root, and restart the demo.
