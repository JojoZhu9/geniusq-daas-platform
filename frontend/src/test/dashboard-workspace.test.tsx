import { fireEvent, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, vi } from "vitest";
import { DashboardWorkspace } from "../pages/DashboardWorkspace";
import { json, renderWorkspace } from "./workspace-test-utils";

const datasets = [{
  source: "房产数据",
  table: "house_price_monthly",
  tables: ["house_price_monthly"],
  updated_at: "2026-07-14T00:00:00+08:00",
  confidence: 0.96,
  fields: ["district", "avg_price"],
  rows: [{ district: "海淀区", avg_price: 101200 }, { district: "朝阳区", avg_price: 78300 }]
}];

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
    datasets,
    layout: { x: 0, y: 0, w: 6, h: 4 }
  }]
};

const stackedDashboard = {
  ...dashboard,
  cards: Array.from({ length: 4 }, (_, index) => ({
    ...dashboard.cards[0],
    id: `card-${index + 1}`,
    title: `图表 ${index + 1}`,
    layout: { x: 0, y: index * 4, w: 6, h: 4 }
  }))
};

const twoColumnDashboard = {
  ...dashboard,
  cards: [
    { ...dashboard.cards[0], id: "card-1", title: "左侧图表", layout: { x: 0, y: 0, w: 6, h: 4 } },
    { ...dashboard.cards[0], id: "card-2", title: "右侧图表", layout: { x: 6, y: 0, w: 6, h: 4 } }
  ]
};

beforeEach(() => vi.restoreAllMocks());

test("dashboard workspace can be imported from the split page module", async () => {
  const module = await import("../pages/dashboard/DashboardWorkspace");

  expect(module.DashboardWorkspace).toBe(DashboardWorkspace);
});

test("creates a dashboard with a custom name", async () => {
  const fetchMock = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
    const path = String(input);
    if (path === "/api/dashboards" && !init?.method) return json([]);
    if (path === "/api/dashboards" && init?.method === "POST") {
      return json({
        id: "custom-dashboard",
        name: "2025区域成交看板",
        share_id: "share-custom",
        share_url: "/share/share-custom",
        requirement_ids: ["2.6"],
        cards: []
      }, 201);
    }
    throw new Error(`Unexpected request: ${path}`);
  });
  vi.stubGlobal("fetch", fetchMock);

  renderWorkspace(<DashboardWorkspace />);
  await userEvent.click(await screen.findByRole("button", { name: "新建仪表盘" }));
  await userEvent.clear(screen.getByLabelText("仪表盘名称"));
  await userEvent.type(screen.getByLabelText("仪表盘名称"), "2025区域成交看板");
  await userEvent.click(screen.getByRole("button", { name: "创建" }));

  await screen.findByRole("heading", { name: "2025区域成交看板" });
  const request = fetchMock.mock.calls.find(([input, init]) => (
    String(input) === "/api/dashboards" && init?.method === "POST"
  ));
  expect(JSON.parse(String(request?.[1]?.body))).toEqual({ name: "2025区域成交看板" });
});

test("renames the selected dashboard", async () => {
  let current = dashboard;
  const fetchMock = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
    const path = String(input);
    if (path === "/api/dashboards" && !init?.method) return json([current]);
    if (path === "/api/dashboards/d1" && init?.method === "PATCH") {
      current = { ...current, name: JSON.parse(String(init.body)).name };
      return json(current);
    }
    throw new Error(`Unexpected request: ${path}`);
  });
  vi.stubGlobal("fetch", fetchMock);

  renderWorkspace(<DashboardWorkspace />);
  await screen.findByRole("heading", { name: "房价分析看板" });
  await userEvent.click(screen.getByRole("button", { name: "重命名仪表盘" }));
  await userEvent.clear(screen.getByLabelText("新仪表盘名称"));
  await userEvent.type(screen.getByLabelText("新仪表盘名称"), "2025区域成交看板");
  await userEvent.click(screen.getByRole("button", { name: "保存名称" }));

  expect(await screen.findByRole("heading", { name: "2025区域成交看板" })).toBeVisible();
  expect(await screen.findByText("已重命名为“2025区域成交看板”")).toBeVisible();
  expect(fetchMock).toHaveBeenCalledWith(
    "/api/dashboards/d1",
    expect.objectContaining({
      method: "PATCH",
      body: JSON.stringify({ name: "2025区域成交看板" })
    })
  );
});

test("does not rename a dashboard with a blank name", async () => {
  const fetchMock = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
    const path = String(input);
    if (path === "/api/dashboards" && !init?.method) return json([dashboard]);
    if (path === "/api/dashboards/d1" && init?.method === "PATCH") {
      return json({ code: "SHOULD_NOT_CALL" }, 500);
    }
    throw new Error(`Unexpected request: ${path}`);
  });
  vi.stubGlobal("fetch", fetchMock);

  renderWorkspace(<DashboardWorkspace />);
  await screen.findByRole("heading", { name: "房价分析看板" });
  await userEvent.click(screen.getByRole("button", { name: "重命名仪表盘" }));
  await userEvent.clear(screen.getByLabelText("新仪表盘名称"));
  await userEvent.click(screen.getByRole("button", { name: "保存名称" }));

  expect(await screen.findByText("仪表盘名称不能为空")).toBeVisible();
  expect(fetchMock).not.toHaveBeenCalledWith(
    "/api/dashboards/d1",
    expect.objectContaining({ method: "PATCH" })
  );
});

test("does not rename a dashboard to an existing dashboard name", async () => {
  const otherDashboard = { ...dashboard, id: "d2", name: "成交看板", share_id: "share-2", share_url: "/share/share-2", cards: [] };
  const fetchMock = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
    const path = String(input);
    if (path === "/api/dashboards" && !init?.method) return json([dashboard, otherDashboard]);
    if (path === "/api/dashboards/d1" && init?.method === "PATCH") {
      return json({ code: "SHOULD_NOT_CALL" }, 500);
    }
    throw new Error(`Unexpected request: ${path}`);
  });
  vi.stubGlobal("fetch", fetchMock);

  renderWorkspace(<DashboardWorkspace />);
  await screen.findByRole("heading", { name: "房价分析看板" });
  await userEvent.click(screen.getByRole("button", { name: "重命名仪表盘" }));
  await userEvent.clear(screen.getByLabelText("新仪表盘名称"));
  await userEvent.type(screen.getByLabelText("新仪表盘名称"), "成交看板");
  await userEvent.click(screen.getByRole("button", { name: "保存名称" }));

  expect(await screen.findByText("仪表盘名称已存在，请换一个名称")).toBeVisible();
  expect(fetchMock).not.toHaveBeenCalledWith(
    "/api/dashboards/d1",
    expect.objectContaining({ method: "PATCH" })
  );
});

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
  expect(screen.getByRole("button", { name: "拖动卡片：2025年各区平均房价" })).toHaveTextContent("9 × 5");
});

test("previews and saves a blank grid drop target while dragging", async () => {
  let current = dashboard;
  let savedCards: Array<{ id: string; x: number; y: number; w: number; h: number }> = [];
  vi.stubGlobal("fetch", vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
    const path = String(input);
    if (path === "/api/dashboards" && !init?.method) return json([current]);
    if (path === "/api/dashboards/d1/layout" && init?.method === "PATCH") {
      savedCards = JSON.parse(String(init.body)).cards;
      current = {
        ...dashboard,
        cards: dashboard.cards.map((card) => {
          const next = savedCards.find((item) => item.id === card.id);
          return next ? { ...card, layout: { x: next.x, y: next.y, w: next.w, h: next.h } } : card;
        })
      };
      return json(current);
    }
    throw new Error(`Unexpected request: ${path}`);
  }));

  renderWorkspace(<DashboardWorkspace />);
  const card = (await screen.findByRole("heading", { name: "2025年各区平均房价" })).closest("article");
  expect(card).toHaveStyle({ gridColumnStart: "1" });
  expect(screen.queryByRole("button", { name: "移动卡片" })).not.toBeInTheDocument();

  const grid = document.querySelector(".dashboard-grid") as HTMLDivElement;
  vi.spyOn(grid, "getBoundingClientRect").mockReturnValue({
    x: 0,
    y: 0,
    left: 0,
    top: 0,
    right: 1200,
    bottom: 600,
    width: 1200,
    height: 600,
    toJSON: () => ({})
  });
  fireEvent.pointerDown(screen.getByRole("button", { name: "拖动卡片：2025年各区平均房价" }), { button: 0 });
  fireEvent(grid, new MouseEvent("pointermove", { bubbles: true, clientX: 900, clientY: 80 }));
  expect(screen.getByRole("status", { name: "卡片空白落点" })).toHaveStyle({
    gridColumnStart: "7",
    gridRowStart: "1"
  });
  fireEvent(grid, new MouseEvent("pointermove", { bubbles: true, clientX: 900, clientY: 200 }));
  expect(screen.getByRole("status", { name: "卡片空白落点" })).toHaveStyle({
    gridColumnStart: "7",
    gridRowStart: "1"
  });
  fireEvent(grid, new MouseEvent("pointerup", { bubbles: true, clientX: 900, clientY: 200 }));

  await waitFor(() => expect(savedCards).toEqual([{ id: "card-1", x: 6, y: 0, w: 6, h: 4 }]));
  expect(await screen.findByText("布局已保存")).toBeVisible();
  expect(card).toHaveStyle({ gridColumnStart: "7" });
  expect(card).toHaveAttribute("data-grid-x", "6");
});

test("clears the blank placeholder when hovering another card", async () => {
  vi.stubGlobal("fetch", vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
    const path = String(input);
    if (path === "/api/dashboards" && !init?.method) return json([twoColumnDashboard]);
    if (path === "/api/dashboards/d1/layout" && init?.method === "PATCH") return json(twoColumnDashboard);
    throw new Error(`Unexpected request: ${path}`);
  }));

  renderWorkspace(<DashboardWorkspace />);
  const leftCard = (await screen.findByRole("heading", { name: "左侧图表" })).closest("article")!;
  const rightCard = screen.getByRole("heading", { name: "右侧图表" }).closest("article")!;
  const grid = document.querySelector(".dashboard-grid") as HTMLDivElement;
  vi.spyOn(grid, "getBoundingClientRect").mockReturnValue({
    x: 0,
    y: 0,
    left: 0,
    top: 0,
    right: 1200,
    bottom: 600,
    width: 1200,
    height: 600,
    toJSON: () => ({})
  });

  fireEvent.pointerDown(within(leftCard).getByRole("button", { name: "拖动卡片：左侧图表" }), { button: 0 });
  fireEvent(grid, new MouseEvent("pointermove", { bubbles: true, clientX: 900, clientY: 360 }));
  expect(screen.getByRole("status", { name: "卡片空白落点" })).toBeVisible();
  fireEvent.pointerEnter(rightCard);

  expect(screen.queryByRole("status", { name: "卡片空白落点" })).not.toBeInTheDocument();
  expect(rightCard).toHaveClass("drop-target");
});

test("does not swap cards from an occupied blank-grid release without direct card hover", async () => {
  let savedCards: Array<{ id: string; x: number; y: number; w: number; h: number }> = [];
  vi.stubGlobal("fetch", vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
    const path = String(input);
    if (path === "/api/dashboards" && !init?.method) return json([twoColumnDashboard]);
    if (path === "/api/dashboards/d1/layout" && init?.method === "PATCH") {
      savedCards = JSON.parse(String(init.body)).cards;
      return json(twoColumnDashboard);
    }
    throw new Error(`Unexpected request: ${path}`);
  }));

  renderWorkspace(<DashboardWorkspace />);
  const leftCard = (await screen.findByRole("heading", { name: "左侧图表" })).closest("article")!;
  const rightCard = screen.getByRole("heading", { name: "右侧图表" }).closest("article")!;
  const grid = document.querySelector(".dashboard-grid") as HTMLDivElement;
  vi.spyOn(grid, "getBoundingClientRect").mockReturnValue({
    x: 0,
    y: 0,
    left: 0,
    top: 0,
    right: 1200,
    bottom: 600,
    width: 1200,
    height: 600,
    toJSON: () => ({})
  });

  fireEvent.pointerDown(within(leftCard).getByRole("button", { name: "拖动卡片：左侧图表" }), { button: 0 });
  fireEvent(grid, new MouseEvent("pointermove", { bubbles: true, clientX: 900, clientY: 80 }));
  expect(screen.queryByRole("status", { name: "卡片空白落点" })).not.toBeInTheDocument();
  fireEvent(grid, new MouseEvent("pointerup", { bubbles: true, clientX: 900, clientY: 80 }));

  expect(savedCards).toEqual([]);
  expect(leftCard).toHaveStyle({ gridColumnStart: "1" });
  expect(rightCard).toHaveStyle({ gridColumnStart: "7" });
});

test("renders the saved analysis chart and allows switching to its data table", async () => {
  vi.stubGlobal("fetch", vi.fn((input: RequestInfo | URL) => {
    if (String(input) === "/api/dashboards") return json([dashboard]);
    throw new Error(`Unexpected request: ${String(input)}`);
  }));

  renderWorkspace(<DashboardWorkspace />);

  const barView = await screen.findByRole("img", { name: "2025年各区平均房价，柱状图" });
  expect(barView.querySelector("svg")).not.toBeNull();
  await userEvent.click(screen.getByRole("button", { name: "表格" }));
  expect(await screen.findByRole("table")).toHaveTextContent("海淀区");
  expect(screen.getByRole("table")).toHaveTextContent("101200");
});

test("keeps the dashboard visible while a legacy API response has no datasets", async () => {
  const legacyDashboard = {
    ...dashboard,
    cards: dashboard.cards.map(({ datasets: _datasets, ...card }) => card)
  };
  vi.stubGlobal("fetch", vi.fn((input: RequestInfo | URL) => {
    if (String(input) === "/api/dashboards") return json([legacyDashboard]);
    throw new Error(`Unexpected request: ${String(input)}`);
  }));

  renderWorkspace(<DashboardWorkspace />);

  expect(await screen.findByRole("heading", { name: "2025年各区平均房价" })).toBeVisible();
  expect(screen.getByRole("status")).toHaveTextContent("原分析数据尚未加载");
});

test("automatically compacts a legacy single-column layout into two columns", async () => {
  let current = stackedDashboard;
  const fetchMock = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
    const path = String(input);
    if (path === "/api/dashboards" && !init?.method) return json([current]);
    if (path === "/api/dashboards/d1/layout" && init?.method === "PATCH") {
      const payload = JSON.parse(String(init.body));
      current = {
        ...current,
        cards: current.cards.map((card) => {
          const next = payload.cards.find((item: { id: string }) => item.id === card.id);
          return next ? { ...card, layout: { x: next.x, y: next.y, w: next.w, h: next.h } } : card;
        })
      };
      return json(current);
    }
    throw new Error(`Unexpected request: ${path}`);
  });
  vi.stubGlobal("fetch", fetchMock);

  renderWorkspace(<DashboardWorkspace />);

  await waitFor(() => expect(fetchMock).toHaveBeenCalledWith(
    "/api/dashboards/d1/layout",
    expect.objectContaining({ method: "PATCH" })
  ));
  const cards = await screen.findAllByRole("article");
  expect(cards[0]).toHaveStyle({ gridColumnStart: "1", gridRowStart: "1" });
  expect(cards[1]).toHaveStyle({ gridColumnStart: "7", gridRowStart: "1" });
  expect(cards[2]).toHaveStyle({ gridColumnStart: "1", gridRowStart: "5" });
  expect(cards[3]).toHaveStyle({ gridColumnStart: "7", gridRowStart: "5" });
});

test("compacts a legacy single-column layout even when deleted cards left row gaps", async () => {
  let current = {
    ...stackedDashboard,
    cards: stackedDashboard.cards.filter((card) => card.id !== "card-2")
  };
  const fetchMock = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
    const path = String(input);
    if (path === "/api/dashboards" && !init?.method) return json([current]);
    if (path === "/api/dashboards/d1/layout" && init?.method === "PATCH") {
      const payload = JSON.parse(String(init.body));
      current = {
        ...current,
        cards: current.cards.map((card) => {
          const next = payload.cards.find((item: { id: string }) => item.id === card.id);
          return next ? { ...card, layout: { x: next.x, y: next.y, w: next.w, h: next.h } } : card;
        })
      };
      return json(current);
    }
    throw new Error(`Unexpected request: ${path}`);
  });
  vi.stubGlobal("fetch", fetchMock);

  renderWorkspace(<DashboardWorkspace />);

  const cards = await screen.findAllByRole("article");
  await waitFor(() => expect(fetchMock).toHaveBeenCalledWith(
    "/api/dashboards/d1/layout",
    expect.objectContaining({ method: "PATCH" })
  ));
  expect(cards[0]).toHaveStyle({ gridColumnStart: "1", gridRowStart: "1" });
  expect(cards[1]).toHaveStyle({ gridColumnStart: "7", gridRowStart: "1" });
  expect(cards[2]).toHaveStyle({ gridColumnStart: "1", gridRowStart: "5" });
});

test("drags a card onto another card and persists their swapped positions", async () => {
  let current = twoColumnDashboard;
  let savedCards: Array<{ id: string; x: number; y: number; w: number; h: number }> = [];
  vi.stubGlobal("fetch", vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
    const path = String(input);
    if (path === "/api/dashboards" && !init?.method) return json([current]);
    if (path === "/api/dashboards/d1/layout" && init?.method === "PATCH") {
      savedCards = JSON.parse(String(init.body)).cards;
      current = {
        ...current,
        cards: current.cards.map((card) => {
          const next = savedCards.find((item) => item.id === card.id);
          return next ? { ...card, layout: { x: next.x, y: next.y, w: next.w, h: next.h } } : card;
        })
      };
      return json(current);
    }
    throw new Error(`Unexpected request: ${path}`);
  }));

  renderWorkspace(<DashboardWorkspace />);
  const leftCard = (await screen.findByRole("heading", { name: "左侧图表" })).closest("article")!;
  const rightCard = screen.getByRole("heading", { name: "右侧图表" }).closest("article")!;
  fireEvent.pointerDown(screen.getByRole("button", { name: "拖动卡片：左侧图表" }), { button: 0 });
  fireEvent.pointerEnter(rightCard);
  fireEvent.pointerUp(rightCard);

  await waitFor(() => expect(savedCards).toEqual(expect.arrayContaining([
    { id: "card-1", x: 6, y: 0, w: 6, h: 4 },
    { id: "card-2", x: 0, y: 0, w: 6, h: 4 }
  ])));
  expect(leftCard).toHaveStyle({ gridColumnStart: "7" });
  expect(rightCard).toHaveStyle({ gridColumnStart: "1" });
  expect(await screen.findByText("布局已保存")).toBeVisible();
});

test("clears the drag session when the pointer is released outside the dashboard grid", async () => {
  const fetchMock = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
    const path = String(input);
    if (path === "/api/dashboards" && !init?.method) return json([twoColumnDashboard]);
    if (path === "/api/dashboards/d1/layout" && init?.method === "PATCH") return json(twoColumnDashboard);
    throw new Error(`Unexpected request: ${path}`);
  });
  vi.stubGlobal("fetch", fetchMock);

  renderWorkspace(<DashboardWorkspace />);
  const handle = await screen.findByRole("button", { name: "拖动卡片：左侧图表" });
  const rightCard = screen.getByRole("heading", { name: "右侧图表" }).closest("article")!;
  fireEvent.pointerDown(handle, { button: 0 });
  fireEvent.pointerUp(window);
  fireEvent.pointerUp(rightCard);

  expect(fetchMock).not.toHaveBeenCalledWith(
    "/api/dashboards/d1/layout",
    expect.objectContaining({ method: "PATCH" })
  );
});

test("reflows neighboring cards when a two-column card is enlarged", async () => {
  let current = twoColumnDashboard;
  let savedCards: Array<{ id: string; x: number; y: number; w: number; h: number }> = [];
  vi.stubGlobal("fetch", vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
    const path = String(input);
    if (path === "/api/dashboards" && !init?.method) return json([current]);
    if (path === "/api/dashboards/d1/layout" && init?.method === "PATCH") {
      savedCards = JSON.parse(String(init.body)).cards;
      current = {
        ...current,
        cards: current.cards.map((card) => {
          const next = savedCards.find((item) => item.id === card.id);
          return next ? { ...card, layout: { x: next.x, y: next.y, w: next.w, h: next.h } } : card;
        })
      };
      return json(current);
    }
    throw new Error(`Unexpected request: ${path}`);
  }));

  renderWorkspace(<DashboardWorkspace />);
  const leftCard = (await screen.findByRole("heading", { name: "左侧图表" })).closest("article")!;
  await userEvent.click(within(leftCard).getByRole("button", { name: "放大卡片" }));

  await waitFor(() => expect(savedCards).toEqual(expect.arrayContaining([
    { id: "card-1", x: 0, y: 0, w: 9, h: 5 },
    { id: "card-2", x: 0, y: 8, w: 6, h: 4 }
  ])));
});
