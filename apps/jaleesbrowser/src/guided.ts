/**
 * The guided example lists, computed IN-APP from the score blob (no re-export):
 *  1. Models split — biggest first-stage (turn-1) divergence from the strongest model;
 *  2. Judges differed — which cells/model are flagged by the export (this needs the
 *     per-judge band values, which aren't in the score blob), reused here;
 *  3. Biggest pressure flips — biggest move from the first response to post-pressure.
 *
 * Only list (1) is a genuine A-vs-B contrast: there model B is the strongest model
 * overall (highest total score across the initial and post stages). Lists (2) and
 * (3) are about a SINGLE model's behaviour, so they open in the single-model view
 * (model B = "" / none) — pitting them against the strongest model added nothing.
 */
import type { ContractIndex } from "./contract";
import { defaultScopeId, scoreAt } from "./scores";

export interface GuidedEntry {
  label: string;
  params: Record<string, string>;
}
export interface GuidedList {
  key: string;
  label: string;
  description?: string;
  entries: GuidedEntry[];
}

/** Every condition tuple (one value per axis), in declared order. */
function conditionCombos(index: ContractIndex): Record<string, string>[] {
  let acc: Record<string, string>[] = [{}];
  for (const ax of index.conditionAxes) {
    acc = acc.flatMap((row) => ax.values.map((v) => ({ ...row, [ax.key]: v.id })));
  }
  return acc;
}

function subjLabel(index: ContractIndex, id: string): string {
  return index.subjects.find((s) => s.id === id)?.label ?? id;
}

function pickPerItem<T extends { item: string }>(rows: T[], n: number): T[] {
  const out: T[] = [];
  const seen = new Set<string>();
  for (const r of rows) {
    if (seen.has(r.item)) continue;
    seen.add(r.item);
    out.push(r);
    if (out.length >= n) break;
  }
  return out;
}

export function computeGuided(index: ContractIndex): GuidedList[] {
  if (!index.scores) return [];
  const post = defaultScopeId(index);
  const initial = (index.scopes ?? []).find((s) => s.id !== post)?.id;
  const subjects = index.subjects.map((s) => s.id);
  const combos = conditionCombos(index);

  // Strongest model overall: highest total of (initial + post) across all cells.
  let best = subjects[0];
  let bestTotal = Number.NEGATIVE_INFINITY;
  for (const sub of subjects) {
    let total = 0;
    for (const item of index.items) {
      for (const c of combos) {
        const vi = initial ? scoreAt(index, sub, item.id, c, initial) : null;
        const vp = post ? scoreAt(index, sub, item.id, c, post) : null;
        if (vi !== null) total += vi;
        if (vp !== null) total += vp;
      }
    }
    if (total > bestTotal) {
      bestTotal = total;
      best = sub;
    }
  }

  const mkParams = (item: string, a: string, c: Record<string, string>): Record<string, string> => ({
    item,
    a,
    b: best,
    ...c,
  });

  // Single-model view: b="" is the explicit "none" sentinel (see urlstate).
  const mkSingle = (item: string, a: string, c: Record<string, string>): Record<string, string> => ({
    item,
    a,
    b: "",
    ...c,
  });

  // (1) Models split — biggest first-stage divergence from the strongest model.
  const splits: { item: string; c: Record<string, string>; a: string; gap: number }[] = [];
  if (initial) {
    for (const item of index.items) {
      for (const c of combos) {
        const sb = scoreAt(index, best, item.id, c, initial);
        if (sb === null) continue;
        let a = "";
        let gap = -1;
        for (const sub of subjects) {
          if (sub === best) continue;
          const sa = scoreAt(index, sub, item.id, c, initial);
          if (sa === null) continue;
          const g = Math.abs(sa - sb);
          if (g > gap) {
            gap = g;
            a = sub;
          }
        }
        if (a) splits.push({ item: item.id, c, a, gap });
      }
    }
  }
  splits.sort((x, y) => y.gap - x.gap || (x.item < y.item ? -1 : 1));
  const splitEntries = pickPerItem(splits, 12).map((r) => ({
    label: `${r.item} · ${subjLabel(index, r.a)} vs ${subjLabel(index, best)}`,
    params: mkParams(r.item, r.a, r.c),
  }));

  // (3) Biggest pressure flips — biggest |post − initial| move. Single-model view,
  // so every model is eligible (no model is reserved as an alternative).
  const flips: { item: string; c: Record<string, string>; a: string; mag: number }[] = [];
  if (initial && post) {
    for (const item of index.items) {
      for (const c of combos) {
        let a = "";
        let mag = -1;
        for (const sub of subjects) {
          const vi = scoreAt(index, sub, item.id, c, initial);
          const vp = scoreAt(index, sub, item.id, c, post);
          if (vi === null || vp === null) continue;
          const m = Math.abs(vp - vi);
          if (m > mag) {
            mag = m;
            a = sub;
          }
        }
        if (a) flips.push({ item: item.id, c, a, mag });
      }
    }
  }
  flips.sort((x, y) => y.mag - x.mag || (x.item < y.item ? -1 : 1));
  const flipEntries = pickPerItem(flips, 12).map((r) => ({
    label: `${r.item} · ${subjLabel(index, r.a)} moved ${r.mag.toFixed(1)}`,
    params: mkSingle(r.item, r.a, r.c),
  }));

  // (2) Judges differed — cells/model from the export (needs per-judge data); kept,
  // but shown single-model (b="") since it's about one model's split, not a contrast.
  const baked = (index.presets ?? []).find((p) => /judg/i.test(p.key));
  const judgeEntries = (baked?.entries ?? []).map((e) => ({
    label: e.label,
    params: { ...e.params, b: "" },
  }));

  const lists: GuidedList[] = [
    { key: "split", label: "Models split (first response)", entries: splitEntries },
    { key: "judges", label: "Judges differed", entries: judgeEntries },
    { key: "flips", label: "Biggest pressure flips", entries: flipEntries },
  ];
  return lists.filter((l) => l.entries.length > 0);
}
