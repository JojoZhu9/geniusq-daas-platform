import { FormEvent, useEffect, useMemo, useState } from "react";
import { api, ApiClientError, type ApiErrorPayload } from "../api/client";
import { RequirementBadge } from "../components/RequirementBadge";
import type { KnowledgeItem } from "../types";

type SyncLog = { id: string; mode: string; status: string; message: string; created_at: string };
type DeletePreview = ApiErrorPayload & {
  affected_knowledge_count: number;
  affected_knowledge: { id: string; name: string }[];
};

export function KnowledgeWorkspace() {
  const [items, setItems] = useState<KnowledgeItem[]>([]);
  const [selectedId, setSelectedId] = useState("");
  const [logs, setLogs] = useState<SyncLog[]>([]);
  const [query, setQuery] = useState("");
  const [kind, setKind] = useState("");
  const [scope, setScope] = useState("");
  const [tag, setTag] = useState("");
  const [notice, setNotice] = useState("");
  const [deletePreview, setDeletePreview] = useState<DeletePreview | null>(null);
  const [showCreate, setShowCreate] = useState(false);
  const [newName, setNewName] = useState("");
  const [newContent, setNewContent] = useState("");
  const [newKind, setNewKind] = useState("text");

  async function load() {
    const [knowledge, syncLogs] = await Promise.all([
      api.get<KnowledgeItem[]>("/api/knowledge"),
      api.get<SyncLog[]>("/api/sync/logs")
    ]);
    setItems(knowledge);
    setLogs(syncLogs);
    setSelectedId((current) => current || knowledge[0]?.id || "");
  }

  useEffect(() => { void load(); }, []);

  const visibleItems = useMemo(() => items.filter((item) => {
    const search = `${item.name} ${item.content}`.toLowerCase();
    return (!query || search.includes(query.toLowerCase()))
      && (!kind || item.kind === kind)
      && (!scope || item.scope === scope)
      && (!tag || item.tags.includes(tag));
  }), [items, query, kind, scope, tag]);
  const selected = items.find((item) => item.id === selectedId) ?? visibleItems[0];
  const tags = [...new Set(items.flatMap((item) => item.tags))];

  async function sync(mode: "manual" | "scheduled_demo") {
    const result = await api.post<{ message: string }>("/api/sync", { mode });
    setNotice(result.message);
  }

  async function previewTableDelete() {
    try {
      await api.delete("/api/data-tables/house_price_monthly");
    } catch (error) {
      if (error instanceof ApiClientError && error.status === 409) {
        setDeletePreview(error.payload as DeletePreview);
      } else {
        throw error;
      }
    }
  }

  async function confirmTableDelete() {
    const result = await api.delete<{ linked_items_removed: number }>("/api/data-tables/house_price_monthly?confirm=true");
    setDeletePreview(null);
    setNotice(`删除联动完成，已移除 ${result.linked_items_removed} 条关联知识`);
    await load();
  }

  async function createKnowledge(event: FormEvent) {
    event.preventDefault();
    await api.post("/api/knowledge", {
      name: newName,
      kind: newKind,
      scope: "private",
      library: "个人知识库",
      content: newContent,
      linked_tables: [],
      tags: ["演示新增"]
    });
    setShowCreate(false);
    setNewName("");
    setNewContent("");
    setNotice("知识条目已创建并完成指纹查重");
    await load();
  }

  return (
    <section className="page-section knowledge-page">
      <div className="page-heading">
        <div><small>知识库管理 / 条目与数据表</small><h1>知识资产与数据血缘</h1></div>
        <div className="heading-actions">
          <button className="secondary-button" type="button" onClick={() => sync("scheduled_demo")}>模拟定时同步</button>
          <button className="secondary-button" type="button" onClick={() => sync("manual")}>手动同步</button>
          <button className="primary-button" type="button" onClick={() => setShowCreate((value) => !value)}>＋ 新增知识</button>
        </div>
      </div>
      {notice && <div className="inline-alert">{notice}</div>}
      {showCreate && (
        <form className="panel create-knowledge" onSubmit={createKnowledge}>
          <strong>新增私有知识</strong>
          <input aria-label="知识名称" placeholder="知识名称" value={newName} onChange={(event) => setNewName(event.target.value)} required />
          <select aria-label="知识类型" value={newKind} onChange={(event) => setNewKind(event.target.value)}><option value="text">文本</option><option value="sql">SQL</option><option value="rule">规则</option></select>
          <input aria-label="知识内容" placeholder="知识内容或只读 SQL" value={newContent} onChange={(event) => setNewContent(event.target.value)} required />
          <button className="primary-button" type="submit">保存并查重</button>
        </form>
      )}
      <div className="knowledge-toolbar panel">
        <input aria-label="检索知识" placeholder="检索名称或内容" value={query} onChange={(event) => setQuery(event.target.value)} />
        <select aria-label="类型" value={kind} onChange={(event) => setKind(event.target.value)}><option value="">全部类型</option><option value="text">文本</option><option value="sql">SQL</option><option value="rule">规则</option></select>
        <select aria-label="范围" value={scope} onChange={(event) => setScope(event.target.value)}><option value="">全部范围</option><option value="private">私有</option><option value="public">公开</option></select>
        <select aria-label="标签" value={tag} onChange={(event) => setTag(event.target.value)}><option value="">全部标签</option>{tags.map((item) => <option value={item} key={item}>{item}</option>)}</select>
        <span>{visibleItems.length} 条知识</span>
      </div>
      <div className="knowledge-layout">
        <section className="panel knowledge-list-panel">
          <div className="panel-header"><div><small>知识条目</small><h2>个人与公共知识库</h2></div></div>
          <div className="knowledge-list">
            {visibleItems.map((item) => (
              <button type="button" aria-label={`${item.name}，${item.scope === "private" ? "私有" : "公开"}`} className={selected?.id === item.id ? "knowledge-row active" : "knowledge-row"} key={item.id} onClick={() => setSelectedId(item.id)}>
                <span className={`kind-icon ${item.kind}`}>{item.kind === "sql" ? "SQL" : item.kind === "rule" ? "R" : "T"}</span>
                <span><strong>{item.name}</strong><small>{item.library} · {item.tags.join(" / ")}</small></span>
                <em>{item.scope === "private" ? "私有" : "公开"}</em>
              </button>
            ))}
          </div>
        </section>
        <aside className="panel knowledge-detail">
          <div className="panel-header"><div><small>条目详情</small><h2>{selected?.name ?? "请选择知识"}</h2></div></div>
          {selected && <div className="detail-body">
            <div className="detail-meta"><span>{selected.kind.toUpperCase()}</span><span>{selected.scope === "private" ? "私有知识" : "公开知识"}</span><span>{selected.schema_status === "valid" ? "结构有效" : "待调整"}</span></div>
            {selected.conflict && <div className="priority-banner"><strong>私有知识优先</strong><span>公开条目被覆盖</span><small>公开条目仍保留，可在问数检索时由当前私有条目覆盖。</small></div>}
            <h3>知识内容</h3>
            {selected.kind === "sql" ? <pre className="knowledge-sql">{selected.content}</pre> : <p className="knowledge-content">{selected.content}</p>}
            <h3>关联数据表</h3>
            <div className="linked-tables">{selected.linked_tables.map((table) => <button type="button" key={table}>{table}<span>双向关联</span></button>)}</div>
            <h3>标签</h3>
            <div className="tag-row">{selected.tags.map((item) => <span key={item}>{item}</span>)}</div>
            <div className="badge-row">{selected.requirement_ids.map((id) => <RequirementBadge id={id} key={id} />)}</div>
          </div>}
        </aside>
        <aside className="panel sync-panel">
          <div className="panel-header"><div><small>数据表同步</small><h2>同步与联动</h2></div></div>
          <div className="sync-body">
            <article><strong>house_price_monthly</strong><span className="healthy">已同步</span><small>4 个知识条目关联</small><button type="button" className="danger-link" onClick={previewTableDelete}>演示删除联动</button></article>
            <h3>最近同步</h3>
            {logs.length ? logs.slice(0, 4).map((log) => <div className="sync-log" key={log.id}><span>{log.mode === "manual" ? "手动" : "模拟定时"}</span><strong>{log.status}</strong></div>) : <p className="muted-copy">尚无同步日志，可点击上方按钮触发。</p>}
            <RequirementBadge id="3.3" />
          </div>
        </aside>
      </div>
      {deletePreview && <div className="modal-backdrop" role="presentation"><div className="confirm-dialog" role="dialog" aria-modal="true" aria-label="确认删除数据表"><h2>确认删除数据表？</h2><p>将联动移除 {deletePreview.affected_knowledge_count} 条关联知识：</p><ul>{deletePreview.affected_knowledge.map((item) => <li key={item.id}>{item.name}</li>)}</ul><div><button type="button" className="secondary-button" onClick={() => setDeletePreview(null)}>取消</button><button type="button" className="danger-button" onClick={confirmTableDelete}>确认删除并联动</button></div></div></div>}
    </section>
  );
}
