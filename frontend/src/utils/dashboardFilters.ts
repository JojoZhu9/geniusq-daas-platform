import type { DashboardCard } from "../types";

export type DashboardFilters = {
  year?: string;
  district?: string;
  metric?: string;
};

function rowMatchesYear(row: Record<string, string | number>, year?: string) {
  if (!year) return true;
  const month = row.month == null ? "" : String(row.month);
  return month.startsWith(`${year}-`) || month === year;
}

function rowMatchesDistrict(row: Record<string, string | number>, district?: string) {
  if (!district) return true;
  return String(row.district ?? "") === district;
}

function visibleFields(fields: string[], metric?: string) {
  if (!metric) return fields;
  return fields.filter((field) => field === "month" || field === "district" || field === metric);
}

function trimRow(row: Record<string, string | number>, fields: string[]) {
  return Object.fromEntries(fields.map((field) => [field, row[field]]).filter(([, value]) => value != null));
}

export function filterDashboardCards(cards: DashboardCard[], filters: DashboardFilters): DashboardCard[] {
  return cards.map((card) => {
    const sourceDatasets = card.datasets ?? [];
    const metric = filters.metric && sourceDatasets.some((dataset) => dataset.fields.includes(filters.metric!))
      ? filters.metric
      : "";
    const datasets = sourceDatasets.map((dataset) => {
      const fields = visibleFields(dataset.fields, metric);
      const rows = dataset.rows
        .filter((row) => rowMatchesYear(row, filters.year))
        .filter((row) => rowMatchesDistrict(row, filters.district))
        .map((row) => trimRow(row, fields));
      return { ...dataset, fields, rows };
    });
    return {
      ...card,
      chart: metric ? { ...card.chart, y_fields: [metric] } : card.chart,
      datasets
    };
  });
}

export function dashboardFilterOptions(cards: DashboardCard[]) {
  const years = new Set<string>();
  const districts = new Set<string>();
  const metrics = new Set<string>();
  for (const card of cards) {
    for (const dataset of card.datasets ?? []) {
      for (const field of dataset.fields) {
        if (!["month", "district"].includes(field)) metrics.add(field);
      }
      for (const row of dataset.rows) {
        if (row.month != null) years.add(String(row.month).slice(0, 4));
        if (row.district != null) districts.add(String(row.district));
      }
    }
  }
  return {
    years: [...years].sort(),
    districts: [...districts].sort(),
    metrics: [...metrics].sort()
  };
}
