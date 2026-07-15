import { FormEvent, useEffect, useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { api, ApiClientError } from "../api/client";
import { AnalysisChart } from "../components/AnalysisChart";
import { DataSourcePanel } from "../components/DataSourcePanel";
import { RequirementBadge } from "../components/RequirementBadge";
import { ThinkingTimeline } from "../components/ThinkingTimeline";
import type { AnalysisResponse, ChartSpec, Dashboard } from "../types";

type Exchange = { question: string; response: AnalysisResponse };

export function QueryWorkspace() {
  const [conversationId, setConversationId] = useState("");
  const [question, setQuestion] = useState("");
  const [history, setHistory] = useState<Exchange[]>([]);
  const [expanded, setExpanded] = useState(false);
  const [notice, setNotice] = useState("");
  const [initError, setInitError] = useState("");
  const [chartTypes, setChartTypes] = useState<Record<string, ChartSpec["type"]>>({});
  const latest = history.at(-1)?.response;

  useEffect(() => {
    api.post<{ id: string }>("/api/conversations")
      .then((value) => setConversationId(value.id))
      .catch(() => setInitError("无法初始化本地会话，请确认后端服务已启动。"));
  }, []);

  const askMutation = useMutation({
    mutationFn: (nextQuestion: string) => api.post<AnalysisResponse>("/api/chat", {
      conversation_id: conversationId,
      question: nextQuestion
    }),
    onSuccess: (response, askedQuestion) => {
      setHistory((items) => [...items, { question: askedQuestion, response }]);
      setExpanded(false);
      setNotice("");
    }
  });

  function ask(nextQuestion: string) {
    const trimmed = nextQuestion.trim();
    if (!trimmed || !conversationId || askMutation.isPending) return;
    setQuestion("");
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
      layout: { x: 0, y: dashboard.cards.length * 4, w: 6, h: 4 }
    });
    setNotice(`已加入“${dashboard.name}”`);
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
      <div className="query-layout">
        <main className="query-main panel">
          <div className="query-welcome">
            <div className="sparkle">✦</div>
            <div><h2>你好，我是极智智能问数助手</h2><p>我会展示可审计的业务步骤、数据来源、只读 SQL、图表和结论。</p></div>
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
            {askMutation.isPending && <div className="analysis-progress"><span className="spinner" /><div><strong>正在生成可审计分析计划</strong><p>识别意图 → 选择数据 → 校验 SQL → 汇总结果</p></div></div>}
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
