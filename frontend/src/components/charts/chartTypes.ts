import type { ChartSpec } from "../../types";

export type ChartType = ChartSpec["type"];
export type RenderableChartType = Exclude<ChartType, "table">;

export const CHART_TYPES: { type: ChartType; label: string; aria: string }[] = [
  { type: "line", label: "折线", aria: "折线图" },
  { type: "bar", label: "柱状", aria: "柱状图" },
  { type: "pie", label: "饼图", aria: "饼图" },
  { type: "scatter", label: "散点", aria: "散点图" },
  { type: "stacked_bar", label: "堆叠", aria: "堆叠柱状图" },
  { type: "table", label: "表格", aria: "表格" }
];

export function chartTypeLabel(type: ChartType) {
  return CHART_TYPES.find((item) => item.type === type)?.aria ?? "图表";
}
