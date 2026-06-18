/**
 * Pure helpers for rendering cells and bands. Generic over the contract — no
 * JaleesBench-specific values.
 */

import type { Cell, ContractIndex, ItemShard } from "./contract";

/** Low → high fallback ramp (red → grey → green) when a band has no `color`. */
const FALLBACK_RAMP = ["#a02020", "#c2603a", "#888888", "#5a9e6f", "#1a6840"];

/** Bands sorted ascending by value. */
export function sortedBands(index: ContractIndex) {
  return [...index.bands].sort((x, y) => x.value - y.value);
}

/** A band's color: the producer-supplied `color`, else a positional fallback. */
export function bandColor(index: ContractIndex, value: number): string {
  const explicit = index.bands.find((b) => b.value === value)?.color;
  if (explicit) return explicit;
  const sorted = sortedBands(index);
  const i = sorted.findIndex((b) => b.value === value);
  if (i < 0 || sorted.length === 0) return "#888888";
  if (sorted.length === 1) return FALLBACK_RAMP[2];
  const pos = i / (sorted.length - 1); // 0..1
  return FALLBACK_RAMP[Math.round(pos * (FALLBACK_RAMP.length - 1))];
}

/** A signed display string for a band value, e.g. +0.5 / -1 / 0. */
export function signed(value: number): string {
  return value > 0 ? `+${value}` : `${value}`;
}

/** Canonical key for a cell: subject + each axis value, in the contract's axis order. */
export function cellKey(
  subject: string,
  conditions: Record<string, string>,
  axisKeys: string[],
): string {
  return [subject, ...axisKeys.map((k) => conditions[k] ?? "")].join("|");
}

/** Mean of a cell's judge bands at one scope (display scale), or null if none. */
export function meanBandAtScope(cell: Cell, scope: string): number | null {
  const bands = cell.verdicts.filter((v) => v.scope === scope).map((v) => v.band);
  return bands.length ? bands.reduce((a, b) => a + b, 0) / bands.length : null;
}

/** Index a shard's cells by (subject, conditions) for O(1) lookup. */
export function indexCells(shard: ItemShard, axisKeys: string[]): Map<string, Cell> {
  const map = new Map<string, Cell>();
  for (const cell of shard.cells) {
    map.set(cellKey(cell.subject, cell.conditions, axisKeys), cell);
  }
  return map;
}
