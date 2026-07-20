import type { EChartsCoreOption } from "echarts/core";
import type { ChartSpec } from "../../types";
import type { ChartSeries } from "./chartDataTransform";
import type { RenderableChartType } from "./chartTypes";

export function createOption(
  type: RenderableChartType,
  chart: ChartSpec,
  categories: string[],
  seriesRows: ChartSeries[],
  rows: Record<string, string | number>[]
): EChartsCoreOption {
  const common = {
    animation: false,
    color: ["#1682df", "#725fed", "#1ca779", "#f29a3f", "#e05f78", "#49a9bf"],
    tooltip: { trigger: type === "pie" ? "item" : "axis" },
    legend: {
      type: "scroll",
      top: 4,
      textStyle: { color: "#52677c", fontSize: 10 }
    }
  } satisfies EChartsCoreOption;

  if (type === "pie") {
    const valueField = chart.y_fields[0];
    return {
      ...common,
      series: [{
        name: valueField,
        type: "pie",
        radius: ["38%", "68%"],
        center: ["50%", "55%"],
        data: categories.map((category) => {
          const row = rows.find((item) => String(item[chart.x_field]) === category);
          return { name: category, value: Number(row?.[valueField] ?? 0) };
        }),
        emphasis: { focus: "self" }
      }]
    };
  }

  if (type === "scatter") {
    const yField = chart.y_fields[0];
    return {
      ...common,
      grid: { top: 42, right: 24, bottom: 52, left: 68 },
      xAxis: {
        type: "value",
        name: chart.x_axis_name ?? chart.x_field,
        axisLabel: { color: "#687d91", fontSize: 10 },
        splitLine: { lineStyle: { color: "#edf1f5" } }
      },
      yAxis: {
        type: "value",
        name: chart.y_axis_name ?? yField,
        axisLabel: { color: "#687d91", fontSize: 10 },
        splitLine: { lineStyle: { color: "#edf1f5" } }
      },
      series: [{
        name: yField,
        type: "scatter",
        symbolSize: 10,
        data: rows.map((row) => [Number(row[chart.x_field] ?? 0), Number(row[yField] ?? 0)])
      }]
    };
  }

  const isStacked = type === "stacked_bar";
  return {
    ...common,
    grid: { top: 42, right: 24, bottom: 52, left: 68 },
    xAxis: {
      type: "category",
      name: chart.x_axis_name ?? undefined,
      data: categories,
      axisLabel: { color: "#687d91", fontSize: 10, rotate: categories.length > 8 ? 30 : 0 },
      axisLine: { lineStyle: { color: "#cfd9e3" } }
    },
    yAxis: {
      type: "value",
      name: chart.y_axis_name ?? chart.unit ?? undefined,
      axisLabel: { color: "#687d91", fontSize: 10 },
      splitLine: { lineStyle: { color: "#edf1f5" } }
    },
    series: seriesRows.map((series) => ({
      name: series.name,
      type: type === "line" ? "line" : "bar",
      stack: isStacked ? "total" : undefined,
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
