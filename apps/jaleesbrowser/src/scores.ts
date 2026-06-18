/**
 * Reads the compact `scores` blob from `index.json` (a flat row-major tensor of
 * mean bands) and derives the compare-divergence ranking — all from the index, with
 * no shard loads. Generic over the contract: dimension order/lengths come from the
 * index's ordered lists (`scores.order` references "subject"/"item"/axis keys/"scope").
 */

import type { ContractIndex } from "./contract";

const cartesian = (lists: string[][]): string[][] =>
  lists.reduce<string[][]>(
    (acc, list) => acc.flatMap((row) => list.map((v) => [...row, v])),
    [[]],
  );

/** The mean band for one (subject, item, conditions, scope), or null if absent. */
export function scoreAt(
  index: ContractIndex,
  subject: string,
  item: string,
  conditions: Record<string, string>,
  scope: string | undefined,
): number | null {
  const sm = index.scores;
  if (!sm) return null;
  const coords: number[] = [];
  for (let d = 0; d < sm.order.length; d++) {
    const dim = sm.order[d];
    let i: number;
    if (dim === "subject") i = index.subjects.findIndex((s) => s.id === subject);
    else if (dim === "item") i = index.items.findIndex((it) => it.id === item);
    else if (dim === "scope") i = (index.scopes ?? []).findIndex((s) => s.id === scope);
    else {
      const axis = index.conditionAxes.find((a) => a.key === dim);
      i = axis ? axis.values.findIndex((v) => v.id === conditions[dim]) : -1;
    }
    if (i < 0 || i >= sm.shape[d]) return null;
    coords.push(i);
  }
  let offset = 0;
  for (let d = 0; d < coords.length; d++) offset = offset * sm.shape[d] + coords[d];
  return sm.data[offset] ?? null;
}

export interface DivergenceRow {
  item: string;
  conditions: Record<string, string>;
  scoreA: number;
  scoreB: number;
  delta: number; // scoreA - scoreB
}

/** The default scope id (or the first scope), used for the compare ranking. */
export function defaultScopeId(index: ContractIndex): string | undefined {
  const scopes = index.scopes ?? [];
  return (scopes.find((s) => s.default) ?? scopes[0])?.id;
}

/**
 * Every (item × condition-tuple) cell ranked by |score(A) − score(B)| descending at
 * the default scope. Cells null for either model are excluded. Deterministic
 * tie-break: item id, then each condition value in axis order.
 */
export function divergenceRanking(
  index: ContractIndex,
  a: string,
  b: string,
): DivergenceRow[] {
  if (!index.scores) return [];
  const scope = defaultScopeId(index);
  const axes = index.conditionAxes;
  const combos = cartesian(axes.map((ax) => ax.values.map((v) => v.id)));
  const rows: DivergenceRow[] = [];
  for (const item of index.items) {
    for (const combo of combos) {
      const conditions: Record<string, string> = {};
      axes.forEach((ax, i) => {
        conditions[ax.key] = combo[i];
      });
      const sa = scoreAt(index, a, item.id, conditions, scope);
      const sb = scoreAt(index, b, item.id, conditions, scope);
      if (sa === null || sb === null) continue;
      rows.push({ item: item.id, conditions, scoreA: sa, scoreB: sb, delta: sa - sb });
    }
  }
  rows.sort((x, y) => {
    const byDelta = Math.abs(y.delta) - Math.abs(x.delta);
    if (byDelta !== 0) return byDelta;
    if (x.item !== y.item) return x.item < y.item ? -1 : 1;
    // Tie-break by each axis value's position in its DECLARED order (not lexical).
    for (const ax of axes) {
      const xi = ax.values.findIndex((v) => v.id === x.conditions[ax.key]);
      const yi = ax.values.findIndex((v) => v.id === y.conditions[ax.key]);
      if (xi !== yi) return xi - yi;
    }
    return 0;
  });
  return rows;
}
