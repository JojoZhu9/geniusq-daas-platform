import { useMemo, useState } from "react";
import type { ChartSpec, Dataset } from "../types";

type ChartType = ChartSpec["type"];

export function AnalysisChart({ chart, datasets }: { chart: ChartSpec; datasets: Dataset[] }) {
  const [type, setType] = useState<ChartType>(chart.type);
  const rows = datasets[0]?.rows ?? [];
  const valueField = chart.y_fields[0];
  const max = useMemo(
    () => Math.max(1, ...rows.map((row) => Number(row[valueField] ?? 0))),
    [rows, valueField]
  );

  return (
    <section className="analysis-chart" aria-label={chart.title}>
      <div className="chart-toolbar">
        <div><small>自动推荐图表</small><h3>{chart.title}</h3></div>
        <div className="segmented" aria-label="图表类型">
          {(["line", "bar", "table"] as ChartType[]).map((item) => (
            <button type="button" className={type === item ? "active" : ""} key={item} onClick={() => setType(item)}>
              {item === "line" ? "折线" : item === "bar" ? "柱状" : "表格"}
            </button>
          ))}
        </div>
      </div>
      {type === "table" ? (
        <div className="table-scroll">
          <table className="data-table">
            <thead><tr>{(datasets[0]?.fields ?? []).map((field) => <th key={field}>{field}</th>)}</tr></thead>
            <tbody>{rows.slice(0, 12).map((row, index) => <tr key={index}>{(datasets[0]?.fields ?? []).map((field) => <td key={field}>{row[field]}</td>)}</tr>)}</tbody>
          </table>
        </div>
      ) : (
        <div className={`mini-chart ${type}`}>
          {rows.slice(0, 12).map((row, index) => {
            const value = Number(row[valueField] ?? 0);
            return (
              <div className="chart-row" key={`${String(row[chart.x_field])}-${index}`}>
                <span>{String(row[chart.x_field] ?? index + 1)}</span>
                <div className="bar-track"><i style={{ width: `${Math.max(4, value / max * 100)}%` }} /></div>
                <strong>{value.toLocaleString("zh-CN")}</strong>
              </div>
            );
          })}
        </div>
      )}
      <p className="chart-footnote">显示前 {Math.min(12, rows.length)} 条记录 · 可切换图表类型 · 数据来自本地 SQLite</p>
    </section>
  );
}
