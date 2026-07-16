import { describe, expect, test } from "vitest";
import { filterDashboardCards } from "../utils/dashboardFilters";
import type { DashboardCard } from "../types";

const card: DashboardCard = {
  id: "card-1",
  title: "房价趋势",
  analysis_id: "a1",
  chart: { type: "line", x_field: "month", y_fields: ["avg_price"], title: "房价趋势" },
  datasets: [{
    source: "demo",
    table: "house_price_monthly",
    tables: ["house_price_monthly"],
    updated_at: "2026-07-14T00:00:00+08:00",
    confidence: 0.96,
    fields: ["month", "district", "avg_price", "rent_price"],
    rows: [
      { month: "2024-01", district: "海淀区", avg_price: 98000, rent_price: 120 },
      { month: "2025-01", district: "海淀区", avg_price: 101200, rent_price: 125 },
      { month: "2025-01", district: "朝阳区", avg_price: 78300, rent_price: 108 }
    ]
  }],
  layout: { x: 0, y: 0, w: 6, h: 4 }
};

describe("filterDashboardCards", () => {
  test("filters saved dashboard card datasets by year, district, and metric", () => {
    const [filtered] = filterDashboardCards([card], {
      year: "2025",
      district: "海淀区",
      metric: "rent_price"
    });

    expect(filtered.datasets[0].rows).toEqual([
      { month: "2025-01", district: "海淀区", rent_price: 125 }
    ]);
    expect(filtered.datasets[0].fields).toEqual(["month", "district", "rent_price"]);
    expect(filtered.chart.y_fields).toEqual(["rent_price"]);
  });
});
