# 极智 DAAS 智能问数优化 Demo

本项目是“智能问数优化需求 0714”的实习交付物，包含正式实施计划书与可在 Windows 本地运行的全栈 Demo。它不修改极智 DAAS 生产源码、不连接公司生产数据，通过 FastAPI、SQLite、React 和 TypeScript 复刻平台式工作流，验证需求的产品与工程可行性。

## 交付物

- `docs/智能问数优化实施计划书.md`：面向产品、研发和验收人员的正式计划书。
- `docs/需求追踪矩阵.md`：15 个石墨需求编号到页面、API、测试和验收动作的映射。
- `backend/`：FastAPI、SQLite、离线分析引擎、只读 SQL、安全边界与 Pytest。
- `frontend/`：React/Vite 平台壳与智能问数、知识库、仪表盘、需求映射工作区。
- `start-demo.ps1`：依赖检查、初始化、健康检查和浏览器打开的一键启动脚本。

## 环境要求

- Windows 10/11 与 PowerShell 5.1+
- Python 3.9+
- Node.js 18+

## 一键启动

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

## 手动启动

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

## 模型模式

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

## 推荐演示脚本

1. 在“智能问数”输入“分析房价”，查看三条自动澄清建议（2.2）。
2. 点击“分析2025年各区平均房价”，展开可审计步骤，查看数据来源、Skill、只读 SQL、图表和洞察（2.1、2.4、2.5）。
3. 继续问“只看海淀区”，验证年份与指标上下文被继承（2.3）。
4. 提问“2025年房价上涨是否与人口和通勤相关”，验证问题被拆成两条跨源 SQL 并综合解释（5）。
5. 在“知识库管理”查看“行政区房价口径”，验证私有知识覆盖公开知识；分别触发手动与模拟定时同步（3.2–3.4）。
6. 从问数结果加入“房价分析看板”，在“我的仪表盘”放大、移动、刷新和复制分享链接（2.6）。
7. 打开“需求映射”，按模块或优先级筛选，并展开每项验收动作。

“思考过程”仅表示意图识别、数据选择、Skill 调用、SQL 校验执行和结果生成等可审计业务步骤，不展示模型隐藏链路推理。

## 自动验证

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

## 常见问题

- `python`、`node` 或 `npm.cmd` 不存在：安装对应运行时并重新打开 PowerShell。
- 8000/5173 端口被占用：关闭占用端口的旧 Demo 进程后重试。
- 页面提示后端不可用：先访问 `/api/health`，确认返回 `{"status":"ok","mode":"offline"}`。
- 需要重置演示状态：停止服务后删除根目录的 `daas_demo.db`，再次启动会自动重建确定性样例数据。
