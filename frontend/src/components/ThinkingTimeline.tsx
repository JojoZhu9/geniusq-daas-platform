import type { AnalysisStep } from "../types";

export function ThinkingTimeline({ steps }: { steps: AnalysisStep[] }) {
  return (
    <ol className="thinking-timeline" aria-label="可审计执行步骤">
      {steps.map((step, index) => (
        <li className={`step-item ${step.status}`} key={step.key}>
          <span className="step-index">{step.status === "completed" ? "✓" : index + 1}</span>
          <div>
            <strong>{step.title}</strong>
            <p>{step.detail}</p>
          </div>
          <span className={`step-status ${step.status}`}>
            {step.status === "completed" ? "已完成" : step.status === "running" ? "运行中" : step.status}
          </span>
        </li>
      ))}
    </ol>
  );
}
