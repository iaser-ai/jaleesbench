import { describe, expect, it } from "vitest";
import type { ContractIndex } from "./contract";
import { decodeSelection, defaultSelection, encodeSelection, isDetail } from "./urlstate";

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
    { id: "full", label: "post-pressure", default: true },
    { id: "turn1", label: "initial" },
  ],
  items: [
    { id: "JLS-001", title: "First" },
    { id: "JLS-002", title: "Second" },
  ],
  shards: {},
};

describe("urlstate", () => {
  it("defaultSelection: two distinct subjects, first axis values, default scope, no open cell", () => {
    const s = defaultSelection(INDEX);
    expect(s).toEqual({
      a: "ansari",
      b: "gpt",
      conditions: { pressure: "secularize", framing: "unstated" },
      scope: "full",
    });
    expect(isDetail(s)).toBe(false);
  });

  it("encode → decode round-trips an open-cell (detail) selection", () => {
    const sel = {
      a: "gpt",
      b: "qwen",
      conditions: { pressure: "insistence", framing: "stated" },
      scope: "turn1",
      item: "JLS-002",
    };
    const decoded = decodeSelection(encodeSelection(sel, INDEX), INDEX);
    expect(decoded).toEqual(sel);
    expect(isDetail(decoded)).toBe(true);
  });

  it("list links carry a/b/scope but no item or conditions", () => {
    const p = new URLSearchParams(encodeSelection(defaultSelection(INDEX), INDEX));
    expect(p.get("a")).toBe("ansari");
    expect(p.get("b")).toBe("gpt");
    expect(p.get("scope")).toBe("full");
    expect(p.get("item")).toBeNull();
    expect(p.get("pressure")).toBeNull();
  });

  it("falls back to defaults for invalid params; an absent item → list", () => {
    const sel = decodeSelection("?a=ghost&b=qwen&pressure=bogus&item=NOPE", INDEX);
    expect(sel.a).toBe("ansari"); // bad subject → default
    expect(sel.b).toBe("qwen"); // valid kept
    expect(sel.conditions.pressure).toBe("secularize"); // bad axis → default
    expect(sel.item).toBeUndefined(); // bad item → list
    expect(isDetail(sel)).toBe(false);
  });

  it("allows the same subject on both sides", () => {
    const sel = decodeSelection("?a=qwen&b=qwen", INDEX);
    expect([sel.a, sel.b]).toEqual(["qwen", "qwen"]);
  });

  it("omits scope when the dataset declares no scopes", () => {
    const noScopes: ContractIndex = { ...INDEX, scopes: undefined };
    expect(defaultSelection(noScopes).scope).toBeUndefined();
    expect(encodeSelection(defaultSelection(noScopes), noScopes)).not.toContain("scope");
  });
});
