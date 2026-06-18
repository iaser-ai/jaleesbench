/**
 * Selection <-> URL query-string mapping. Generic over the contract: the
 * condition axes are read from `index.conditionAxes`, so there are no hardcoded
 * "pressure"/"framing" keys here. Decoding is fail-soft — any missing or invalid
 * parameter falls back to a sensible default, never throwing.
 */

import type { ContractIndex } from "./contract";

export type View = "detail" | "compare";
const VIEWS: View[] = ["detail", "compare"];

export interface Selection {
  /** which surface: the drill-in detail, or the A-vs-B compare ranking */
  view: View;
  /** item (probe) id */
  item: string;
  /** subject id, left column */
  a: string;
  /** subject id, right column; "" means none → single-model view (no side-by-side) */
  b: string;
  /** axisKey -> valueId, one entry per conditionAxis */
  conditions: Record<string, string>;
  /** verdict scope id (omitted when the dataset declares no scopes) */
  scope?: string;
}

function hasId(arr: { id: string }[] | undefined, id: string | null): id is string {
  return id !== null && !!arr?.some((x) => x.id === id);
}

/** First item, first two *distinct* subjects, each axis's first value, default scope. */
export function defaultSelection(index: ContractIndex): Selection {
  const conditions: Record<string, string> = {};
  for (const axis of index.conditionAxes) {
    const first = axis.values[0];
    if (first) conditions[axis.key] = first.id;
  }
  const scopes = index.scopes ?? [];
  const scope = (scopes.find((s) => s.default) ?? scopes[0])?.id;
  return {
    view: "detail",
    item: index.items[0]?.id ?? "",
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

  const item = params.get("item");
  const a = params.get("a");
  const b = params.get("b");
  const scope = params.get("scope");
  const view = params.get("view");

  return {
    view: VIEWS.includes(view as View) ? (view as View) : def.view,
    item: hasId(index.items, item) ? item : def.item,
    a: hasId(index.subjects, a) ? a : def.a,
    // An explicit empty `b` (`?b=`) is the "none" sentinel → single-model view.
    // Absent `b` falls back to the default second model (side-by-side).
    b: b === "" ? "" : hasId(index.subjects, b) ? b : def.b,
    conditions,
    ...(def.scope !== undefined
      ? { scope: hasId(index.scopes, scope) ? scope : def.scope }
      : {}),
  };
}

/**
 * Encode a Selection as a `?…` query string — **per-view**: compare links are
 * canonical (`view`, `a`, `b` only), while detail links also carry the item,
 * condition axes, and scope. Axis keys come from the contract.
 */
export function encodeSelection(sel: Selection, index: ContractIndex): string {
  const params = new URLSearchParams();
  params.set("view", sel.view);
  params.set("a", sel.a);
  params.set("b", sel.b);
  if (sel.view === "detail") {
    params.set("item", sel.item);
    for (const axis of index.conditionAxes) {
      const v = sel.conditions[axis.key];
      if (v !== undefined) params.set(axis.key, v);
    }
    if (sel.scope !== undefined) params.set("scope", sel.scope);
  }
  return `?${params.toString()}`;
}
