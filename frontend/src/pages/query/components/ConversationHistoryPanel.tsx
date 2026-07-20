import type { ConversationSummary } from "../../../types";

type ConversationHistoryPanelProps = {
  conversations: ConversationSummary[];
  conversationId: string;
  loadingConversationId: string;
  error: string;
  onRestore: (id: string) => void;
  onRefresh: () => void;
};

export function ConversationHistoryPanel({
  conversations,
  conversationId,
  loadingConversationId,
  error,
  onRestore,
  onRefresh,
}: ConversationHistoryPanelProps) {
  return (
    <div className="conversation-history panel" aria-label="历史会话">
      <div>
        <small>历史会话</small>
        <strong>保存的问数记录</strong>
      </div>
      <div className="conversation-history-list">
        {error && <span className="conversation-history-empty">{error}</span>}
        {!error && conversations.length === 0 && (
          <span className="conversation-history-empty">暂无历史会话，完成一次问数后会自动保存到这里</span>
        )}
        {conversations.slice(0, 6).map((item) => (
          <button
            type="button"
            key={item.id}
            className={item.id === conversationId ? "conversation-history-item active" : "conversation-history-item"}
            onClick={() => onRestore(item.id)}
            disabled={loadingConversationId === item.id}
          >
            <strong>{item.title}</strong>
            <span>{item.latest_question ?? "暂无问题"} · {item.analysis_count} 轮</span>
          </button>
        ))}
      </div>
      <button className="text-button" type="button" onClick={onRefresh}>刷新历史</button>
    </div>
  );
}

