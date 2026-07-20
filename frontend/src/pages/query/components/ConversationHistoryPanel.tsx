import type { ConversationSummary } from "../../../types";

type ConversationHistoryPanelProps = {
  conversations: ConversationSummary[];
  conversationId: string;
  loadingConversationId: string;
  error: string;
  onRestore: (id: string) => void;
  onDelete: (id: string) => void;
  onClear: () => void;
  onRefresh: () => void;
};

export function ConversationHistoryPanel({
  conversations,
  conversationId,
  loadingConversationId,
  error,
  onRestore,
  onDelete,
  onClear,
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
          <div className="conversation-history-row" key={item.id}>
            <button
              type="button"
              className={item.id === conversationId ? "conversation-history-item active" : "conversation-history-item"}
              aria-label={`打开会话：${item.title}`}
              onClick={() => onRestore(item.id)}
              disabled={loadingConversationId === item.id}
            >
              <strong>{item.title}</strong>
              <span>{item.latest_question ?? "暂无问题"} · {item.analysis_count} 轮</span>
            </button>
            <button
              type="button"
              className="text-button danger-text-button"
              aria-label={`删除会话：${item.title}`}
              onClick={() => onDelete(item.id)}
              disabled={loadingConversationId === item.id}
            >
              删除
            </button>
          </div>
        ))}
      </div>
      <div className="conversation-history-actions">
        <button className="text-button" type="button" onClick={onRefresh}>刷新历史</button>
        {conversations.length > 0 && (
          <button className="text-button danger-text-button" type="button" onClick={onClear}>清空历史</button>
        )}
      </div>
    </div>
  );
}
