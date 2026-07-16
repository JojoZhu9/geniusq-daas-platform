import type { AnalysisStep } from "../types";

function statusText(status: AnalysisStep["status"]) {
  if (status === "completed") return "已完成";
  if (status === "running") return "运行中";
  if (status === "failed") return "失败";
  return "等待中";
}

export function ThinkingTimeline({ steps }: { steps: AnalysisStep[] }) {
  return (
    <ol className="thinking-timeline" aria-label="可审计执行步骤">
      {steps.map((step, index) => (
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
            {step.error && (
              <div className="tool-trace-grid">
                <section className="tool-error">
                  <span>失败原因</span>
                  <pre>{step.error}</pre>
                </section>
              </div>
            )}
          </div>
          <span className={`step-status ${step.status}`}>{statusText(step.status)}</span>
        </li>
      ))}
    </ol>
  );
}
