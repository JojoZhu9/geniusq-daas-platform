import { useEffect, useMemo, useRef, useState } from "react";
import * as echarts from "echarts/core";
import { BarChart, LineChart } from "echarts/charts";
import { GridComponent, LegendComponent, TooltipComponent } from "echarts/components";
import { SVGRenderer } from "echarts/renderers";
import type { EChartsCoreOption } from "echarts/core";
import type { ChartSpec, Dataset } from "../types";

echarts.use([
  LineChart,
  BarChart,
  GridComponent,
  LegendComponent,
  TooltipComponent,
  SVGRenderer
]);

type ChartType = ChartSpec["type"];
type RenderableChartType = "line" | "bar";
type ChartSeries = { name: string; data: number[] };

function unique(values: string[]) {
  return [...new Set(values)];
}

function buildSeries(chart: ChartSpec, datasets: Dataset[]) {
  const rows = datasets.flatMap((dataset) => dataset.rows);
  const districts = unique(rows.map((row) => String(row.district ?? "")).filter(Boolean));
  const groupByDistrict = chart.x_field !== "district"
    && chart.y_fields.length === 1
    && districts.length > 1;

  if (groupByDistrict) {
    const categories = unique(rows.map((row) => String(row[chart.x_field] ?? "")));
    const valueField = chart.y_fields[0];
    const series = districts.map((district) => ({
      name: district,
      data: categories.map((category) => {
        const row = rows.find((item) => String(item.district) === district
          && String(item[chart.x_field]) === category);
        return Number(row?.[valueField] ?? 0);
      })
    }));
    return { categories, series };
  }

  const rowsByCategory = new Map<string, Record<string, string | number>>();
  for (const row of rows) {
    const category = String(row[chart.x_field] ?? "");
    rowsByCategory.set(category, { ...(rowsByCategory.get(category) ?? {}), ...row });
  }
  const categories = [...rowsByCategory.keys()];
  const series = chart.y_fields.map((field) => ({
    name: field,
    data: categories.map((category) => Number(rowsByCategory.get(category)?.[field] ?? 0))
  }));
  return { categories, series };
}

function createOption(
  type: RenderableChartType,
  chart: ChartSpec,
  categories: string[],
  seriesRows: ChartSeries[]
): EChartsCoreOption {
  return {
    animation: false,
    color: ["#1682df", "#725fed", "#1ca779", "#f29a3f", "#e05f78", "#49a9bf"],
    tooltip: { trigger: "axis" },
    legend: {
      type: "scroll",
      top: 4,
      textStyle: { color: "#52677c", fontSize: 10 }
    },
    grid: { top: 42, right: 24, bottom: 48, left: 68 },
    xAxis: {
      type: "category",
      data: categories,
      axisLabel: { color: "#687d91", fontSize: 10, rotate: categories.length > 8 ? 30 : 0 },
      axisLine: { lineStyle: { color: "#cfd9e3" } }
    },
    yAxis: {
      type: "value",
      axisLabel: { color: "#687d91", fontSize: 10 },
      splitLine: { lineStyle: { color: "#edf1f5" } }
    },
    series: seriesRows.map((series) => ({
      name: series.name,
      type,
      data: series.data,
      smooth: type === "line",
      showSymbol: type === "line",
      symbolSize: 6,
      barMaxWidth: 26,
      lineStyle: type === "line" ? { width: 2.5 } : undefined,
      emphasis: { focus: "series" }
    }))
  };
}

export function AnalysisChart({ chart, datasets }: { chart: ChartSpec; datasets: Dataset[] }) {
  const [type, setType] = useState<ChartType>(chart.type === "table" ? "table" : chart.type);
  const chartElement = useRef<HTMLDivElement>(null);
  const tableRows = datasets[0]?.rows ?? [];
  const allRows = datasets.flatMap((dataset) => dataset.rows);
  const chartModel = useMemo(() => buildSeries(chart, datasets), [chart, datasets]);
  const option = useMemo(
    () => type === "line" || type === "bar"
      ? createOption(type, chart, chartModel.categories, chartModel.series)
      : null,
    [chart, chartModel, type]
  );

  useEffect(() => {
    const node = chartElement.current;
    if (!node || !option || (type !== "line" && type !== "bar")) return;

    const instance = echarts.init(node, undefined, {
      renderer: "svg",
      width: node.clientWidth || 640,
      height: node.clientHeight || 280
    });
    instance.setOption(option, true);

    const resize = () => instance.resize({
      width: node.clientWidth || 640,
      height: node.clientHeight || 280
    });
    const observer = typeof ResizeObserver === "undefined" ? null : new ResizeObserver(resize);
    observer?.observe(node);
    window.addEventListener("resize", resize);

    return () => {
      observer?.disconnect();
      window.removeEventListener("resize", resize);
      instance.dispose();
    };
  }, [option, type]);

  const typeLabel = type === "line" ? "折线图" : type === "bar" ? "柱状图" : "表格";

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
            <tbody>{tableRows.slice(0, 12).map((row, index) => <tr key={index}>{(datasets[0]?.fields ?? []).map((field) => <td key={field}>{row[field]}</td>)}</tr>)}</tbody>
          </table>
        </div>
      ) : (
        <div
          ref={chartElement}
          className="echart-view"
          role="img"
          aria-label={`${chart.title}，${typeLabel}`}
          data-chart-type={type}
        />
      )}
      <p className="chart-footnote">共 {allRows.length} 条记录 · 可切换图表类型 · 数据来自本地 SQLite</p>
    </section>
  );
}
