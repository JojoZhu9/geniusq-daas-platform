export const LIVE_STEPS = [
  { key: "understand_question", title: "理解用户问题", detail: "正在识别用户意图、时间范围、区域和指标…" },
  { key: "merge_context", title: "合并会话上下文", detail: "正在读取历史对话，合并上一轮年份、区域和指标…" },
  { key: "retrieve_knowledge", title: "检索问数知识", detail: "正在从知识库中检索表结构、业务口径和 SQL 示例…" },
  { key: "select_tables_fields", title: "选择数据表与字段", detail: "正在匹配可用数据表和字段，并确认查询边界…" },
  { key: "deepseek_text_to_sql", title: "调用 DeepSeek 生成 SQL", detail: "正在把问题、上下文和知识片段发送给模型生成候选 SQL…" },
  { key: "validate_sql", title: "校验只读 SQL", detail: "正在检查 SQL 是否只读、单语句、且只访问授权表…" },
  { key: "execute_and_visualize", title: "执行查询并生成图表建议", detail: "正在查询本地 SQLite，并准备图表和洞察结果…" },
] as const;

const LIVE_STEP_TOOLS: Record<string, string> = {
  understand_question: "问题理解器",
  merge_context: "会话上下文管理器",
  retrieve_knowledge: "知识库检索工具",
  select_tables_fields: "数据表字段选择器",
  deepseek_text_to_sql: "DeepSeek SQL 生成工具",
  validate_sql: "只读 SQL 安全校验器",
  execute_and_visualize: "SQLite 查询与图表工具",
};

export function liveThinkingSteps(activeIndex: number) {
  return LIVE_STEPS.slice(0, Math.min(activeIndex + 1, LIVE_STEPS.length)).map((step, index) => ({
    ...step,
    tool_label: LIVE_STEP_TOOLS[step.key],
    status: index < activeIndex ? "completed" : "running"
  } as const));
}

