export type QueryContext = {
  year_from: number | null;
  year_to: number | null;
  district: string | null;
  metric: string | null;
};

export type AnalysisStep = {
  key: string;
  title: string;
  detail: string;
  status: "pending" | "running" | "completed" | "failed";
};

export type PlannedQuery = { source: string; sql: string };
export type ChartSpec = {
  type: "line" | "bar" | "pie" | "table";
  x_field: string;
  y_fields: string[];
  title: string;
};
export type Dataset = {
  source: string;
  table: string;
  tables: string[];
  updated_at: string;
  confidence: number;
  fields: string[];
  rows: Record<string, string | number>[];
};
export type AnalysisResponse = {
  status: "needs_clarification" | "completed";
  analysis_id: string;
  conversation_id: string;
  context: QueryContext;
  suggestions: string[];
  steps: AnalysisStep[];
  queries: PlannedQuery[];
  datasets: Dataset[];
  chart: ChartSpec | null;
  insights: string[];
  follow_ups: string[];
  requirement_ids: string[];
  metadata: {
    mode?: string;
    model?: string;
    model_reasoning?: string;
    confidence?: number | null;
    sql_validation_status?: string;
    used_knowledge?: {
      id: string;
      title: string;
      kind: string;
      scope: string;
      linked_tables: string[];
      score: number;
    }[];
    [key: string]: unknown;
  };
  created_at: string;
};

export type KnowledgeItem = {
  id: string;
  name: string;
  kind: "text" | "sql" | "rule";
  scope: "private" | "public";
  library: string;
  content: string;
  linked_tables: string[];
  tags: string[];
  schema_status: string;
  overrides_id: string | null;
  conflict: { message: string; overrides_id: string } | null;
  requirement_ids: string[];
};

export type DashboardCard = {
  id: string;
  title: string;
  analysis_id: string;
  chart: ChartSpec;
  datasets: Dataset[];
  layout: { x: number; y: number; w: number; h: number };
};
export type Dashboard = {
  id: string;
  name: string;
  share_id: string;
  share_url: string;
  cards: DashboardCard[];
  requirement_ids: string[];
};

export type Requirement = {
  id: string;
  original: string;
  title: string;
  solution: string;
  page: string;
  acceptance: string;
  module: string;
  priority: string;
  status: string;
};
