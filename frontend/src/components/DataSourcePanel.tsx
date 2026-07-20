import { useState } from "react";
import type { Dataset, PlannedQuery } from "../types";

export function DataSourcePanel({ datasets, queries }: { datasets: Dataset[]; queries: PlannedQuery[] }) {
  const [copied, setCopied] = useState("");

  async function copySql(sql: string, source: string) {
    if (navigator.clipboard) await navigator.clipboard.writeText(sql);
    setCopied(source);
  }

  return (
    <aside className="source-panel panel">
      <div className="panel-header">
        <div><small>分析依据</small><h2>数据来源与 SQL</h2></div>
      </div>
      {!datasets.length && <div className="source-empty">完成查询后，这里会展示数据表血缘和只读 SQL。</div>}
      {datasets.map((dataset) => (
        <article className="source-card" key={dataset.source}>
          <div className="source-title"><span className="source-icon">DB</span><strong>{dataset.source}</strong></div>
          <span className="source-table-name">{dataset.table}</span>
          <dl>
            <div><dt>更新</dt><dd>{new Date(dataset.updated_at).toLocaleDateString("zh-CN")}</dd></div>
            <div><dt>置信度</dt><dd>{Math.round(dataset.confidence * 100)}%</dd></div>
            <div><dt>字段</dt><dd>{dataset.fields.join("、")}</dd></div>
          </dl>
        </article>
      ))}
      {queries.map((query) => (
        <article className="sql-card" key={query.source}>
          <div className="sql-toolbar">
            <span>SQL 查询 · {query.source}</span>
            <button type="button" onClick={() => copySql(query.sql, query.source)}>{copied === query.source ? "已复制" : "复制 SQL"}</button>
          </div>
          <pre><code>{query.sql}</code></pre>
        </article>
      ))}
    </aside>
  );
}
