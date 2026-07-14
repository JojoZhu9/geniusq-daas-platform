import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, vi } from "vitest";
import { DashboardWorkspace } from "../pages/DashboardWorkspace";
import { json, renderWorkspace } from "./workspace-test-utils";

const dashboard = {
  id: "d1",
  name: "房价分析看板",
  share_id: "share-1",
  share_url: "/share/share-1",
  requirement_ids: ["2.6"],
  cards: [{
    id: "card-1",
    title: "2025年各区平均房价",
    analysis_id: "a1",
    chart: { type: "bar", x_field: "district", y_fields: ["avg_price"], title: "各区平均房价" },
    layout: { x: 0, y: 0, w: 6, h: 4 }
  }]
};

beforeEach(() => vi.restoreAllMocks());

test("persists a resized dashboard card", async () => {
  vi.stubGlobal("fetch", vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
    const path = String(input);
    if (path === "/api/dashboards" && !init?.method) return json([dashboard]);
    if (path === "/api/dashboards/d1/layout" && init?.method === "PATCH") return json({
      ...dashboard,
      cards: [{ ...dashboard.cards[0], layout: { x: 0, y: 0, w: 9, h: 5 } }]
    });
    throw new Error(`Unexpected request: ${path}`);
  }));

  renderWorkspace(<DashboardWorkspace />);
  await userEvent.click(await screen.findByRole("button", { name: "放大卡片" }));

  expect(await screen.findByText("布局已保存")).toBeVisible();
  expect(screen.getByText("9 × 5")).toBeVisible();
});
