import { beforeEach, describe, expect, test, vi } from "vitest";

describe("api client deployment base URL", () => {
  beforeEach(() => {
    vi.resetModules();
    vi.unstubAllEnvs();
    vi.stubGlobal("fetch", vi.fn(async () => new Response(JSON.stringify({ ok: true }), {
      headers: { "Content-Type": "application/json" },
      status: 200
    })));
  });

  test("uses relative API paths when no deployment base URL is configured", async () => {
    const { api } = await import("../api/client");

    await api.get("/api/health");

    expect(fetch).toHaveBeenCalledWith("/api/health", expect.anything());
  });

  test("prefixes API paths with VITE_API_BASE_URL for deployed frontends", async () => {
    vi.stubEnv("VITE_API_BASE_URL", "https://geniusq-api.onrender.com/");
    const { api } = await import("../api/client");

    await api.get("/api/health");

    expect(fetch).toHaveBeenCalledWith("https://geniusq-api.onrender.com/api/health", expect.anything());
  });
});
