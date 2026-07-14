import type { AnalysisStep } from "../types";

export function ThinkingTimeline({ steps }: { steps: AnalysisStep[] }) {
  return (
    <ol className="thinking-timeline" aria-label="可审计执行步骤">
      {steps.map((step, index) => (
        <li key={step.key}>
          <span className="step-index">{index + 1}</span>
          <div>
            <strong>{step.title}</strong>
            <p>{step.detail}</p>
          </div>
          <span className={`step-status ${step.status}`}>{step.status === "completed" ? "已完成" : step.status}</span>
        </li>
      ))}
    </ol>
  );
}
