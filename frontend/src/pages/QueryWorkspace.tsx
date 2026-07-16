import { FormEvent, useEffect, useMemo, useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { api, ApiClientError } from "../api/client";
import { AnalysisChart } from "../components/AnalysisChart";
import { DataSourcePanel } from "../components/DataSourcePanel";
import { RequirementBadge } from "../components/RequirementBadge";
import { ThinkingTimeline } from "../components/ThinkingTimeline";
import type { AnalysisResponse, ChartSpec, Dashboard } from "../types";

type Exchange = { question: string; response: AnalysisResponse };

type ModelSettings = {
  llm_mode: string;
  deepseek_base_url: string;
  deepseek_model: string;
  deepseek_api_key_configured: boolean;
};

const LIVE_STEPS = [
  { key: "understand_question", title: "理解用户问题", detail: "正在识别用户意图、时间范围、区域和指标…" },
  { key: "merge_context", title: "合并会话上下文", detail: "正在读取历史对话，合并上一轮年份、区域和指标…" },
  { key: "retrieve_knowledge", title: "检索问数知识", detail: "正在从知识库中检索表结构、业务口径和 SQL 示例…" },
  { key: "select_tables_fields", title: "选择数据表与字段", detail: "正在匹配可用数据表和字段，并确认查询边界…" },
  { key: "deepseek_text_to_sql", title: "调用 DeepSeek 生成 SQL", detail: "正在把问题、上下文和知识片段发送给模型生成候选 SQL…" },
  { key: "validate_sql", title: "校验只读 SQL", detail: "正在检查 SQL 是否只读、单语句、且只访问授权表…" },
  { key: "execute_and_visualize", title: "执行查询并生成图表建议", detail: "正在查询本地 SQLite，并准备图表和洞察结果…" },
] as const;

function liveThinkingSteps(activeIndex: number) {
  return LIVE_STEPS.map((step, index) => ({
    ...step,
    status: index < activeIndex ? "completed" : index === activeIndex ? "running" : "pending"
  } as const));
}

function nextDashboardCardLayout(cards: Dashboard["cards"]) {
  const width = 6;
  const height = 4;
  const overlaps = (x: number, y: number) => cards.some((card) => (
    x < card.layout.x + card.layout.w
    && x + width > card.layout.x
    && y < card.layout.y + card.layout.h
    && y + height > card.layout.y
  ));

  for (let row = 0; row <= cards.length; row += 1) {
    const y = row * height;
    for (const x of [0, 6]) {
      if (!overlaps(x, y)) return { x, y, w: width, h: height };
    }
  }
  return { x: 0, y: cards.length * height, w: width, h: height };
}

export function QueryWorkspace() {
  const [conversationId, setConversationId] = useState("");
  const [question, setQuestion] = useState("");
  const [history, setHistory] = useState<Exchange[]>([]);
  const [expanded, setExpanded] = useState(false);
  const [thinkingCollapsed, setThinkingCollapsed] = useState(false);
  const [pendingQuestion, setPendingQuestion] = useState("");
  const [liveStepIndex, setLiveStepIndex] = useState(0);
  const [modelSettings, setModelSettings] = useState<ModelSettings | null>(null);
  const [showModelSettings, setShowModelSettings] = useState(false);
  const [apiKeyInput, setApiKeyInput] = useState("");
  const [modelInput, setModelInput] = useState("deepseek-v4-flash");
  const [notice, setNotice] = useState("");
  const [initError, setInitError] = useState("");
  const [chartTypes, setChartTypes] = useState<Record<string, ChartSpec["type"]>>({});
  const latest = history.at(-1)?.response;
  const liveSteps = useMemo(() => liveThinkingSteps(liveStepIndex), [liveStepIndex]);

  useEffect(() => {
    api.post<{ id: string }>("/api/conversations")
      .then((value) => setConversationId(value.id))
      .catch(() => setInitError("无法初始化本地会话，请确认后端服务已启动。"));
    api.get<ModelSettings>("/api/model-settings")
      .then((settings) => {
        setModelSettings(settings);
        setModelInput(settings.deepseek_model || "deepseek-v4-flash");
      })
      .catch(() => setModelSettings(null));
  }, []);

  const askMutation = useMutation({
    mutationFn: (nextQuestion: string) => api.post<AnalysisResponse>("/api/chat", {
      conversation_id: conversationId,
      question: nextQuestion
    }),
    onSuccess: (response, askedQuestion) => {
      setHistory((items) => [...items, { question: askedQuestion, response }]);
      setExpanded(true);
      setThinkingCollapsed(false);
      setPendingQuestion("");
      setNotice("");
    }
  });

  useEffect(() => {
    if (!askMutation.isPending) {
      setLiveStepIndex(0);
      return;
    }
    const timer = window.setInterval(() => {
      setLiveStepIndex((index) => Math.min(index + 1, LIVE_STEPS.length - 1));
    }, 650);
    return () => window.clearInterval(timer);
  }, [askMutation.isPending]);

  function ask(nextQuestion: string) {
    const trimmed = nextQuestion.trim();
    if (!trimmed || !conversationId || askMutation.isPending) return;
    setQuestion("");
    setPendingQuestion(trimmed);
    setThinkingCollapsed(false);
    setLiveStepIndex(0);
    askMutation.mutate(trimmed);
  }

  function submit(event: FormEvent) {
    event.preventDefault();
    ask(question);
  }

  async function resetConversation() {
    const next = await api.post<{ id: string }>("/api/conversations");
    setConversationId(next.id);
    setHistory([]);
    setChartTypes({});
    setNotice("已新建会话");
  }

  async function saveToDashboard() {
    if (!latest?.chart) return;
    const dashboards = await api.get<Dashboard[]>("/api/dashboards");
    const dashboard = dashboards[0] ?? await api.post<Dashboard>("/api/dashboards", { name: "房价分析看板" });
    await api.post(`/api/dashboards/${dashboard.id}/cards`, {
      title: latest.chart.title,
      analysis_id: latest.analysis_id,
      chart: {
        ...latest.chart,
        type: chartTypes[latest.analysis_id] ?? latest.chart.type
      },
      layout: nextDashboardCardLayout(dashboard.cards)
    });
    setNotice(`已加入“${dashboard.name}”`);
  }

  async function saveFeedback(analysisId: string, saveAsExample = false) {
    await api.post(`/api/analysis/${analysisId}/feedback`, {
      rating: "correct",
      comment: saveAsExample ? "SQL 正确，可作为示例" : "SQL 正确",
      save_as_example: saveAsExample
    });
    setNotice(saveAsExample ? "反馈已保存，并已收藏为 SQL 示例" : "反馈已保存");
  }

  async function saveModelSettings(event: FormEvent) {
    event.preventDefault();
    const settings = await api.post<ModelSettings>("/api/model-settings/deepseek", {
      api_key: apiKeyInput.trim(),
      base_url: modelSettings?.deepseek_base_url || "https://api.deepseek.com",
      model: modelInput.trim() || "deepseek-v4-flash"
    });
    setModelSettings(settings);
    setApiKeyInput("");
    setShowModelSettings(false);
    setNotice("DeepSeek API Key 已配置，本次本地后端运行生效");
  }

  const error = askMutation.error instanceof ApiClientError
    ? `${askMutation.error.message}；${askMutation.error.payload.action}`
    : askMutation.error ? "分析失败，请稍后重试。" : "";

  if (!conversationId && !initError) {
    return <section className="page-section"><div className="panel page-loading">正在初始化本地问数会话…</div></section>;
  }

  return (
    <section className="page-section query-page">
      <div className="page-heading">
        <div><small>智慧问数 / 智能问数工作台</small><h1>用自然语言探索可信数据</h1></div>
        <div className="heading-actions"><span className="offline-chip"><i />离线规则引擎</span><button className="secondary-button" type="button" onClick={resetConversation}>＋ 新建会话</button></div>
      </div>
      <div className="model-config-strip panel">
        <span className={`offline-chip ${modelSettings?.llm_mode === "deepseek" ? "online" : ""}`}>
          <i />{modelSettings?.llm_mode === "deepseek" ? "DeepSeek 已启用" : "离线规则引擎"}
        </span>
        <button className="secondary-button" type="button" onClick={() => setShowModelSettings(true)}>配置 DeepSeek API</button>
        <small>{modelSettings?.deepseek_api_key_configured ? "API Key 已配置，可覆盖更新" : "未配置 API Key 时使用离线演示规则"}</small>
      </div>
      {showModelSettings && (
        <div className="model-settings-panel panel" role="dialog" aria-label="DeepSeek API 配置">
          <div>
            <strong>DeepSeek API 配置</strong>
            <p>给演示平台填入 API Key 后，本次本地后端会切换到真实 DeepSeek Text-to-SQL。Key 不会显示在页面，也不会写入仓库。</p>
          </div>
          <form onSubmit={saveModelSettings}>
            <label>
              API Key
              <input
                aria-label="DeepSeek API Key"
                type="password"
                value={apiKeyInput}
                onChange={(event) => setApiKeyInput(event.target.value)}
                placeholder={modelSettings?.deepseek_api_key_configured ? "已配置，可输入新 Key 覆盖" : "sk-..."}
                required={!modelSettings?.deepseek_api_key_configured}
              />
            </label>
            <label>
              模型
              <input
                aria-label="DeepSeek 模型"
                value={modelInput}
                onChange={(event) => setModelInput(event.target.value)}
                placeholder="deepseek-v4-flash"
              />
            </label>
            <div>
              <button className="secondary-button" type="button" onClick={() => setShowModelSettings(false)}>取消</button>
              <button className="primary-button" type="submit" disabled={!apiKeyInput.trim()}>保存配置</button>
            </div>
          </form>
        </div>
      )}
      <div className="query-layout">
        <main className="query-main panel">
          <div className="query-welcome">
            <div className="sparkle">✦</div>
            <div><h2>你好，我是 GeniusQ 智能问数助手</h2><p>我会展示可审计的业务步骤、数据来源、只读 SQL、图表和结论。</p></div>
          </div>
          <div className="quick-prompts">
            {["分析2025年各区平均房价", "只看海淀区", "2025年房价上涨是否与人口和通勤相关"].map((item) => (
              <button type="button" key={item} onClick={() => ask(item)}>{item}</button>
            ))}
          </div>

          <div className="conversation-stream" aria-live="polite">
            {history.map((exchange) => (
              <article className="exchange" key={exchange.response.analysis_id}>
                <div className="user-message"><span>你</span><p>{exchange.question}</p></div>
                <div className="assistant-message">
                  {exchange.response.status === "needs_clarification" ? (
                    <div className="clarification-card">
                      <div className="result-kicker">需要补充条件</div>
                      <h3>为了得到准确结果，请选择一个分析范围</h3>
                      <p>{exchange.response.insights[0]}</p>
                      <div className="suggestion-list">
                        {exchange.response.suggestions.map((suggestion) => <button type="button" key={suggestion} onClick={() => ask(suggestion)}>{suggestion}<span>→</span></button>)}
                      </div>
                      <RequirementBadge id="2.2" />
                    </div>
                  ) : exchange.response.analysis_id === latest?.analysis_id ? (
                    <div className="completed-result">
                      <div className="result-topline">
                        <div><span className="success-icon">✓</span><strong>分析完成</strong><small>任务 {exchange.response.analysis_id.slice(0, 8)}</small></div>
                        <button className="text-button" type="button" onClick={() => setExpanded((value) => !value)}>{expanded ? "收起思考过程" : "查看思考过程"}</button>
                      </div>
                      {expanded && <ThinkingTimeline steps={exchange.response.steps} />}
                      {exchange.response.metadata.mode === "deepseek" && (
                        <section className="model-evidence-card" aria-label="模型生成依据">
                          <div>
                            <small>当前模式</small>
                            <strong>DeepSeek Text-to-SQL</strong>
                            <span>{exchange.response.metadata.model ?? "deepseek-v4-flash"}</span>
                          </div>
                          <div>
                            <small>SQL 校验</small>
                            <strong>
                              SQL 校验：{exchange.response.metadata.sql_validation_status === "passed" ? "通过" : "待校验"}
                            </strong>
                            {typeof exchange.response.metadata.confidence === "number" && (
                              <span>模型置信度：{Math.round(exchange.response.metadata.confidence * 100)}%</span>
                            )}
                          </div>
                          {exchange.response.metadata.model_reasoning && (
                            <p>{String(exchange.response.metadata.model_reasoning)}</p>
                          )}
                          {!!exchange.response.metadata.used_knowledge?.length && (
                            <div className="knowledge-chips" aria-label="使用知识">
                              {exchange.response.metadata.used_knowledge.map((item) => (
                                <span key={item.id}>
                                  {item.title}
                                  <small>{item.scope === "private" ? "私有" : "公开"} · {item.kind}</small>
                                </span>
                              ))}
                            </div>
                          )}
                          {!!exchange.response.metadata.used_metrics?.length && (
                            <div className="knowledge-chips semantic-chips" aria-label="命中指标口径">
                              {exchange.response.metadata.used_metrics.map((item) => (
                                <span key={item.id}>
                                  {item.name}
                                  <small>{item.formula}</small>
                                </span>
                              ))}
                            </div>
                          )}
                        </section>
                      )}
                      <div className="insight-grid">
                        {exchange.response.insights.slice(0, 3).map((insight, index) => (
                          <article key={insight}><span>{index === 0 ? "MAX" : index === 1 ? "TREND" : "NOTE"}</span><p>{insight}</p></article>
                        ))}
                      </div>
                      {exchange.response.chart && (
                        <AnalysisChart
                          chart={{
                            ...exchange.response.chart,
                            type: chartTypes[exchange.response.analysis_id] ?? exchange.response.chart.type
                          }}
                          datasets={exchange.response.datasets}
                          onTypeChange={(type) => setChartTypes((items) => ({
                            ...items,
                            [exchange.response.analysis_id]: type
                          }))}
                        />
                      )}
                      <div className="result-actions">
                        <button type="button" className="primary-button" onClick={saveToDashboard}><span aria-hidden="true">＋ </span>加入仪表盘</button>
                        <button type="button" className="secondary-button" onClick={() => saveFeedback(exchange.response.analysis_id)}>SQL 正确</button>
                        <button type="button" className="secondary-button" onClick={() => saveFeedback(exchange.response.analysis_id, true)}>收藏为示例</button>
                        <span className="result-meta">耗时 &lt; 1 秒 · {exchange.response.datasets.reduce((sum, dataset) => sum + dataset.rows.length, 0)} 条记录</span>
                      </div>
                      <div className="follow-ups"><strong>继续追问</strong>{exchange.response.follow_ups.map((item) => <button type="button" key={item} onClick={() => ask(item)}>{item}</button>)}</div>
                      <div className="badge-row">{exchange.response.requirement_ids.map((id) => <RequirementBadge id={id} key={id} />)}</div>
                    </div>
                  ) : (
                    <div className="history-summary"><strong>分析已完成</strong><p>{exchange.response.insights[0]}</p></div>
                  )}
                </div>
              </article>
            ))}
            {askMutation.isPending && (
              <article className="exchange live-exchange">
                <div className="user-message"><span>你</span><p>{pendingQuestion}</p></div>
                <div className="assistant-message">
                  <div className="completed-result live-thinking">
                    <div className="result-topline">
                      <div><span className="spinner small-spinner" /><strong>正在分析</strong><small>DeepSeek Text-to-SQL</small></div>
                      <button className="text-button" type="button" onClick={() => setThinkingCollapsed((value) => !value)}>{thinkingCollapsed ? "展开思考过程" : "折叠思考过程"}</button>
                    </div>
                    {!thinkingCollapsed && <ThinkingTimeline steps={liveSteps} />}
                  </div>
                </div>
              </article>
            )}
          </div>

          {(notice || error || initError) && <div className={error || initError ? "inline-alert error" : "inline-alert"}>{error || initError || notice}</div>}
          <form className="question-composer" onSubmit={submit}>
            <textarea aria-label="问题" value={question} onChange={(event) => setQuestion(event.target.value)} placeholder="请输入想分析的问题" rows={2} />
            <div className="composer-footer"><span>Enter 发送 · 所有查询均为只读</span><button className="send-button" type="submit" disabled={!question.trim() || askMutation.isPending}>发送</button></div>
          </form>
        </main>
        <DataSourcePanel datasets={latest?.datasets ?? []} queries={latest?.queries ?? []} />
      </div>
    </section>
  );
}
