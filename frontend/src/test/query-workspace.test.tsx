import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, vi } from "vitest";
import { ThinkingTimeline } from "../components/ThinkingTimeline";
import { QueryWorkspace, liveThinkingSteps } from "../pages/QueryWorkspace";

const completedAnalysis = {
  status: "completed",
  analysis_id: "a-complete",
  conversation_id: "c1",
  context: { year_from: 2025, year_to: 2025, district: null, metric: "平均房价" },
  suggestions: [],
  steps: [
    { key: "scope", title: "确认分析范围", detail: "分析 2025 年房价。", status: "completed" },
    { key: "tables", title: "选择数据表与字段", detail: "house_price_monthly：district、avg_price", status: "completed" },
    { key: "skill", title: "调用趋势与异常检测 Skill", detail: "计算趋势、最大值和异常点。", status: "completed" }
  ],
  queries: [{ source: "房产数据", sql: "SELECT district, avg_price FROM house_price_monthly" }],
  datasets: [{
    source: "房产数据",
    table: "house_price_monthly",
    tables: ["house_price_monthly"],
    updated_at: "2026-07-14T00:00:00+08:00",
    confidence: 0.96,
    fields: ["district", "avg_price"],
    rows: [{ district: "海淀区", avg_price: 101200 }, { district: "朝阳区", avg_price: 78300 }]
  }],
  chart: { type: "bar", x_field: "district", y_fields: ["avg_price"], title: "2025年各区平均房价" },
  insights: ["最大值：海淀区平均房价为 101,200 元/平方米。", "趋势：整体保持温和上涨。"],
  follow_ups: ["哪些区同比涨幅最高？"],
  requirement_ids: ["2.1-a", "2.1-b", "2.1-c", "2.4-a", "2.4-b", "2.5"],
  metadata: { mode: "offline" },
  created_at: "2026-07-14T00:00:00+08:00"
};

const defaultModelSettings = {
  llm_mode: "offline",
  deepseek_base_url: "https://api.deepseek.com",
  deepseek_model: "deepseek-v4-flash",
  deepseek_api_key_configured: false
};

function json(body: unknown, status = 200) {
  return Promise.resolve(new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" }
  }));
}

function renderWorkspace() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
        <QueryWorkspace />
      </MemoryRouter>
    </QueryClientProvider>
  );
}

beforeEach(() => {
  vi.restoreAllMocks();
});

test("live thinking reveals only completed steps plus the active tool step", () => {
  expect(liveThinkingSteps(0).map((step) => step.status)).toEqual(["running"]);
  expect(liveThinkingSteps(1).map((step) => step.status)).toEqual(["completed", "running"]);
  expect(liveThinkingSteps(3).map((step) => step.status)).toEqual([
    "completed",
    "completed",
    "completed",
    "running"
  ]);
});

test("renders called tool without input and output summaries in the thinking timeline", () => {
  render(
    <ThinkingTimeline
      steps={[{
        key: "select_schema",
        title: "Select tables and fields",
        detail: "Choose the minimum schema needed for the question.",
        status: "completed",
        tool: "schema_selector",
        tool_label: "数据表字段选择器",
        input_summary: ["读取用户问题中的年份、区域和指标"],
        output_summary: ["选择 house_price_monthly 表", "使用 district、avg_price 字段"],
        input: { question: "2025 district price analysis" },
        output: { tables: ["house_price_monthly"], fields: ["district", "avg_price"] }
      }]}
    />
  );

  expect(screen.getByText("调用工具")).toBeVisible();
  expect(screen.getByText("数据表字段选择器")).toBeVisible();
  expect(screen.queryByText("输入摘要")).not.toBeInTheDocument();
  expect(screen.queryByText("输出摘要")).not.toBeInTheDocument();
  expect(screen.queryByText("选择 house_price_monthly 表")).not.toBeInTheDocument();
  expect(screen.queryByText("schema_selector")).not.toBeInTheDocument();
});

test("configures deepseek api key from the workspace", async () => {
  const fetchMock = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
    const path = String(input);
    if (path === "/api/conversations") return json({ id: "c1" }, 201);
    if (path === "/api/model-settings" && (!init?.method || init.method === "GET")) {
      return json(defaultModelSettings);
    }
    if (path === "/api/model-settings/deepseek") {
      return json({
        ...defaultModelSettings,
        llm_mode: "deepseek",
        deepseek_api_key_configured: true
      });
    }
    throw new Error(`Unexpected request: ${path}`);
  });
  vi.stubGlobal("fetch", fetchMock);

  renderWorkspace();
  await screen.findByText("配置 DeepSeek API");
  await userEvent.click(screen.getByRole("button", { name: "配置 DeepSeek API" }));
  await userEvent.type(screen.getByLabelText("DeepSeek API Key"), "sk-test-secret");
  await userEvent.click(screen.getByRole("button", { name: "保存配置" }));

  expect(await screen.findByText("DeepSeek API Key 已配置，本次本地后端运行生效")).toBeVisible();
  const configRequest = fetchMock.mock.calls.find(([input]) => String(input) === "/api/model-settings/deepseek");
  expect(configRequest?.[1]).toEqual(expect.objectContaining({ method: "POST" }));
  expect(JSON.parse(String(configRequest?.[1]?.body))).toMatchObject({
    api_key: "sk-test-secret",
    model: "deepseek-v4-flash"
  });
});

test("submits an incomplete question and offers clickable suggestions", async () => {
  vi.stubGlobal("fetch", vi.fn((input: RequestInfo | URL) => {
    const path = String(input);
    if (path === "/api/conversations") return json({ id: "c1" }, 201);
    if (path === "/api/model-settings") return json(defaultModelSettings);
    if (path === "/api/chat") return json({
      ...completedAnalysis,
      status: "needs_clarification",
      analysis_id: "a-clarify",
      queries: [],
      datasets: [],
      chart: null,
      steps: [{ key: "scope", title: "检查分析范围", detail: "缺少时间范围", status: "completed" }],
      suggestions: ["分析2025年各区平均房价", "分析2024—2025年房价趋势", "只看海淀区房价"],
      insights: ["当前问题未指定房价分析的时间范围。"],
      requirement_ids: ["2.2"]
    });
    throw new Error(`Unexpected request: ${path}`);
  }));

  renderWorkspace();
  const input = await screen.findByPlaceholderText("请输入想分析的问题");
  await userEvent.type(input, "分析房价");
  await userEvent.click(screen.getByRole("button", { name: "发送" }));

  expect(await screen.findByRole("button", { name: "分析2025年各区平均房价" })).toBeVisible();
  expect(screen.getByRole("link", { name: "需求 2.2" })).toBeVisible();
  expect(screen.queryByText("SQL 查询")).not.toBeInTheDocument();
});

test("shows the history panel even before any conversation has results", async () => {
  vi.stubGlobal("fetch", vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
    const path = String(input);
    if (path === "/api/conversations" && init?.method === "POST") return json({ id: "c-empty" }, 201);
    if (path === "/api/conversations" && (!init?.method || init.method === "GET")) return json([]);
    if (path === "/api/model-settings") return json(defaultModelSettings);
    throw new Error(`Unexpected request: ${path}`);
  }));

  renderWorkspace();

  expect(await screen.findByLabelText("历史会话")).toBeVisible();
  expect(screen.getByText("暂无历史会话", { exact: false })).toBeVisible();
  expect(screen.getByRole("button", { name: "刷新历史" })).toBeVisible();
});

test("refreshes the history panel after saved conversations appear", async () => {
  let historyRequests = 0;
  vi.stubGlobal("fetch", vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
    const path = String(input);
    if (path === "/api/conversations" && init?.method === "POST") return json({ id: "c-new" }, 201);
    if (path === "/api/conversations" && (!init?.method || init.method === "GET")) {
      historyRequests += 1;
      return json(historyRequests === 1 ? [] : [{
        id: "c-saved",
        title: "历史房价分析",
        latest_question: "继续看朝阳区",
        latest_status: "completed",
        analysis_count: 3,
        created_at: "2026-07-14T00:00:00+08:00",
        updated_at: "2026-07-14T00:05:00+08:00"
      }]);
    }
    if (path === "/api/model-settings") return json(defaultModelSettings);
    throw new Error(`Unexpected request: ${path}`);
  }));

  renderWorkspace();
  expect(await screen.findByText("暂无历史会话", { exact: false })).toBeVisible();
  await userEvent.click(screen.getByRole("button", { name: "刷新历史" }));

  expect(await screen.findByRole("button", { name: /历史房价分析/ })).toBeVisible();
  expect(screen.getByText("继续看朝阳区", { exact: false })).toBeVisible();
});

test("shows a clear history error when the backend needs restarting", async () => {
  vi.stubGlobal("fetch", vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
    const path = String(input);
    if (path === "/api/conversations" && init?.method === "POST") return json({ id: "c-error" }, 201);
    if (path === "/api/conversations" && (!init?.method || init.method === "GET")) {
      return json({ code: "NOT_FOUND", message: "not found", action: "restart", request_id: "r1" }, 404);
    }
    if (path === "/api/model-settings") return json(defaultModelSettings);
    throw new Error(`Unexpected request: ${path}`);
  }));

  renderWorkspace();

  expect(await screen.findByText("历史接口暂不可用", { exact: false })).toBeVisible();
  expect(screen.getByRole("button", { name: "刷新历史" })).toBeVisible();
});

test("restores a saved conversation from the history list", async () => {
  const restoredAnalysis = {
    ...completedAnalysis,
    analysis_id: "a-restored",
    conversation_id: "c-old"
  };
  const fetchMock = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
    const path = String(input);
    if (path === "/api/conversations" && init?.method === "POST") return json({ id: "c-new" }, 201);
    if (path === "/api/conversations" && (!init?.method || init.method === "GET")) {
      return json([{
        id: "c-old",
        title: "2025区域房价分析",
        latest_question: "只看海淀区",
        latest_status: "completed",
        analysis_count: 2,
        created_at: "2026-07-14T00:00:00+08:00",
        updated_at: "2026-07-14T00:03:00+08:00"
      }]);
    }
    if (path === "/api/conversations/c-old") {
      return json({
        id: "c-old",
        title: "2025区域房价分析",
        context: restoredAnalysis.context,
        created_at: "2026-07-14T00:00:00+08:00",
        updated_at: "2026-07-14T00:03:00+08:00",
        exchanges: [{ question: "只看海淀区", response: restoredAnalysis, created_at: restoredAnalysis.created_at }]
      });
    }
    if (path === "/api/model-settings") return json(defaultModelSettings);
    throw new Error(`Unexpected request: ${path}`);
  });
  vi.stubGlobal("fetch", fetchMock);

  renderWorkspace();
  await userEvent.click(await screen.findByRole("button", { name: /2025区域房价分析/ }));

  expect((await screen.findAllByText("只看海淀区")).length).toBeGreaterThan(1);
  expect(screen.getByText("a-restor", { exact: false })).toBeVisible();
  expect(fetchMock).toHaveBeenCalledWith("/api/conversations/c-old", expect.anything());
});

test("expands auditable steps and saves the chart to a dashboard", async () => {
  const existingDashboard = {
    id: "d1",
    name: "房价分析看板",
    cards: [{ id: "existing-card", layout: { x: 0, y: 0, w: 6, h: 4 } }]
  };
  const fetchMock = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
    const path = String(input);
    if (path === "/api/conversations") return json({ id: "c1" }, 201);
    if (path === "/api/model-settings") return json(defaultModelSettings);
    if (path === "/api/chat") return json(completedAnalysis);
    if (path === "/api/dashboards" && (!init?.method || init.method === "GET")) return json([existingDashboard]);
    if (path === "/api/dashboards" && init?.method === "POST") return json({ id: "d1", name: "房价分析看板", cards: [] }, 201);
    if (path === "/api/dashboards/d1/cards") return json({ id: "card-1" }, 201);
    throw new Error(`Unexpected request: ${path}`);
  });
  vi.stubGlobal("fetch", fetchMock);

  renderWorkspace();
  const input = await screen.findByPlaceholderText("请输入想分析的问题");
  await userEvent.type(input, "分析2025年各区平均房价");
  await userEvent.click(screen.getByRole("button", { name: "发送" }));

  expect(await screen.findByRole("button", { name: "收起思考过程" })).toBeVisible();
  expect(screen.getByText("选择数据表与字段")).toBeVisible();
  expect(screen.getAllByText("house_price_monthly").length).toBeGreaterThan(0);
  await userEvent.click(screen.getByRole("button", { name: "折线" }));
  await userEvent.click(screen.getByRole("button", { name: "加入仪表盘" }));

  expect(await screen.findByText("已加入“房价分析看板”")).toBeVisible();
  await waitFor(() => expect(fetch).toHaveBeenCalledWith(
    "/api/dashboards/d1/cards",
    expect.objectContaining({ method: "POST" })
  ));
  const cardRequest = fetchMock.mock.calls.find(([input]) => String(input) === "/api/dashboards/d1/cards");
  const payload = JSON.parse(String(cardRequest?.[1]?.body));
  expect(payload.chart.type).toBe("line");
  expect(payload.layout).toEqual({ x: 6, y: 0, w: 6, h: 4 });
});

test("shows deepseek metadata and saves positive feedback", async () => {
  const deepseekAnalysis = {
    ...completedAnalysis,
    analysis_id: "a-deepseek",
    metadata: {
      mode: "deepseek",
      model: "deepseek-v4-flash",
      model_reasoning: "使用房价月度表生成趋势查询",
      confidence: 0.81,
      sql_validation_status: "passed",
      used_knowledge: [
        {
          id: "knowledge-private-house-price",
          title: "行政区房价口径",
          kind: "text",
          scope: "private",
          linked_tables: ["house_price_monthly"],
          score: 21.5
        }
      ]
    }
  };
  const fetchMock = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
    const path = String(input);
    if (path === "/api/conversations") return json({ id: "c1" }, 201);
    if (path === "/api/model-settings") return json(defaultModelSettings);
    if (path === "/api/chat") return json(deepseekAnalysis);
    if (path === "/api/analysis/a-deepseek/feedback") return json({
      id: "feedback-1",
      analysis_id: "a-deepseek",
      rating: "correct",
      comment: "SQL 正确",
      save_as_example: false,
      saved_knowledge_id: null,
      created_at: "2026-07-16T00:00:00Z"
    }, 201);
    throw new Error(`Unexpected request: ${path}`);
  });
  vi.stubGlobal("fetch", fetchMock);

  renderWorkspace();
  const input = await screen.findByPlaceholderText("请输入想分析的问题");
  await userEvent.type(input, "分析2025年各区平均房价");
  await userEvent.click(screen.getByRole("button", { name: "发送" }));

  expect(await screen.findByText("DeepSeek Text-to-SQL")).toBeVisible();
  expect(screen.getByText("行政区房价口径")).toBeVisible();
  expect(screen.getByText("使用房价月度表生成趋势查询")).toBeVisible();
  expect(screen.getByText("SQL 校验：通过")).toBeVisible();
  await userEvent.click(screen.getByRole("button", { name: "SQL 正确" }));

  expect(await screen.findByText("反馈已保存")).toBeVisible();
  expect(fetchMock).toHaveBeenCalledWith(
    "/api/analysis/a-deepseek/feedback",
    expect.objectContaining({
      method: "POST",
      body: JSON.stringify({
        rating: "correct",
        comment: "SQL 正确",
        save_as_example: false
      })
    })
  );
});
