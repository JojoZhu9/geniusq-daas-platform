import type { ChartSpec, Dataset } from "../../types";

export type ChartSeries = { name: string; data: number[] };

function unique(values: string[]) {
  return [...new Set(values)];
}

export function buildSeries(chart: ChartSpec, datasets: Dataset[]) {
  const rows = datasets.flatMap((dataset) => dataset.rows);
  const districts = unique(rows.map((row) => String(row.district ?? "")).filter(Boolean));
  const groupByDistrict = chart.x_field !== "district"
    && chart.y_fields.length === 1
    && districts.length > 1;

  if (groupByDistrict) {
    const categories = unique(rows.map((row) => String(row[chart.x_field] ?? "")));
    const valueField = chart.y_fields[0];
    const series = districts.map((district) => ({
      name: district,
      data: categories.map((category) => {
        const row = rows.find((item) => String(item.district) === district
          && String(item[chart.x_field]) === category);
        return Number(row?.[valueField] ?? 0);
      })
    }));
    return { categories, series, rows };
  }

  const rowsByCategory = new Map<string, Record<string, string | number>>();
  for (const row of rows) {
    const category = String(row[chart.x_field] ?? "");
    rowsByCategory.set(category, { ...(rowsByCategory.get(category) ?? {}), ...row });
  }
  const categories = [...rowsByCategory.keys()];
  const series = chart.y_fields.map((field) => ({
    name: field,
    data: categories.map((category) => Number(rowsByCategory.get(category)?.[field] ?? 0))
  }));
  return { categories, series, rows };
}
