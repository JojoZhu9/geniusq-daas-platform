import { screen } from "@testing-library/react";
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
  expect(fetchMock).toHaveBeenCalledWith(
    "/api/dashboards/share/share-1",
    expect.objectContaining({ headers: expect.objectContaining({ "Content-Type": "application/json" }) })
  );
});
