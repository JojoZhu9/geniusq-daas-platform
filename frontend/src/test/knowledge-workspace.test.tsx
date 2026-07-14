import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, vi } from "vitest";
import { KnowledgeWorkspace } from "../pages/KnowledgeWorkspace";
import { json, renderWorkspace } from "./workspace-test-utils";

const knowledgeItems = [{
  id: "private-1",
  name: "行政区房价口径",
  kind: "text",
  scope: "private",
  library: "个人知识库",
  content: "平均房价按行政区和月份统计，内部补充剔除无效成交。",
  linked_tables: ["house_price_monthly"],
  tags: ["房价", "指标口径", "私有优先"],
  schema_status: "valid",
  overrides_id: "public-1",
  conflict: { message: "私有知识优先，公开条目被覆盖", overrides_id: "public-1" },
  requirement_ids: ["3.2", "3.4-a", "3.4-b"]
}];

beforeEach(() => vi.restoreAllMocks());

test("shows that private knowledge overrides a public match", async () => {
  vi.stubGlobal("fetch", vi.fn((input: RequestInfo | URL) => {
    if (String(input).startsWith("/api/knowledge")) return json(knowledgeItems);
    if (String(input) === "/api/sync/logs") return json([]);
    throw new Error(`Unexpected request: ${String(input)}`);
  }));

  renderWorkspace(<KnowledgeWorkspace />);
  await userEvent.click(await screen.findByRole("button", { name: /行政区房价口径/ }));

  expect(screen.getByText("私有知识优先")).toBeVisible();
  expect(screen.getByText("公开条目被覆盖")).toBeVisible();
  expect(screen.getByRole("link", { name: "需求 3.2" })).toBeVisible();
  expect(screen.getAllByText("house_price_monthly").length).toBeGreaterThan(0);
});

test("runs the same auditable workflow for manual and scheduled demo sync", async () => {
  let syncCount = 0;
  vi.stubGlobal("fetch", vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
    const path = String(input);
    if (path.startsWith("/api/knowledge")) return json(knowledgeItems);
    if (path === "/api/sync/logs") return json([]);
    if (path === "/api/sync" && init?.method === "POST") {
      syncCount += 1;
      return json({ status: "completed", message: `第 ${syncCount} 次同步完成`, requirement_ids: ["3.3"] });
    }
    throw new Error(`Unexpected request: ${path}`);
  }));

  renderWorkspace(<KnowledgeWorkspace />);
  await userEvent.click(await screen.findByRole("button", { name: "手动同步" }));
  expect(await screen.findByText("第 1 次同步完成")).toBeVisible();
  await userEvent.click(screen.getByRole("button", { name: "模拟定时同步" }));
  expect(await screen.findByText("第 2 次同步完成")).toBeVisible();
});
