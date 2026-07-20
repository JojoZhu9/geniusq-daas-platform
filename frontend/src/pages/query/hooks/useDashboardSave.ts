import { api } from "../../../api/client";
import type { AnalysisResponse, ChartSpec, Dashboard } from "../../../types";

function nextDashboardCardLayout(cards: Dashboard["cards"]) {
  const width = 6;
  const height = 4;
  const overlaps = (x: number, y: number) => cards.some((card) => (
    x < card.layout.x + card.layout.w
    && x + width > card.layout.x
    && y < card.layout.y + card.layout.h
    && y + height > card.layout.y
  ));

  for (let row = 0; row <= cards.length; row += 1) {
    const y = row * height;
    for (const x of [0, 6]) {
      if (!overlaps(x, y)) return { x, y, w: width, h: height };
    }
  }
  return { x: 0, y: cards.length * height, w: width, h: height };
}

export function useDashboardSave(
  latest: AnalysisResponse | undefined,
  chartTypes: Record<string, ChartSpec["type"]>,
  onNotice: (notice: string) => void
) {
  return async function saveToDashboard() {
    if (!latest?.chart) return;
    const dashboards = await api.get<Dashboard[]>("/api/dashboards");
    const dashboard = dashboards[0] ?? await api.post<Dashboard>("/api/dashboards", { name: "房价分析看板" });
    await api.post(`/api/dashboards/${dashboard.id}/cards`, {
      title: latest.chart.title,
      analysis_id: latest.analysis_id,
      chart: {
        ...latest.chart,
        type: chartTypes[latest.analysis_id] ?? latest.chart.type
      },
      layout: nextDashboardCardLayout(dashboard.cards)
    });
    onNotice(`已加入“${dashboard.name}”`);
  };
}
