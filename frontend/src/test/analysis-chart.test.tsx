import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { AnalysisChart } from "../components/AnalysisChart";
import type { ChartSpec, Dataset } from "../types";

const chart: ChartSpec = {
  type: "line",
  x_field: "month",
  y_fields: ["avg_price"],
  title: "2025年各区房价趋势"
};

const datasets: Dataset[] = [{
  source: "房产数据",
  table: "house_price_monthly",
  tables: ["house_price_monthly"],
  updated_at: "2026-07-14T00:00:00+08:00",
  confidence: 0.96,
  fields: ["month", "district", "avg_price"],
  rows: [
    { month: "2025-01", district: "海淀区", avg_price: 100000 },
    { month: "2025-02", district: "海淀区", avg_price: 101200 },
    { month: "2025-01", district: "朝阳区", avg_price: 77000 },
    { month: "2025-02", district: "朝阳区", avg_price: 78300 }
  ]
}];

test("renders genuinely different SVG line and bar charts", async () => {
  render(<AnalysisChart chart={chart} datasets={datasets} />);

  const lineView = await screen.findByRole("img", { name: "2025年各区房价趋势，折线图" });
  await waitFor(() => expect(lineView.querySelector("svg")).not.toBeNull());
  const lineMarkup = lineView.innerHTML;

  await userEvent.click(screen.getByRole("button", { name: "柱状" }));

  const barView = await screen.findByRole("img", { name: "2025年各区房价趋势，柱状图" });
  await waitFor(() => expect(barView.querySelector("svg")).not.toBeNull());
  expect(barView).toHaveAttribute("data-chart-type", "bar");
  expect(barView.innerHTML).not.toBe(lineMarkup);
  expect(document.querySelector(".bar-track")).not.toBeInTheDocument();
});

test("keeps table rows visible after switching away from ECharts", async () => {
  render(<AnalysisChart chart={chart} datasets={datasets} />);

  await userEvent.click(screen.getByRole("button", { name: "柱状" }));
  await waitFor(() => expect(screen.getByRole("img").querySelector("svg")).not.toBeNull());

  await userEvent.click(screen.getByRole("button", { name: "表格" }));

  const table = await screen.findByRole("table");
  expect(table).toHaveTextContent("avg_price");
  expect(table).toHaveTextContent("100000");
});

test("renders pie, scatter, and stacked bar chart types", async () => {
  const richChart: ChartSpec = {
    ...chart,
    type: "pie",
    x_field: "district",
    y_fields: ["avg_price", "rent_price"],
    title: "Chart type upgrade"
  };
  const richDatasets: Dataset[] = [{
    ...datasets[0],
    fields: ["district", "avg_price", "rent_price"],
    rows: [
      { district: "A", avg_price: 100, rent_price: 10 },
      { district: "B", avg_price: 80, rent_price: 8 }
    ]
  }];
  render(<AnalysisChart chart={richChart} datasets={richDatasets} />);

  const pieView = await screen.findByRole("img", { name: "Chart type upgrade，饼图" });
  await waitFor(() => expect(pieView.querySelector("svg")).not.toBeNull());
  expect(pieView).toHaveAttribute("data-chart-type", "pie");

  await userEvent.click(screen.getByRole("button", { name: "散点" }));
  const scatterView = await screen.findByRole("img", { name: "Chart type upgrade，散点图" });
  await waitFor(() => expect(scatterView.querySelector("svg")).not.toBeNull());
  expect(scatterView).toHaveAttribute("data-chart-type", "scatter");

  await userEvent.click(screen.getByRole("button", { name: "堆叠" }));
  const stackedView = await screen.findByRole("img", { name: "Chart type upgrade，堆叠柱状图" });
  await waitFor(() => expect(stackedView.querySelector("svg")).not.toBeNull());
  expect(stackedView).toHaveAttribute("data-chart-type", "stacked_bar");
});
