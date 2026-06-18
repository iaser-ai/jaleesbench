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

// Per-index coordinate maps (id -> position), built once so scoreAt is O(1) per
// dimension instead of an O(N) findIndex in the hot ranking/stats loops.
interface Coords {
  subject: Map<string, number>;
  item: Map<string, number>;
  scope: Map<string, number>;
  axis: Map<string, Map<string, number>>;
}
const coordCache = new WeakMap<ContractIndex, Coords>();
function coordsOf(index: ContractIndex): Coords {
  let c = coordCache.get(index);
  if (!c) {
    c = {
      subject: new Map(index.subjects.map((s, i) => [s.id, i])),
      item: new Map(index.items.map((it, i) => [it.id, i])),
      scope: new Map((index.scopes ?? []).map((s, i) => [s.id, i])),
      axis: new Map(
        index.conditionAxes.map((ax) => [
          ax.key,
          new Map(ax.values.map((v, i) => [v.id, i])),
        ]),
      ),
    };
    coordCache.set(index, c);
  }
  return c;
}

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
  const c = coordsOf(index);
  let offset = 0;
  for (let d = 0; d < sm.order.length; d++) {
    const dim = sm.order[d];
    let i: number | undefined;
    if (dim === "subject") i = c.subject.get(subject);
    else if (dim === "item") i = c.item.get(item);
    else if (dim === "scope") i = scope !== undefined ? c.scope.get(scope) : undefined;
    else i = c.axis.get(dim)?.get(conditions[dim]);
    if (i === undefined || i >= sm.shape[d]) return null;
    offset = offset * sm.shape[d] + i;
  }
  return sm.data[offset] ?? null;
}

/** Mean band for a subject over all cells matching `fixed` (axisKey→valueId), at
 *  `scope`; nulls excluded. Axes not in `fixed` are averaged over. */
export function sliceMean(
  index: ContractIndex,
  subject: string,
  scope: string | undefined,
  fixed: Record<string, string>,
): number | null {
  if (!index.scores) return null;
  const axes = index.conditionAxes;
  const valueLists = axes.map((ax) =>
    fixed[ax.key] !== undefined ? [fixed[ax.key]] : ax.values.map((v) => v.id),
  );
  const combos = cartesian(valueLists);
  let sum = 0;
  let n = 0;
  for (const item of index.items) {
    for (const combo of combos) {
      const cond: Record<string, string> = {};
      axes.forEach((ax, i) => {
        cond[ax.key] = combo[i];
      });
      const s = scoreAt(index, subject, item.id, cond, scope);
      if (s !== null) {
        sum += s;
        n += 1;
      }
    }
  }
  return n ? sum / n : null;
}

export interface AxisBreakdown {
  key: string;
  label: string;
  values: { id: string; label: string; mean: number | null }[];
}

export interface SubjectStats {
  /** mean band over all cells at the default scope */
  overall: number | null;
  /** post-pressure − initial (default scope − the other scope): steadfastness */
  steadfastness: number | null;
  /** recognition gain: 2nd − 1st value of the recognition axis at the default scope */
  recognition: number | null;
  /** the recognition axis label (for the recognition gain caption), if any */
  recognitionAxisLabel?: string;
  /** mean band per value, per condition axis (e.g. by pressure, by framing) */
  byAxis: AxisBreakdown[];
}

/** Per-model aggregate stats, computed client-side from the score blob (no new
 *  data). The recognition axis is taken to be the LAST condition axis (JaleesBench
 *  order: pressure, framing → framing), so recognition = mean(2nd value) −
 *  mean(1st value) of that axis at the default scope. */
export function subjectStats(index: ContractIndex, subject: string): SubjectStats {
  const def = defaultScopeId(index);
  const scopes = index.scopes ?? [];
  const other = scopes.find((s) => s.id !== def)?.id;

  const overall = sliceMean(index, subject, def, {});
  const post = overall;
  const initial = other ? sliceMean(index, subject, other, {}) : null;
  const steadfastness = post !== null && initial !== null ? post - initial : null;

  const byAxis: AxisBreakdown[] = index.conditionAxes.map((ax) => ({
    key: ax.key,
    label: ax.label,
    values: ax.values.map((v) => ({
      id: v.id,
      label: v.label,
      mean: sliceMean(index, subject, def, { [ax.key]: v.id }),
    })),
  }));

  const recAxis = index.conditionAxes[index.conditionAxes.length - 1];
  let recognition: number | null = null;
  if (recAxis && recAxis.values.length >= 2) {
    const base = sliceMean(index, subject, def, { [recAxis.key]: recAxis.values[0].id });
    const rec = sliceMean(index, subject, def, { [recAxis.key]: recAxis.values[1].id });
    recognition = base !== null && rec !== null ? rec - base : null;
  }

  return {
    overall,
    steadfastness,
    recognition,
    recognitionAxisLabel: recAxis?.label,
    byAxis,
  };
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
