import { useCallback, useEffect, useMemo, useRef, useState } from "react";
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

function EChartView({
  type,
  option,
  label,
  onReady
}: {
  type: RenderableChartType;
  option: EChartsCoreOption;
  label: string;
  onReady: () => void;
}) {
  const chartElement = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const node = chartElement.current;
    if (!node) return;

    const instance = echarts.init(node, undefined, {
      renderer: "svg",
      width: node.clientWidth || 640,
      height: node.clientHeight || 280
    });
    instance.setOption(option, true);
    onReady();

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
  }, [onReady, option]);

  return (
    <div
      ref={chartElement}
      className="echart-view"
      role="img"
      aria-label={label}
      data-chart-type={type}
    />
  );
}

export function AnalysisChart({
  chart,
  datasets = [],
  onTypeChange
}: {
  chart: ChartSpec;
  datasets?: Dataset[];
  onTypeChange?: (type: ChartType) => void;
}) {
  const [type, setType] = useState<ChartType>(chart.type === "table" ? "table" : chart.type);
  const [isSwitching, setIsSwitching] = useState(false);
  const tableRows = datasets[0]?.rows ?? [];
  const tableFields = datasets[0]?.fields ?? [];
  const allRows = datasets.flatMap((dataset) => dataset.rows);
  const chartModel = useMemo(() => buildSeries(chart, datasets), [chart, datasets]);
  const option = useMemo(
    () => type === "line" || type === "bar"
      ? createOption(type, chart, chartModel.categories, chartModel.series)
      : null,
    [chart, chartModel, type]
  );

  const typeLabel = type === "line" ? "折线图" : type === "bar" ? "柱状图" : "表格";
  const markViewReady = useCallback(() => setIsSwitching(false), []);

  useEffect(() => {
    if (type === "table") markViewReady();
  }, [markViewReady, type]);

  const selectType = (nextType: ChartType) => {
    if (nextType === type) return;
    setIsSwitching(true);
    setType(nextType);
    onTypeChange?.(nextType);
  };

  return (
    <section className="analysis-chart" aria-label={chart.title}>
      <div className="chart-toolbar">
        <div><small>自动推荐图表</small><h3>{chart.title}</h3></div>
        <div className="segmented" aria-label="图表类型">
          {(["line", "bar", "table"] as ChartType[]).map((item) => (
            <button type="button" className={type === item ? "active" : ""} key={item} onClick={() => selectType(item)}>
              {item === "line" ? "折线" : item === "bar" ? "柱状" : "表格"}
            </button>
          ))}
        </div>
      </div>
      <div className="chart-stage" aria-busy={isSwitching}>
        {isSwitching && (
          <div className="chart-switching" role="status">
            <span className="spinner chart-spinner" aria-hidden="true" />
            正在切换到{typeLabel}…
          </div>
        )}
        {allRows.length === 0 ? (
          <div className="chart-fallback" role="status">原分析数据尚未加载，请刷新页面。</div>
        ) : type === "table" ? (
          <div className="table-scroll">
            <table className="data-table">
              <thead><tr>{tableFields.map((field) => <th key={field}>{field}</th>)}</tr></thead>
              <tbody>
                {tableRows.length > 0 ? tableRows.slice(0, 12).map((row, index) => (
                  <tr key={index}>{tableFields.map((field) => <td key={field}>{row[field]}</td>)}</tr>
                )) : (
                  <tr><td className="table-empty" colSpan={Math.max(tableFields.length, 1)}>暂无表格数据</td></tr>
                )}
              </tbody>
            </table>
          </div>
        ) : (type === "line" || type === "bar") && option ? (
          <EChartView
            key={type}
            type={type}
            option={option}
            label={`${chart.title}，${typeLabel}`}
            onReady={markViewReady}
          />
        ) : (
          <div className="chart-fallback" role="status">图表数据准备中…</div>
        )}
      </div>
      <p className="chart-footnote">共 {allRows.length} 条记录 · 可切换图表类型 · 数据来自本地 SQLite</p>
    </section>
  );
}
