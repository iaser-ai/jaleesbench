/**
 * Leaderboard rows, computed IN-APP from the index's score blob (no re-export,
 * same precedent as guided.ts). Generic over the contract: the overall columns
 * are means of cell means at each scope, and the breakdown columns split the
 * post-stage score by the values of ONE condition axis — the axis with the
 * fewest values (the summary-most one; for JaleesBench that is `framing`).
 *
 * Rows come back in the canonical order: the first declared value of the
 * breakdown axis at the default (post) scope, descending — for JaleesBench
 * that is the Unstated post-pressure score, the paper's published ordering.
 *
 * Scale note: the blob is already on the display scale (the exporter rescales
 * native −2…+2 judge bands by ×0.5), so a mean of cell means here reproduces
 * the exporter's `subjects[].overall` exactly.
 */

import type { ConditionAxis, ContractIndex } from "./contract";
import { defaultScopeId, scoreAt } from "./scores";

export interface LeaderboardRow {
  subject: string;
  label: string;
  /** First-stage (e.g. turn-1) mean across every cell, or null if absent. */
  initial: number | null;
  /** Default-scope (e.g. post-pressure) mean across every cell — the headline score. */
  post: number | null;
  /** post − initial: how far the subject moved between the two stages. */
  delta: number | null;
  /** Default-scope mean per breakdown-axis value, in the axis's declared order. */
  byValue: (number | null)[];
}

/** The breakdown axis: the one with the fewest values (first wins ties). */
export function breakdownAxis(index: ContractIndex): ConditionAxis | null {
  let best: ConditionAxis | null = null;
  for (const ax of index.conditionAxes) {
    if (!best || ax.values.length < best.values.length) best = ax;
  }
  return best;
}

/** Every condition tuple (one value per axis), in declared order. */
function conditionCombos(index: ContractIndex): Record<string, string>[] {
  let acc: Record<string, string>[] = [{}];
  for (const ax of index.conditionAxes) {
    acc = acc.flatMap((row) => ax.values.map((v) => ({ ...row, [ax.key]: v.id })));
  }
  return acc;
}

const mean = (xs: number[]): number | null =>
  xs.length ? xs.reduce((a, b) => a + b, 0) / xs.length : null;

/**
 * One row per subject, in canonical order (first breakdown value at the post
 * scope, descending; nulls last; ties by post, then label). Empty when the
 * index ships no score blob.
 */
export function computeLeaderboard(index: ContractIndex): LeaderboardRow[] {
  if (!index.scores) return [];
  const post = defaultScopeId(index);
  const initial = (index.scopes ?? []).find((s) => s.id !== post)?.id;
  const axis = breakdownAxis(index);
  const combos = conditionCombos(index);

  const rows = index.subjects.map((sub) => {
    const postAll: number[] = [];
    const initialAll: number[] = [];
    const perValue: number[][] = (axis?.values ?? []).map(() => []);
    for (const item of index.items) {
      for (const c of combos) {
        const vp = post ? scoreAt(index, sub.id, item.id, c, post) : null;
        if (vp !== null) {
          postAll.push(vp);
          if (axis) {
            const vi = axis.values.findIndex((v) => v.id === c[axis.key]);
            if (vi >= 0) perValue[vi].push(vp);
          }
        }
        const v1 = initial ? scoreAt(index, sub.id, item.id, c, initial) : null;
        if (v1 !== null) initialAll.push(v1);
      }
    }
    const p = mean(postAll);
    const i = mean(initialAll);
    return {
      subject: sub.id,
      label: sub.label,
      initial: i,
      post: p,
      delta: p !== null && i !== null ? p - i : null,
      byValue: perValue.map(mean),
    };
  });

  const rankScore = (r: LeaderboardRow) => r.byValue[0] ?? r.post;
  rows.sort((x, y) => {
    const rx = rankScore(x);
    const ry = rankScore(y);
    if (rx === null || ry === null) return rx === null ? (ry === null ? 0 : 1) : -1;
    if (rx !== ry) return ry - rx;
    if (x.post !== y.post) return (y.post ?? -Infinity) - (x.post ?? -Infinity);
    return x.label < y.label ? -1 : x.label > y.label ? 1 : 0;
  });
  return rows;
}
