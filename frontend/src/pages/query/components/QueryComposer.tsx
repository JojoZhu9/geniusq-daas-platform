import type { FormEvent } from "react";

type QueryComposerProps = {
  question: string;
  isPending: boolean;
  onQuestionChange: (value: string) => void;
  onSubmit: (event: FormEvent) => void;
};

export function QueryComposer({
  question,
  isPending,
  onQuestionChange,
  onSubmit
}: QueryComposerProps) {
  return (
    <form className="question-composer" onSubmit={onSubmit}>
      <textarea
        aria-label="问题"
        value={question}
        onChange={(event) => onQuestionChange(event.target.value)}
        placeholder="请输入想分析的问题"
        rows={2}
      />
      <div className="composer-footer">
        <span>Enter 发送 · 所有查询均为只读</span>
        <button className="send-button" type="submit" disabled={!question.trim() || isPending}>发送</button>
      </div>
    </form>
  );
}
