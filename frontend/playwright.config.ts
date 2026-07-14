import { fileURLToPath } from "node:url";
import { dirname, resolve } from "node:path";
import { defineConfig, devices } from "@playwright/test";

const frontendDir = dirname(fileURLToPath(import.meta.url));
const rootDir = resolve(frontendDir, "..");
const databaseName = `playwright-${process.pid}.db`;

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false,
  workers: 1,
  retries: 0,
  reporter: "list",
  use: {
    baseURL: "http://127.0.0.1:15173",
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
    ...devices["Desktop Chrome"]
  },
  webServer: [
    {
      command: "python -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 18000",
      cwd: rootDir,
      env: { ...process.env, DATABASE_URL: `sqlite:///./${databaseName}`, LLM_MODE: "offline" },
      url: "http://127.0.0.1:18000/api/health",
      reuseExistingServer: false,
      timeout: 30_000
    },
    {
      command: "npm.cmd run dev -- --port 15173",
      cwd: frontendDir,
      env: { ...process.env, VITE_API_PROXY: "http://127.0.0.1:18000" },
      url: "http://127.0.0.1:15173",
      reuseExistingServer: false,
      timeout: 30_000
    }
  ]
});
