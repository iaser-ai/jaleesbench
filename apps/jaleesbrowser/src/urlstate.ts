/**
 * Selection <-> URL query-string mapping. Generic over the contract: the
 * condition axes are read from `index.conditionAxes`, so there are no hardcoded
 * "pressure"/"framing" keys here. Decoding is fail-soft — any missing or invalid
 * parameter falls back to a sensible default, never throwing.
 *
 * There is no manual "view" — the surface is derived from `item`: when a cell is
 * open (`item` set) the app shows the drill-in detail; otherwise it shows the
 * A-vs-B divergence list. `a`/`b`/`scope` are the persistent top controls.
 */

import type { ContractIndex } from "./contract";

export interface Selection {
  /** subject id, left column */
  a: string;
  /** subject id, right column */
  b: string;
  /** axisKey -> valueId; defaulted, used when a cell is open */
  conditions: Record<string, string>;
  /** verdict scope id (omitted when the dataset declares no scopes) */
  scope?: string;
  /** the open cell's item id; unset → the divergence list is shown */
  item?: string;
}

/** True when a cell/detail is open (an item is selected). */
export function isDetail(sel: Selection): boolean {
  return sel.item !== undefined;
}

function hasId(arr: { id: string }[] | undefined, id: string | null): id is string {
  return id !== null && !!arr?.some((x) => x.id === id);
}

/** First two distinct subjects, each axis's first value, default scope, NO open
 *  cell (so the landing shows the divergence list). */
export function defaultSelection(index: ContractIndex): Selection {
  const conditions: Record<string, string> = {};
  for (const axis of index.conditionAxes) {
    const first = axis.values[0];
    if (first) conditions[axis.key] = first.id;
  }
  const scopes = index.scopes ?? [];
  const scope = (scopes.find((s) => s.default) ?? scopes[0])?.id;
  return {
    a: index.subjects[0]?.id ?? "",
    b: (index.subjects[1] ?? index.subjects[0])?.id ?? "",
    conditions,
    ...(scope !== undefined ? { scope } : {}),
  };
}

/** Parse a query string into a fully-valid Selection, defaulting anything invalid. */
export function decodeSelection(search: string, index: ContractIndex): Selection {
  const params = new URLSearchParams(search);
  const def = defaultSelection(index);

  const conditions: Record<string, string> = {};
  for (const axis of index.conditionAxes) {
    const v = params.get(axis.key);
    conditions[axis.key] = hasId(axis.values, v) ? v : def.conditions[axis.key];
  }

  const a = params.get("a");
  const b = params.get("b");
  const scope = params.get("scope");
  const item = params.get("item");

  return {
    a: hasId(index.subjects, a) ? a : def.a,
    b: hasId(index.subjects, b) ? b : def.b,
    conditions,
    ...(def.scope !== undefined
      ? { scope: hasId(index.scopes, scope) ? scope : def.scope }
      : {}),
    ...(hasId(index.items, item) ? { item } : {}),
  };
}

/**
 * Encode a Selection as a `?…` query string. The list always carries `a`/`b`/
 * `scope`; when a cell is open it also carries `item` + the condition axes.
 */
export function encodeSelection(sel: Selection, index: ContractIndex): string {
  const params = new URLSearchParams();
  params.set("a", sel.a);
  params.set("b", sel.b);
  if (sel.scope !== undefined) params.set("scope", sel.scope);
  if (sel.item !== undefined) {
    params.set("item", sel.item);
    for (const axis of index.conditionAxes) {
      const v = sel.conditions[axis.key];
      if (v !== undefined) params.set(axis.key, v);
    }
  }
  return `?${params.toString()}`;
}
