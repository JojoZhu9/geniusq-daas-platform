import { FormEvent, useEffect, useMemo, useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { useSearchParams } from "react-router-dom";
import { api, ApiClientError } from "../../api/client";
import { AnalysisChart } from "../../components/AnalysisChart";
import { DataSourcePanel } from "../../components/DataSourcePanel";
import { RequirementBadge } from "../../components/RequirementBadge";
import { ThinkingTimeline } from "../../components/ThinkingTimeline";
import { DEFAULT_DEEPSEEK_MODEL } from "../../config/modelDefaults";
import type { AnalysisResponse, ChartSpec, ConversationDetail, ConversationSummary } from "../../types";
import { ConversationHistoryPanel } from "./components/ConversationHistoryPanel";
import { ModelConfigStrip } from "./components/ModelConfigStrip";
import { QueryComposer } from "./components/QueryComposer";
import { useDashboardSave } from "./hooks/useDashboardSave";
import { useModelSettings } from "./hooks/useModelSettings";
import { LIVE_STEPS, liveThinkingSteps } from "./queryUtils";

type Exchange = { question: string; response: AnalysisResponse };

export function QueryWorkspace() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [conversationId, setConversationId] = useState("");
  const [question, setQuestion] = useState("");
  const [history, setHistory] = useState<Exchange[]>([]);
  const [expanded, setExpanded] = useState(false);
  const [thinkingCollapsed, setThinkingCollapsed] = useState(false);
  const [pendingQuestion, setPendingQuestion] = useState("");
  const [liveStepIndex, setLiveStepIndex] = useState(0);
  const [notice, setNotice] = useState("");
  const [initError, setInitError] = useState("");
  const [chartTypes, setChartTypes] = useState<Record<string, ChartSpec["type"]>>({});
  const [conversations, setConversations] = useState<ConversationSummary[]>([]);
  const [loadingConversationId, setLoadingConversationId] = useState("");
  const [conversationHistoryError, setConversationHistoryError] = useState("");
  const latest = history.at(-1)?.response;
  const liveSteps = useMemo(() => liveThinkingSteps(liveStepIndex), [liveStepIndex]);
  const {
    modelSettings,
    showModelSettings,
    apiKeyInput,
    modelInput,
    setShowModelSettings,
    setApiKeyInput,
    setModelInput,
    saveModelSettings
  } = useModelSettings(setNotice);
  const saveToDashboard = useDashboardSave(latest, chartTypes, setNotice);

  async function loadConversations() {
    try {
      const items = await api.get<ConversationSummary[]>("/api/conversations");
      setConversations(Array.isArray(items) ? items.filter((item) => item.analysis_count > 0) : []);
      setConversationHistoryError("");
    } catch {
      setConversations([]);
      setConversationHistoryError("历史接口暂不可用，请重启后端服务后刷新");
    }
  }

  useEffect(() => {
    api.post<{ id: string }>("/api/conversations")
      .then((value) => setConversationId(value.id))
      .catch(() => setInitError("无法初始化本地会话，请确认后端服务已启动。"));
    loadConversations();
  }, []);

  useEffect(() => {
    const suggestedQuestion = searchParams.get("question");
    if (!suggestedQuestion) return;
    setQuestion(suggestedQuestion);
    setSearchParams({}, { replace: true });
  }, [searchParams, setSearchParams]);

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
      loadConversations();
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

  async function deleteConversation(id: string) {
    if (!window.confirm("确认删除该历史会话吗？")) return;
    await api.delete(`/api/conversations/${id}`);
    setConversations((items) => items.filter((item) => item.id !== id));
    if (id === conversationId) {
      const next = await api.post<{ id: string }>("/api/conversations");
      setConversationId(next.id);
      setHistory([]);
      setChartTypes({});
      setExpanded(false);
      setThinkingCollapsed(false);
    }
    setNotice("已删除历史会话");
    await loadConversations();
  }

  async function clearConversationHistory() {
    if (!window.confirm("确认清空全部历史会话吗？此操作不可恢复。")) return;
    await api.delete("/api/conversations");
    const next = await api.post<{ id: string }>("/api/conversations");
    setConversationId(next.id);
    setHistory([]);
    setChartTypes({});
    setExpanded(false);
    setThinkingCollapsed(false);
    setConversations([]);
    setNotice("已清空历史会话");
  }

  async function restoreConversation(id: string) {
    setLoadingConversationId(id);
    try {
      const detail = await api.get<ConversationDetail>(`/api/conversations/${id}`);
      setConversationId(detail.id);
      setHistory(detail.exchanges.map((exchange) => ({
        question: exchange.question,
        response: exchange.response
      })));
      setChartTypes({});
      setExpanded(false);
      setThinkingCollapsed(false);
      setNotice(`已恢复“${detail.title}”`);
    } finally {
      setLoadingConversationId("");
    }
  }

  async function saveFeedback(analysisId: string, saveAsExample = false) {
    await api.post(`/api/analysis/${analysisId}/feedback`, {
      rating: "correct",
      comment: saveAsExample ? "SQL 正确，可作为示例" : "SQL 正确",
      save_as_example: saveAsExample
    });
    setNotice(saveAsExample ? "反馈已保存，并已收藏为 SQL 示例" : "反馈已保存");
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
      <ModelConfigStrip
        modelSettings={modelSettings}
        showModelSettings={showModelSettings}
        apiKeyInput={apiKeyInput}
        modelInput={modelInput}
        onOpen={() => setShowModelSettings(true)}
        onCancel={() => setShowModelSettings(false)}
        onApiKeyChange={setApiKeyInput}
        onModelChange={setModelInput}
        onSave={saveModelSettings}
      />
      <ConversationHistoryPanel
        conversations={conversations}
        conversationId={conversationId}
        loadingConversationId={loadingConversationId}
        error={conversationHistoryError}
        onRestore={restoreConversation}
        onDelete={deleteConversation}
        onClear={clearConversationHistory}
        onRefresh={loadConversations}
      />
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
                            <span>{exchange.response.metadata.model ?? DEFAULT_DEEPSEEK_MODEL}</span>
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
          <QueryComposer
            question={question}
            isPending={askMutation.isPending}
            onQuestionChange={setQuestion}
            onSubmit={submit}
          />
        </main>
        <DataSourcePanel datasets={latest?.datasets ?? []} queries={latest?.queries ?? []} />
      </div>
    </section>
  );
}
