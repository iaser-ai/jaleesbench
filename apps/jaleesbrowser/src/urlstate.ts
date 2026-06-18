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
  /** subject id, right column; "" means none → single-model view (the default) */
  b: string;
  /** axisKey -> valueId, one entry per conditionAxis */
  conditions: Record<string, string>;
}

function hasId(arr: { id: string }[] | undefined, id: string | null): id is string {
  return id !== null && !!arr?.some((x) => x.id === id);
}

/** First item, first subject, single-model view (no model B), each axis's first value. */
export function defaultSelection(index: ContractIndex): Selection {
  const conditions: Record<string, string> = {};
  for (const axis of index.conditionAxes) {
    const first = axis.values[0];
    if (first) conditions[axis.key] = first.id;
  }
  return {
    view: "detail",
    item: index.items[0]?.id ?? "",
    a: index.subjects[0]?.id ?? "",
    // Default to the single-model view; choose a model B to opt into side-by-side.
    b: "",
    conditions,
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
  const view = params.get("view");

  return {
    view: VIEWS.includes(view as View) ? (view as View) : def.view,
    item: hasId(index.items, item) ? item : def.item,
    a: hasId(index.subjects, a) ? a : def.a,
    // `b` defaults to "" (single-model view); only a valid subject id opts into the
    // side-by-side comparison — so absent / empty / invalid `b` all stay single-model.
    b: hasId(index.subjects, b) ? b : def.b,
    conditions,
  };
}

/**
 * Encode a Selection as a `?…` query string — **per-view**: compare links are
 * canonical (`view`, `a`, `b` only), while detail links also carry the item and
 * condition axes. Axis keys come from the contract.
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
  }
  return `?${params.toString()}`;
}
