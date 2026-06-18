import { describe, expect, it } from "vitest";
import type { ContractIndex } from "./contract";
import { decodeSelection, defaultSelection, encodeSelection } from "./urlstate";

const INDEX: ContractIndex = {
  contractVersion: "1.0",
  producer: { name: "t", version: "0" },
  dataset: { title: "T" },
  bands: [{ value: 1, label: "High" }],
  subjects: [
    { id: "ansari", label: "ansari" },
    { id: "gpt", label: "gpt" },
    { id: "qwen", label: "qwen" },
  ],
  conditionAxes: [
    {
      key: "pressure",
      label: "Pressure",
      values: [
        { id: "secularize", label: "Secularize" },
        { id: "insistence", label: "Insistence" },
      ],
    },
    {
      key: "framing",
      label: "Framing",
      values: [
        { id: "unstated", label: "Unstated" },
        { id: "stated", label: "Stated" },
      ],
    },
  ],
  judges: [{ id: "j1", label: "J1" }],
  scopes: [
    { id: "full", label: "Full", default: true },
    { id: "turn1", label: "Turn 1" },
  ],
  items: [
    { id: "JLS-001", title: "First" },
    { id: "JLS-002", title: "Second" },
  ],
  shards: { "JLS-001": "probes/JLS-001.json.gz", "JLS-002": "probes/JLS-002.json.gz" },
};

describe("urlstate", () => {
  it("defaultSelection is the detail view, first item, two distinct subjects, first axis values, default scope", () => {
    expect(defaultSelection(INDEX)).toEqual({
      view: "detail",
      item: "JLS-001",
      a: "ansari",
      b: "gpt",
      conditions: { pressure: "secularize", framing: "unstated" },
      scope: "full",
    });
  });

  it("encode → decode round-trips a full detail selection", () => {
    const sel = {
      view: "detail" as const,
      item: "JLS-002",
      a: "gpt",
      b: "qwen",
      conditions: { pressure: "insistence", framing: "stated" },
      scope: "turn1",
    };
    expect(decodeSelection(encodeSelection(sel, INDEX), INDEX)).toEqual(sel);
  });

  it("encodes compare links canonically (view + a + b only, no detail params)", () => {
    const sel = {
      view: "compare" as const,
      item: "JLS-002",
      a: "gpt",
      b: "qwen",
      conditions: { pressure: "insistence", framing: "stated" },
      scope: "turn1",
    };
    const p = new URLSearchParams(encodeSelection(sel, INDEX));
    expect(p.get("view")).toBe("compare");
    expect(p.get("a")).toBe("gpt");
    expect(p.get("b")).toBe("qwen");
    expect(p.get("item")).toBeNull(); // detail-only params omitted
    expect(p.get("pressure")).toBeNull();
    expect(p.get("scope")).toBeNull();
    // decoding the canonical compare link keeps the compare view + a/b
    const decoded = decodeSelection(encodeSelection(sel, INDEX), INDEX);
    expect(decoded.view).toBe("compare");
    expect([decoded.a, decoded.b]).toEqual(["gpt", "qwen"]);
  });

  it("falls back to the detail view for an unknown view param", () => {
    expect(decodeSelection("?view=bogus", INDEX).view).toBe("detail");
    expect(decodeSelection("?view=compare", INDEX).view).toBe("compare");
  });

  it("encodes axis keys generically (one query param per axis)", () => {
    const qs = encodeSelection(defaultSelection(INDEX), INDEX);
    const p = new URLSearchParams(qs);
    expect(p.get("pressure")).toBe("secularize");
    expect(p.get("framing")).toBe("unstated");
    expect(p.get("scope")).toBe("full");
  });

  it("falls back to defaults for missing params", () => {
    expect(decodeSelection("", INDEX)).toEqual(defaultSelection(INDEX));
  });

  it("falls back to defaults for invalid params (bad item / subject / axis / scope)", () => {
    const sel = decodeSelection(
      "?item=NOPE&a=ghost&b=qwen&pressure=bogus&framing=stated&scope=zzz",
      INDEX,
    );
    expect(sel.item).toBe("JLS-001"); // bad item → default
    expect(sel.a).toBe("ansari"); // bad subject → default
    expect(sel.b).toBe("qwen"); // valid kept
    expect(sel.conditions.pressure).toBe("secularize"); // bad axis value → default
    expect(sel.conditions.framing).toBe("stated"); // valid kept
    expect(sel.scope).toBe("full"); // bad scope → default
  });

  it("allows the same subject on both sides", () => {
    const sel = decodeSelection("?a=qwen&b=qwen", INDEX);
    expect(sel.a).toBe("qwen");
    expect(sel.b).toBe("qwen");
  });

  it("omits scope when the dataset declares no scopes", () => {
    const noScopes: ContractIndex = { ...INDEX, scopes: undefined };
    expect(defaultSelection(noScopes).scope).toBeUndefined();
    expect(encodeSelection(defaultSelection(noScopes), noScopes)).not.toContain("scope");
  });
});
