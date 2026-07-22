import type {
  AnalysisResponse,
  ConversationDetail,
  ConversationSummary,
  Dashboard,
  DataSourceOverview,
  DataSourceTable,
  DataSourceTableDetail,
  DeepSeekConnectionTest,
  KnowledgeItem,
  ModelSettings
} from "../types";

type Method = "GET" | "POST" | "PATCH" | "DELETE";

const now = "2026-07-22T10:00:00.000Z";
const districts = ["东城区", "丰台区", "朝阳区", "海淀区", "西城区", "通州区"];
const districtPrice: Record<string, number> = {
  东城区: 108000,
  丰台区: 65000,
  朝阳区: 78000,
  海淀区: 100000,
  西城区: 122000,
  通州区: 52000
};

function monthlyRows(year = 2025, selectedDistricts = districts) {
  return selectedDistricts.flatMap((district) =>
    Array.from({ length: 12 }, (_, index) => {
      const month = `${year}-${String(index + 1).padStart(2, "0")}`;
      const base = districtPrice[district] ?? 76000;
      return {
        district,
        month,
        avg_price: Math.round(base + index * 420 + (district.length % 3) * 300),
        mom_change: Number((0.4 + index * 0.03).toFixed(2)),
        yoy_change: Number((2.8 + index * 0.08).toFixed(2))
      };
    })
  );
}

const chart = {
  type: "line" as const,
  x_field: "month",
  y_fields: districts,
  title: "2025年各区房价趋势",
  x_axis_name: "月份",
  y_axis_name: "平均房价",
  unit: "元/平方米",
  series_mode: "district",
  recommended_reason: "按月份观察多个区域的连续变化，推荐使用折线图。"
};

const dataset = {
  source: "SQLite 演示库",
  table: "house_price_monthly",
  tables: ["house_price_monthly"],
  updated_at: now,
  confidence: 0.94,
  fields: ["district", "month", "avg_price", "mom_change", "yoy_change"],
  rows: monthlyRows()
};

const completedAnalysis: AnalysisResponse = {
  status: "completed",
  analysis_id: "static-demo-analysis",
  conversation_id: "static-demo-conversation",
  context: { year_from: 2025, year_to: 2025, district: null, metric: "avg_price" },
  suggestions: [],
  steps: [
    { key: "understand", title: "理解用户问题", detail: "识别到用户希望按行政区和月份查看 2025 年平均房价趋势。", status: "completed", tool_label: "问题解析器" },
    { key: "knowledge", title: "检索问数知识", detail: "命中房价口径、字段说明和可用数据表。", status: "completed", tool_label: "知识检索" },
    { key: "schema", title: "选择数据表与字段", detail: "选择 house_price_monthly 表中的 month、district、avg_price 字段。", status: "completed", tool_label: "Schema Selector" },
    { key: "sql", title: "生成只读 SQL", detail: "生成按月份和区域查询平均房价的只读 SQL。", status: "completed", tool_label: "DeepSeek Text-to-SQL" },
    { key: "guard", title: "校验 SQL 安全性", detail: "SQL 通过 SELECT/WITH、单语句和表白名单校验。", status: "completed", tool_label: "SQL Guard" },
    { key: "query", title: "执行查询并推荐图表", detail: "返回 72 条记录，推荐使用折线图观察连续趋势。", status: "completed", tool_label: "SQLite Query" }
  ],
  queries: [{
    source: "house_price_monthly",
    sql: "SELECT month, district, avg_price FROM house_price_monthly WHERE month BETWEEN '2025-01' AND '2025-12' ORDER BY month, district"
  }],
  datasets: [dataset],
  chart,
  insights: [
    "西城区与海淀区保持较高房价水平，通州区整体较低。",
    "各区月度趋势整体平稳上行，适合继续查看同比和环比变化。",
    "该部署版使用静态演示数据；本地运行时可连接 FastAPI 和 SQLite 获取真实后端结果。"
  ],
  follow_ups: ["哪个区域涨幅最大？", "只看海淀区的月度趋势", "房价变化是否和人口或通勤相关？"],
  requirement_ids: [],
  metadata: {
    mode: "static-demo",
    model: "DeepSeek Text-to-SQL 演示模式",
    confidence: 0.94,
    sql_validation_status: "passed",
    used_knowledge: [{
      id: "knowledge-public-house-price",
      title: "行政区房价口径",
      kind: "text",
      scope: "public",
      linked_tables: ["house_price_monthly"],
      score: 0.92
    }],
    used_metrics: [{
      id: "metric-avg-price",
      name: "平均房价",
      formula: "avg_price",
      fields: ["avg_price"],
      tables: ["house_price_monthly"],
      description: "按行政区和月份统计的平均房价。"
    }]
  },
  created_at: now
};

const clarificationAnalysis: AnalysisResponse = {
  ...completedAnalysis,
  status: "needs_clarification",
  analysis_id: "static-demo-clarification",
  chart: null,
  datasets: [],
  queries: [],
  insights: ["当前问题较宽泛，建议补充年份、区域或指标后再执行查询。"],
  suggestions: ["分析2025年各区平均房价", "只看海淀区", "2025年房价上涨是否与人口和通勤相关"],
  follow_ups: []
};

let dashboards: Dashboard[] = [{
  id: "static-dashboard",
  name: "房价分析看板",
  share_id: "static-share",
  share_url: "/share/static-share",
  requirement_ids: [],
  cards: [{
    id: "static-card-1",
    title: "2025年各区房价趋势",
    analysis_id: completedAnalysis.analysis_id,
    chart,
    datasets: [dataset],
    layout: { x: 0, y: 0, w: 6, h: 4 }
  }]
}];

const conversations: ConversationSummary[] = [{
  id: "static-demo-conversation",
  title: "2025年各区平均房价",
  latest_question: "分析2025年各区平均房价",
  latest_status: "completed",
  analysis_count: 1,
  created_at: now,
  updated_at: now
}];

const knowledge: KnowledgeItem[] = [{
  id: "knowledge-public-house-price",
  name: "行政区房价口径（公开）",
  kind: "text",
  scope: "public",
  library: "公共知识库",
  content: "平均房价按行政区和月份统计，单位为元/平方米。",
  linked_tables: ["house_price_monthly"],
  tags: ["房价", "演示"],
  schema_status: "valid",
  overrides_id: null,
  conflict: null,
  requirement_ids: []
}, {
  id: "knowledge-sql-trend",
  name: "月度房价趋势 SQL 模型",
  kind: "sql",
  scope: "private",
  library: "个人知识库",
  content: "SELECT month, district, avg_price FROM house_price_monthly",
  linked_tables: ["house_price_monthly"],
  tags: ["SQL", "趋势"],
  schema_status: "valid",
  overrides_id: null,
  conflict: null,
  requirement_ids: []
}];

const tables: DataSourceTable[] = [
  { name: "house_price_monthly", title: "房价月度指标", description: "按行政区和月份记录平均房价、环比和同比。", row_count: 144, column_count: 8 },
  { name: "housing_transactions", title: "住房成交指标", description: "按行政区和月份记录成交套数、成交面积和成交均价。", row_count: 144, column_count: 7 },
  { name: "district_population", title: "区域人口指标", description: "按行政区和年份记录常住人口与人口变化。", row_count: 12, column_count: 6 },
  { name: "commuting_metrics", title: "通勤与就业指标", description: "按行政区和年份记录通勤时间与就业机会。", row_count: 12, column_count: 6 },
  { name: "knowledge_items", title: "知识库条目", description: "记录私有和公共知识，用于增强 Text-to-SQL。", row_count: 6, column_count: 12 },
  { name: "semantic_metrics", title: "语义指标库", description: "记录业务指标、公式和字段映射。", row_count: 4, column_count: 9 }
];

function tableDetail(name: string): DataSourceTableDetail {
  const table = tables.find((item) => item.name === name) ?? tables[0];
  const rows: Record<string, string | number>[] = name === "house_price_monthly" ? monthlyRows(2025, ["东城区"]).slice(0, 5) : monthlyRows(2025, ["海淀区"]).slice(0, 5);
  return {
    ...table,
    columns: Object.keys(rows[0] ?? { id: "demo" }).map((key, index) => ({
      name: key,
      type: typeof rows[0]?.[key] === "number" ? "REAL" : "TEXT",
      label: key === "avg_price" ? "平均房价" : key,
      role: index < 2 ? "筛选 / 分组维度" : "可聚合指标",
      is_primary_key: index < 2,
      sample_value: rows[0]?.[key] ?? null
    })),
    sample_rows: rows,
    suggested_questions: [
      `2025年${table.title}趋势如何？`,
      "哪个区域变化最大？",
      "按区域对比核心指标"
    ]
  };
}

function response<T>(value: T, delay = 160): Promise<T> {
  return new Promise((resolve) => window.setTimeout(() => resolve(value), delay));
}

function parseBody(init?: RequestInit) {
  if (!init?.body || typeof init.body !== "string") return {};
  try { return JSON.parse(init.body) as Record<string, unknown>; } catch { return {}; }
}

export function staticDemoRequest<T>(path: string, init?: RequestInit): Promise<T> {
  const method = (init?.method ?? "GET") as Method;
  const cleanPath = path.split("?")[0];
  const body = parseBody(init);

  if (cleanPath === "/api/model-settings") {
    return response({
      llm_mode: "static-demo",
      deepseek_base_url: "https://api.deepseek.com",
      deepseek_model: "deepseek-v4-flash",
      deepseek_api_key_configured: false,
      deepseek_api_key_masked: ""
    } satisfies ModelSettings as T);
  }
  if (cleanPath === "/api/model-settings/deepseek") return staticDemoRequest<T>("/api/model-settings", init);
  if (cleanPath === "/api/model-settings/deepseek/test") {
    return response({ ok: false, mode: "static-demo", message: "部署演示模式不会连接真实 DeepSeek API。", error_type: "missing_api_key" } satisfies DeepSeekConnectionTest as T);
  }
  if (cleanPath === "/api/conversations" && method === "POST") {
    return response({ id: "static-demo-conversation" } as T);
  }
  if (cleanPath === "/api/conversations" && method === "GET") return response(conversations as T);
  if (cleanPath === "/api/conversations" && method === "DELETE") return response(undefined as T);
  if (cleanPath.startsWith("/api/conversations/")) {
    return response({
      id: "static-demo-conversation",
      title: "2025年各区平均房价",
      context: completedAnalysis.context,
      created_at: now,
      updated_at: now,
      exchanges: [{ question: "分析2025年各区平均房价", response: completedAnalysis, created_at: now }]
    } satisfies ConversationDetail as T);
  }
  if (cleanPath === "/api/chat") {
    const question = String(body.question ?? "");
    return response((question.length < 6 ? clarificationAnalysis : completedAnalysis) as T, 900);
  }
  if (cleanPath.startsWith("/api/analysis/")) return response({ status: "ok" } as T);
  if (cleanPath === "/api/datasource/overview") {
    return response({
      database: { engine: "SQLite", url: "sqlite:///backend/runtime/daas_demo.db（静态演示数据）" },
      table_count: 6,
      column_count: 48,
      row_count: 322,
      business_tables: tables.map((item) => item.name)
    } satisfies DataSourceOverview as T);
  }
  if (cleanPath === "/api/datasource/tables") return response(tables as T);
  if (cleanPath.startsWith("/api/datasource/tables/")) return response(tableDetail(decodeURIComponent(cleanPath.split("/").at(-1) ?? "")) as T);
  if (cleanPath === "/api/knowledge") return response(knowledge as T);
  if (cleanPath === "/api/sync/logs") return response([] as T);
  if (cleanPath === "/api/sync") return response({ message: "静态演示模式：已模拟同步完成" } as T);
  if (cleanPath.startsWith("/api/data-tables/")) return response({ linked_items_removed: 1 } as T);
  if (cleanPath.startsWith("/api/knowledge")) return response({ id: "static-knowledge-new" } as T);
  if (cleanPath === "/api/dashboards" && method === "GET") return response(dashboards as T);
  if (cleanPath === "/api/dashboards" && method === "POST") {
    const next: Dashboard = { id: `static-dashboard-${dashboards.length + 1}`, name: String(body.name ?? "新建仪表盘"), share_id: "static-share", share_url: "/share/static-share", cards: [], requirement_ids: [] };
    dashboards = [...dashboards, next];
    return response(next as T);
  }
  if (cleanPath.startsWith("/api/dashboards/share/")) return response((dashboards[0] ?? null) as T);
  if (cleanPath.includes("/cards") && method === "POST") {
    const cardBody = body as Partial<Dashboard["cards"][number]>;
    const nextCard = {
      id: `static-card-${Date.now()}`,
      title: String(cardBody.title ?? "静态演示图表"),
      analysis_id: String(cardBody.analysis_id ?? completedAnalysis.analysis_id),
      chart: cardBody.chart ?? chart,
      datasets: cardBody.datasets ?? [dataset],
      layout: cardBody.layout ?? { x: 0, y: dashboards[0]?.cards.length ?? 0, w: 6, h: 4 }
    };
    dashboards = dashboards.map((item) => item.id === cleanPath.split("/")[3] ? { ...item, cards: [...item.cards, nextCard] } : item);
    return response(nextCard as T);
  }
  if (cleanPath.includes("/layout") && method === "PATCH") {
    const id = cleanPath.split("/")[3];
    const layoutCards = Array.isArray(body.cards) ? body.cards as { id: string; layout: Dashboard["cards"][number]["layout"] }[] : [];
    dashboards = dashboards.map((item) => item.id === id ? {
      ...item,
      cards: item.cards.map((card) => {
        const update = layoutCards.find((next) => next.id === card.id);
        return update ? { ...card, layout: update.layout } : card;
      })
    } : item);
    return response((dashboards.find((item) => item.id === id) ?? dashboards[0]) as T);
  }
  if (cleanPath.startsWith("/api/dashboards/") && method === "PATCH") {
    const id = cleanPath.split("/")[3];
    dashboards = dashboards.map((item) => item.id === id ? { ...item, name: String(body.name ?? item.name) } : item);
    return response((dashboards.find((item) => item.id === id) ?? dashboards[0]) as T);
  }
  if (cleanPath.includes("/cards/") && method === "DELETE") return response(undefined as T);

  return response(undefined as T);
}
