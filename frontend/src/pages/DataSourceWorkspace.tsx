import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api/client";
import type { DataSourceOverview, DataSourceTable, DataSourceTableDetail } from "../types";

function formatValue(value: string | number | null | undefined) {
  if (value === null || value === undefined || value === "") return "—";
  return String(value);
}

export function DataSourceWorkspace() {
  const navigate = useNavigate();
  const [overview, setOverview] = useState<DataSourceOverview | null>(null);
  const [tables, setTables] = useState<DataSourceTable[]>([]);
  const [selectedName, setSelectedName] = useState("");
  const [detail, setDetail] = useState<DataSourceTableDetail | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    Promise.all([
      api.get<DataSourceOverview>("/api/datasource/overview"),
      api.get<DataSourceTable[]>("/api/datasource/tables")
    ])
      .then(([nextOverview, nextTables]) => {
        if (!active) return;
        setOverview(nextOverview);
        setTables(nextTables);
        setSelectedName(nextTables[0]?.name ?? "");
      })
      .catch(() => {
        if (active) setError("无法读取本地数据源结构，请确认后端服务已启动。");
      });
    return () => { active = false; };
  }, []);

  useEffect(() => {
    if (!selectedName) return;
    let active = true;
    api.get<DataSourceTableDetail>(`/api/datasource/tables/${selectedName}`)
      .then((nextDetail) => { if (active) setDetail(nextDetail); })
      .catch(() => { if (active) setError("无法读取选中数据表详情。"); });
    return () => { active = false; };
  }, [selectedName]);

  const sampleColumns = useMemo(() => detail?.columns.slice(0, 6) ?? [], [detail]);

  return (
    <section className="page-section datasource-page">
      <div className="page-heading">
        <div>
          <small>智能问数 / 数据理解</small>
          <h1>数据源管理</h1>
        </div>
        <div className="coverage-chip">
          <strong>{overview?.table_count ?? "—"}</strong>
          <span>可问数数据表</span>
        </div>
      </div>

      {error && <div className="inline-alert">{error}</div>}

      <div className="datasource-overview-grid">
        <article className="panel metric-card">
          <small>数据库引擎</small>
          <strong>{overview?.database.engine ?? "加载中"}</strong>
          <span>{overview?.database.url ?? "正在读取运行时数据库"}</span>
        </article>
        <article className="panel metric-card">
          <small>字段数量</small>
          <strong>{overview?.column_count ?? "—"}</strong>
          <span>用于筛选、分组和聚合</span>
        </article>
        <article className="panel metric-card">
          <small>数据行数</small>
          <strong>{overview?.row_count ?? "—"}</strong>
          <span>当前本地演示库记录</span>
        </article>
      </div>

      <div className="datasource-layout">
        <aside className="panel datasource-table-list">
          <div className="panel-header">
            <div>
              <small>业务数据表</small>
              <h2>当前可查询数据</h2>
            </div>
          </div>
          {tables.map((table) => (
            <button
              type="button"
              className={table.name === selectedName ? "datasource-table-button is-active" : "datasource-table-button"}
              key={table.name}
              onClick={() => setSelectedName(table.name)}
            >
              <strong>{table.name}</strong>
              <span>{table.title} · {table.row_count} 行 · {table.column_count} 字段</span>
            </button>
          ))}
        </aside>

        <section className="panel datasource-detail">
          {detail ? (
            <>
              <div className="panel-header">
                <div>
                  <small>{detail.name}</small>
                  <h2>{detail.title}</h2>
                  <p>{detail.description}</p>
                </div>
              </div>

              <h3>字段结构</h3>
              <div className="datasource-column-table">
                <table>
                  <thead>
                    <tr>
                      <th>字段</th>
                      <th>含义</th>
                      <th>类型</th>
                      <th>用途</th>
                      <th>示例值</th>
                    </tr>
                  </thead>
                  <tbody>
                    {detail.columns.map((column) => (
                      <tr key={column.name}>
                        <td className="datasource-name-cell">
                          <code>{column.name}</code>
                          {column.is_primary_key && <span className="pk-chip">PK</span>}
                        </td>
                        <td>{column.label}</td>
                        <td>{column.type}</td>
                        <td>{column.role}</td>
                        <td className="datasource-value-cell">{formatValue(column.sample_value)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              <h3>样例数据</h3>
              <div className="datasource-sample-table">
                <table>
                  <thead>
                    <tr>{sampleColumns.map((column) => <th key={column.name}>{column.name}</th>)}</tr>
                  </thead>
                  <tbody>
                    {detail.sample_rows.map((row, index) => (
                      <tr key={index}>
                        {sampleColumns.map((column) => (
                          <td className="datasource-value-cell" key={column.name}>
                            {formatValue(row[column.name])}
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              <h3>这张表可以这样问</h3>
              <div className="suggestion-row">
                {detail.suggested_questions.map((question) => (
                  <button
                    className="question-chip"
                    key={question}
                    type="button"
                    onClick={() => navigate(`/query?question=${encodeURIComponent(question)}`)}
                  >
                    {question}
                  </button>
                ))}
              </div>
            </>
          ) : (
            <div className="empty-state">正在读取数据表详情...</div>
          )}
        </section>
      </div>
    </section>
  );
}
