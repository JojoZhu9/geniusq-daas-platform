import type { DashboardCard } from "../../types";

export type LayoutItem = DashboardCard["layout"] & { id: string };

export function layoutItem(card: DashboardCard, position: Partial<DashboardCard["layout"]> = {}): LayoutItem {
  return { id: card.id, ...card.layout, ...position };
}

export function isLegacySingleColumn(cards: DashboardCard[]) {
  if (cards.length < 2) return false;
  return cards.every((card) => card.layout.x === 0 && card.layout.w === 6);
}

export function compactIntoTwoColumns(cards: DashboardCard[]): LayoutItem[] {
  const result: LayoutItem[] = [];
  let y = 0;
  for (let index = 0; index < cards.length; index += 2) {
    const left = cards[index];
    const right = cards[index + 1];
    result.push(layoutItem(left, { x: 0, y }));
    if (right) result.push(layoutItem(right, { x: 6, y }));
    y += Math.max(left.layout.h, right?.layout.h ?? 0);
  }
  return result;
}

export function layoutsOverlap(left: DashboardCard["layout"], right: DashboardCard["layout"]) {
  return left.x < right.x + right.w
    && left.x + left.w > right.x
    && left.y < right.y + right.h
    && left.y + left.h > right.y;
}

export function dropTargetFromPointer(
  source: DashboardCard,
  bounds: DOMRect,
  clientX: number,
  clientY: number
): DashboardCard["layout"] {
  const relativeX = clientX - bounds.left;
  const relativeY = Math.max(0, clientY - bounds.top);
  const targetX = source.layout.w > 6
    ? (relativeX < bounds.width / 2 ? 0 : 12 - source.layout.w)
    : (relativeX < bounds.width / 2 ? 0 : 6);
  const targetY = Math.max(0, Math.floor(relativeY / 280) * 4);
  return { ...source.layout, x: targetX, y: targetY };
}

export function firstOpenPosition(card: DashboardCard, occupied: LayoutItem[]): LayoutItem {
  const rightX = Math.max(0, 12 - card.layout.w);
  const candidateXs = card.layout.w <= 6 ? [0, 6] : [0, rightX];
  for (let row = 0; row <= occupied.length * 3 + 3; row += 1) {
    for (const x of [...new Set(candidateXs)]) {
      const candidate = layoutItem(card, { x, y: row * 4 });
      if (!occupied.some((item) => layoutsOverlap(candidate, item))) return candidate;
    }
  }
  return layoutItem(card, { x: 0, y: (occupied.length + 1) * 4 });
}

export function reflowAroundCard(cards: DashboardCard[], fixed: LayoutItem): LayoutItem[] {
  const occupied = [fixed];
  const remaining = cards
    .filter((card) => card.id !== fixed.id)
    .sort((left, right) => left.layout.y - right.layout.y || left.layout.x - right.layout.x);
  for (const card of remaining) occupied.push(firstOpenPosition(card, occupied));
  return occupied;
}

