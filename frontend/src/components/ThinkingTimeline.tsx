import type { AnalysisStep } from "../types";

function statusText(status: AnalysisStep["status"]) {
  if (status === "completed") return "已完成";
  if (status === "running") return "运行中";
  if (status === "failed") return "失败";
  return "等待中";
}

function formatTraceValue(value: Record<string, unknown>) {
  return JSON.stringify(value, null, 2);
}

function SummaryList({ items }: { items: string[] }) {
  return (
    <ul>
      {items.map((item) => (
        <li key={item}>{item}</li>
      ))}
    </ul>
  );
}

export function ThinkingTimeline({ steps }: { steps: AnalysisStep[] }) {
  return (
    <ol className="thinking-timeline" aria-label="可审计执行步骤">
      {steps.map((step, index) => {
        const hasFriendlyTrace = Boolean(
          step.tool_label || step.input_summary?.length || step.output_summary?.length
        );
        const showRawInput = !step.input_summary?.length && step.input;
        const showRawOutput = !step.output_summary?.length && step.output;
        return (
          <li className={`step-item ${step.status}`} key={step.key}>
            <span className="step-index">{step.status === "completed" ? "✓" : index + 1}</span>
            <div>
              <div className="step-title-row">
                <strong>{step.title}</strong>
                {(step.tool_label || step.tool) && (
                  <span className="tool-pill">
                    <b>调用工具</b>
                    {step.tool_label || step.tool}
                  </span>
                )}
              </div>
              <p>{step.detail}</p>
              {(hasFriendlyTrace || showRawInput || showRawOutput || step.error) && (
                <div className="tool-trace-grid">
                  {(step.input_summary?.length || showRawInput) && (
                    <section>
                      <span>输入摘要</span>
                      {step.input_summary?.length ? (
                        <SummaryList items={step.input_summary} />
                      ) : (
                        <pre>{formatTraceValue(step.input ?? {})}</pre>
                      )}
                    </section>
                  )}
                  {(step.output_summary?.length || showRawOutput) && (
                    <section>
                      <span>输出摘要</span>
                      {step.output_summary?.length ? (
                        <SummaryList items={step.output_summary} />
                      ) : (
                        <pre>{formatTraceValue(step.output ?? {})}</pre>
                      )}
                    </section>
                  )}
                  {step.error && (
                    <section className="tool-error">
                      <span>失败原因</span>
                      <pre>{step.error}</pre>
                    </section>
                  )}
                </div>
              )}
            </div>
            <span className={`step-status ${step.status}`}>{statusText(step.status)}</span>
          </li>
        );
      })}
    </ol>
  );
}
