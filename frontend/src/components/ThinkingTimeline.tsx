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

export function ThinkingTimeline({ steps }: { steps: AnalysisStep[] }) {
  return (
    <ol className="thinking-timeline" aria-label="可审计执行步骤">
      {steps.map((step, index) => (
        <li className={`step-item ${step.status}`} key={step.key}>
          <span className="step-index">{step.status === "completed" ? "✓" : index + 1}</span>
          <div>
            <div className="step-title-row">
              <strong>{step.title}</strong>
              {step.tool && <code>{step.tool}</code>}
            </div>
            <p>{step.detail}</p>
            {(step.input || step.output || step.error) && (
              <div className="tool-trace-grid">
                {step.input && (
                  <section>
                    <span>Input</span>
                    <pre>{formatTraceValue(step.input)}</pre>
                  </section>
                )}
                {step.output && (
                  <section>
                    <span>Output</span>
                    <pre>{formatTraceValue(step.output)}</pre>
                  </section>
                )}
                {step.error && (
                  <section className="tool-error">
                    <span>Error</span>
                    <pre>{step.error}</pre>
                  </section>
                )}
              </div>
            )}
          </div>
          <span className={`step-status ${step.status}`}>{statusText(step.status)}</span>
        </li>
      ))}
    </ol>
  );
}
