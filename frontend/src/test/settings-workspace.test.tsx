import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, vi } from "vitest";
import { SettingsWorkspace } from "../pages/SettingsWorkspace";
import { json, renderWorkspace } from "./workspace-test-utils";

const settings = {
  llm_mode: "deepseek",
  deepseek_base_url: "https://api.deepseek.com",
  deepseek_model: "deepseek-chat",
  deepseek_api_key_configured: true,
  deepseek_api_key_masked: "sk-****3456"
};

beforeEach(() => vi.restoreAllMocks());

test("renders masked DeepSeek configuration and tests connection", async () => {
  vi.stubGlobal("fetch", vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
    const path = String(input);
    if (path === "/api/model-settings" && !init?.method) return json(settings);
    if (path === "/api/model-settings/deepseek/test" && init?.method === "POST") {
      return json({ ok: true, mode: "deepseek", message: "DeepSeek 连接测试成功。" });
    }
    throw new Error(`Unexpected request: ${path}`);
  }));

  renderWorkspace(<SettingsWorkspace />);

  expect(await screen.findByText("运行配置")).toBeVisible();
  expect(screen.getByText("sk-****3456")).toBeVisible();
  expect(screen.queryByText("sk-demo-secret-123456")).not.toBeInTheDocument();

  await userEvent.click(screen.getByRole("button", { name: "测试连接" }));
  expect(await screen.findByText("DeepSeek 连接测试成功。")).toBeVisible();
});
