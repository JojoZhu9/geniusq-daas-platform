# 低耦合重构设计文档

## 背景

当前 Demo 已经具备 DeepSeek Text-to-SQL、知识检索增强、多轮会话、数据源查看、图表分析、仪表盘与历史会话等功能。随着功能不断扩展，部分文件开始承担过多职责：

- `backend/app/services/conversation.py` 同时负责会话上下文、SQL 生成与修复、图表建议、结果洞察、Agent 轨迹、历史会话查询。
- `frontend/src/pages/QueryWorkspace.tsx` 同时负责模型配置、历史会话、输入区、推荐问题、结果展示、Agent 过程展示。
- `frontend/src/pages/DashboardWorkspace.tsx` 同时负责仪表盘管理、卡片布局、筛选器、拖拽、图表渲染。
- 房价分析相关的业务配置散落在服务代码中，不利于后续切换行业数据或扩展业务域。

本次重构目标是降低耦合、明确模块边界，并保持现有功能、接口和页面体验不发生破坏性变化。

## 目标

1. 拆分后端 `conversation.py`，让每个模块只负责一个清晰职责。
2. 拆分前端问数页和仪表盘页，减少单文件复杂度。
3. 抽离业务域配置，将当前“房价分析演示域”的表、字段、单位、图表规则、推荐问题规则集中管理。
4. 保持原有 API 路径、前端路由、测试入口兼容。
5. 每个阶段都可以独立运行测试，避免大爆炸式重构。

## 非目标

- 不重写 Text-to-SQL 主流程。
- 不替换前端技术栈。
- 不修改 DeepSeek API 配置方式。
- 不改变用户可见的核心业务流程。
- 不引入新的状态管理库。

## 后端目标结构

将 `backend/app/services/conversation.py` 从单文件迁移为包：

```text
backend/app/services/conversation/
├── __init__.py              # 对外兼容导出 run_chat/get_analysis/list_conversations/get_conversation_history
├── service.py               # 主编排入口：run_chat/select_analysis_engine
├── context.py               # 多轮上下文合并、年份/区域/指标补全
├── charting.py              # 图表字段选择、图表修复、标题/单位/推荐理由
├── trace.py                 # Agent 工具调用轨迹与步骤状态
├── insights.py              # 结果洞察、追问推荐、问题去重
├── history.py               # 会话历史查询与分析结果读取
└── sql_repair.py            # SQL 安全修复和只读约束辅助
```

同时新增业务域配置：

```text
backend/app/domain/
├── __init__.py
├── config.py                # DomainConfig 类型与获取入口
└── real_estate.py           # 房价分析演示域配置
```

### 后端模块边界

| 模块 | 职责 | 不负责 |
|---|---|---|
| `domain/real_estate.py` | 表白名单、字段优先级、区域枚举、单位、推荐问题种子 | 调用 LLM、执行 SQL |
| `conversation/context.py` | 从历史对话和当前问题中补全年份、区域、指标 | 图表渲染、数据库查询 |
| `conversation/charting.py` | 根据查询结果生成和修复图表规格 | 生成 SQL、调用 DeepSeek |
| `conversation/trace.py` | 构造逐步 Agent 工具轨迹 | 业务数据计算 |
| `conversation/insights.py` | 生成结论摘要和后续问题推荐 | SQL 安全校验 |
| `conversation/history.py` | 历史会话和历史分析结果读取 | 新分析任务执行 |
| `conversation/service.py` | 串联检索、LLM、SQL 校验、查询、图表、洞察 | 存放业务域常量 |

## 前端目标结构

### 问数页

保留 `frontend/src/pages/QueryWorkspace.tsx` 作为兼容导出入口，将实现迁移到：

```text
frontend/src/pages/query/
├── QueryWorkspace.tsx       # 页面编排
├── components/
│   ├── ConversationHistory.tsx
│   ├── ModelConfigStrip.tsx
│   ├── QueryComposer.tsx
│   ├── QueryResult.tsx
│   ├── LiveThinkingCard.tsx
│   └── AnalysisSidePanel.tsx
├── hooks/
│   ├── useConversation.ts
│   ├── useModelSettings.ts
│   └── useQuestionSuggestions.ts
└── queryUtils.ts            # 纯函数：liveThinkingSteps、格式化等
```

### 仪表盘页

保留 `frontend/src/pages/DashboardWorkspace.tsx` 作为兼容导出入口，将实现迁移到：

```text
frontend/src/pages/dashboard/
├── DashboardWorkspace.tsx
├── components/
│   ├── DashboardCreateForm.tsx
│   ├── DashboardManagementBar.tsx
│   ├── DashboardFilters.tsx
│   ├── DashboardGrid.tsx
│   └── DashboardCardView.tsx
├── hooks/
│   ├── useDashboardState.ts
│   └── useDashboardDrag.ts
└── dashboardUtils.ts
```

## 兼容策略

- 后端继续支持 `from app.services.conversation import run_chat`。
- 前端测试继续支持从 `frontend/src/pages/QueryWorkspace.tsx` 和 `frontend/src/pages/DashboardWorkspace.tsx` 导入。
- API 路由不改名。
- 数据库路径不改动。
- `.env` 配置不改动。

## 风险与控制

1. Python 模块从单文件迁移为包时，不能同时存在 `conversation.py` 和 `conversation/` 同名包。迁移时需要在同一次提交中删除旧文件并新增包目录。
2. 前端拆组件可能造成 props 传递过深。本次只做轻量拆分，不引入 Redux/Zustand。
3. 业务域配置抽离后，测试需要覆盖常量迁移是否保持行为一致。
4. Agent 轨迹、推荐问题和图表建议依赖上下文，需要保持多轮测试通过。

## 验收标准

每个阶段完成后都必须通过：

```powershell
python -m pytest backend/tests -q
npm.cmd --prefix frontend run test:run
npm.cmd --prefix frontend run build
```

人工核查：

1. 进入智慧问数页，可以正常发送问题。
2. DeepSeek 已配置时可以走在线模式；未配置或失败时可以降级本地规则。
3. Agent 步骤仍然逐步显示工具调用。
4. 历史会话可以查看并恢复上下文。
5. 数据源页布局不随最后两个表左移。
6. 仪表盘可以新建命名、保存图表、筛选、切换图表类型。

