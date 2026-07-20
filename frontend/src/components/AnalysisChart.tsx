import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import * as echarts from "echarts/core";
import { BarChart, LineChart, PieChart, ScatterChart } from "echarts/charts";
import { GridComponent, LegendComponent, TooltipComponent } from "echarts/components";
import { SVGRenderer } from "echarts/renderers";
import type { EChartsCoreOption } from "echarts/core";
import type { ChartSpec, Dataset } from "../types";
import { buildSeries } from "./charts/chartDataTransform";
import { createOption } from "./charts/chartOptions";
import { CHART_TYPES, chartTypeLabel, type ChartType, type RenderableChartType } from "./charts/chartTypes";

echarts.use([
  LineChart,
  BarChart,
  PieChart,
  ScatterChart,
  GridComponent,
  LegendComponent,
  TooltipComponent,
  SVGRenderer
]);

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
    () => type !== "table"
      ? createOption(type, chart, chartModel.categories, chartModel.series, chartModel.rows)
      : null,
    [chart, chartModel, type]
  );

  const typeLabel = chartTypeLabel(type);
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
        <div>
          <small>自动推荐图表</small>
          <h3>{chart.title}</h3>
          {chart.recommended_reason && <p className="chart-reason">{chart.recommended_reason}</p>}
        </div>
        <div className="segmented" aria-label="图表类型">
          {CHART_TYPES.map((item) => (
            <button type="button" className={type === item.type ? "active" : ""} key={item.type} onClick={() => selectType(item.type)}>
              {item.label}
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
        ) : option ? (
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
      <p className="chart-footnote">
        共 {allRows.length} 条记录 · 可切换图表类型 · 数据来自本地 SQLite
        {chart.unit ? ` · 单位：${chart.unit}` : ""}
      </p>
    </section>
  );
}
