import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, vi } from "vitest";
import { RequirementMatrix } from "../pages/RequirementMatrix";
import { json, renderWorkspace } from "./workspace-test-utils";

const rows = [
  { id: "2.3", original: "支持多轮对话", title: "支持多轮对话", solution: "会话上下文", page: "智能问数工作台", acceptance: "继续追问只看海淀区", module: "智慧问数", priority: "P0", status: "planned" },
  { id: "3.2", original: "自动查重与私有优先", title: "自动查重与私有优先", solution: "指纹查重", page: "知识库管理", acceptance: "查看私有覆盖公开", module: "知识库管理", priority: "P0", status: "planned" }
];

beforeEach(() => vi.restoreAllMocks());

test("filters requirement rows by module and preserves source ids", async () => {
  vi.stubGlobal("fetch", vi.fn(() => json(rows)));

  renderWorkspace(<RequirementMatrix />, "/requirements");
  await userEvent.selectOptions(await screen.findByLabelText("模块"), "知识库管理");

  expect(screen.getByText("3.2")).toBeVisible();
  expect(screen.queryByText("2.3")).not.toBeInTheDocument();
});
