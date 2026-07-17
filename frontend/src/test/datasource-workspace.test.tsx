import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, vi } from "vitest";
import { DataSourceWorkspace } from "../pages/DataSourceWorkspace";
import { json, renderWorkspace } from "./workspace-test-utils";

const overview = {
  database: { engine: "SQLite", url: "sqlite:///backend/runtime/daas_demo.db" },
  table_count: 2,
  column_count: 8,
  row_count: 120,
  business_tables: ["house_price_monthly", "housing_transactions"]
};

const tables = [
  {
    name: "house_price_monthly",
    title: "房价月度指标",
    description: "按行政区和月份记录平均房价。",
    row_count: 72,
    column_count: 8
  },
  {
    name: "housing_transactions",
    title: "住房成交指标",
    description: "按行政区和月份记录成交。",
    row_count: 48,
    column_count: 6
  }
];

const detail = {
  ...tables[0],
  columns: [
    { name: "district", type: "TEXT", label: "行政区", role: "筛选 / 分组维度", is_primary_key: true, sample_value: "海淀区" },
    { name: "avg_price", type: "INTEGER", label: "平均房价", role: "可聚合指标", is_primary_key: false, sample_value: 98000 }
  ],
  sample_rows: [{ district: "海淀区", month: "2025-01", avg_price: 98000 }],
  suggested_questions: ["2025年各区平均房价趋势如何？"]
};

beforeEach(() => vi.restoreAllMocks());

test("renders datasource overview table detail and suggested questions", async () => {
  vi.stubGlobal("fetch", vi.fn((input: RequestInfo | URL) => {
    const path = String(input);
    if (path === "/api/datasource/overview") return json(overview);
    if (path === "/api/datasource/tables") return json(tables);
    if (path === "/api/datasource/tables/house_price_monthly") return json(detail);
    throw new Error(`Unexpected request: ${path}`);
  }));

  renderWorkspace(<DataSourceWorkspace />);

  expect(await screen.findByText("数据源管理")).toBeVisible();
  expect(screen.getByText("SQLite")).toBeVisible();
  expect(screen.getByText("house_price_monthly")).toBeVisible();
  expect(await screen.findByText("平均房价")).toBeVisible();
  expect(screen.getByText("2025年各区平均房价趋势如何？")).toBeVisible();

  await userEvent.click(screen.getByRole("button", { name: /housing_transactions/ }));
  expect(fetch).toHaveBeenCalledWith("/api/datasource/tables/housing_transactions", expect.anything());
});
