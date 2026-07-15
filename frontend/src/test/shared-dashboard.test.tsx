import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, vi } from "vitest";
import { App } from "../app";
import { json, renderWorkspace } from "./workspace-test-utils";

const sharedDashboard = {
  id: "d1",
  name: "房价分析看板",
  share_id: "share-1",
  share_url: "/share/share-1",
  requirement_ids: ["2.6"],
  cards: [{
    id: "card-1",
    title: "2025年各区房价趋势",
    analysis_id: "a1",
    chart: { type: "line", x_field: "month", y_fields: ["avg_price"], title: "2025年各区房价趋势" },
    datasets: [{
      source: "房产数据",
      table: "house_price_monthly",
      tables: ["house_price_monthly"],
      updated_at: "2026-07-14T00:00:00+08:00",
      confidence: 0.96,
      fields: ["month", "avg_price"],
      rows: [{ month: "2025-01", avg_price: 100000 }, { month: "2025-02", avg_price: 101200 }]
    }],
    layout: { x: 0, y: 0, w: 6, h: 4 }
  }]
};

beforeEach(() => vi.restoreAllMocks());

test("opens a copied dashboard URL as a read-only share page", async () => {
  const fetchMock = vi.fn((input: RequestInfo | URL) => {
    const path = String(input);
    if (path === "/api/dashboards/share/share-1") return json(sharedDashboard);
    if (path === "/api/conversations") return json({ id: "c1" }, 201);
    throw new Error(`Unexpected request: ${path}`);
  });
  vi.stubGlobal("fetch", fetchMock);

  renderWorkspace(<App />, "/share/share-1");

  expect(await screen.findByRole("heading", { name: "房价分析看板" })).toBeVisible();
  expect(screen.getByText("2025年各区房价趋势")).toBeVisible();
  expect(screen.getByText("只读分享")).toBeVisible();
  expect(screen.queryByRole("button", { name: "移动卡片" })).not.toBeInTheDocument();
  expect(screen.queryByRole("button", { name: "移除" })).not.toBeInTheDocument();
  expect(screen.getByRole("img", { name: "2025年各区房价趋势，折线图" })).toBeVisible();
  await userEvent.click(screen.getByRole("button", { name: "表格" }));
  expect(await screen.findByRole("table")).toHaveTextContent("101200");
  expect(fetchMock).toHaveBeenCalledWith(
    "/api/dashboards/share/share-1",
    expect.objectContaining({ headers: expect.objectContaining({ "Content-Type": "application/json" }) })
  );
});
