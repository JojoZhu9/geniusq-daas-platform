import { useEffect, useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { api } from "../api/client";
import type { Requirement } from "../types";

export function RequirementMatrix() {
  const [rows, setRows] = useState<Requirement[]>([]);
  const [module, setModule] = useState("");
  const [priority, setPriority] = useState("");
  const [expanded, setExpanded] = useState("");
  const [searchParams] = useSearchParams();
  const focusId = searchParams.get("id") ?? "";

  useEffect(() => {
    api.get<Requirement[]>("/api/requirements").then((requirements) => {
      setRows(requirements);
      if (focusId) setExpanded(focusId);
    });
  }, [focusId]);

  const modules = useMemo(() => [...new Set(rows.map((row) => row.module))], [rows]);
  const visibleRows = rows.filter((row) => (!module || row.module === module) && (!priority || row.priority === priority));

  return (
    <section className="page-section requirements-page">
      <div className="page-heading"><div><small>项目交付 / 可验证需求</small><h1>0714 需求追踪矩阵</h1></div><div className="coverage-chip"><strong>{rows.length}/15</strong><span>需求已映射</span></div></div>
      <div className="requirement-stats">
        <article className="panel"><span>P0</span><strong>{rows.filter((row) => row.priority === "P0").length}</strong><small>核心验收项</small></article>
        <article className="panel"><span>P1</span><strong>{rows.filter((row) => row.priority === "P1").length}</strong><small>增强体验项</small></article>
        <article className="panel"><span>API</span><strong>100%</strong><small>页面与接口可追踪</small></article>
      </div>
      <div className="requirement-filters panel">
        <select aria-label="模块" value={module} onChange={(event) => setModule(event.target.value)}><option value="">全部模块</option>{modules.map((item) => <option value={item} key={item}>{item}</option>)}</select>
        <select aria-label="优先级" value={priority} onChange={(event) => setPriority(event.target.value)}><option value="">全部优先级</option><option value="P0">P0</option><option value="P1">P1</option></select>
        <span>当前显示 {visibleRows.length} 项</span>
      </div>
      <div className="panel requirement-table-wrap">
        <table className="requirement-table">
          <thead><tr><th>编号</th><th>优先级</th><th>原始需求</th><th>Demo 解决方案</th><th>对应页面</th><th>验收</th></tr></thead>
          <tbody>
            {visibleRows.map((row) => (
              <tr className={row.id === focusId ? "focused" : ""} key={row.id}>
                <td><strong>{row.id}</strong></td>
                <td><span className={`priority-pill ${row.priority.toLowerCase()}`}>{row.priority}</span></td>
                <td>{row.original}</td>
                <td>{row.solution}</td>
                <td>{row.page}</td>
                <td><button type="button" aria-label={`查看 ${row.id} 验收动作`} onClick={() => setExpanded(expanded === row.id ? "" : row.id)}>{expanded === row.id ? "收起" : "查看"}</button>{expanded === row.id && <div className="acceptance-detail"><strong>验收动作</strong><p>{row.acceptance}</p><span>状态：Demo 已实现</span></div>}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="matrix-note">矩阵以 `/api/requirements` 为唯一数据源，编号、页面与验收动作均可由自动化测试核对。</p>
    </section>
  );
}
