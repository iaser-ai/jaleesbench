import { describe, expect, it } from "vitest";
import type { ContractIndex } from "./contract";
import { divergenceRanking, scoreAt } from "./scores";

// 2 subjects × 2 items × 1 pressure × 1 framing × 1 scope. Flat row-major:
// [A/i1, A/i2, B/i1, B/i2]
const INDEX: ContractIndex = {
  contractVersion: "1.0",
  producer: { name: "t", version: "0" },
  dataset: { title: "T" },
  bands: [{ value: 1, label: "High" }],
  subjects: [
    { id: "A", label: "A" },
    { id: "B", label: "B" },
  ],
  conditionAxes: [
    { key: "pressure", label: "P", values: [{ id: "x", label: "X" }] },
    { key: "framing", label: "F", values: [{ id: "u", label: "U" }] },
  ],
  judges: [{ id: "j", label: "J" }],
  scopes: [{ id: "full", label: "after", default: true }],
  items: [
    { id: "JLS-001", title: "First" },
    { id: "JLS-002", title: "Second" },
  ],
  shards: {},
  scores: {
    order: ["subject", "item", "pressure", "framing", "scope"],
    shape: [2, 2, 1, 1, 1],
    // A/001=+1, A/002=null, B/001=-1, B/002=+0.5
    data: [1, null, -1, 0.5],
  },
};

describe("scoreAt", () => {
  it("reads the right cell by (subject, item, conditions, scope)", () => {
    expect(scoreAt(INDEX, "A", "JLS-001", { pressure: "x", framing: "u" }, "full")).toBe(1);
    expect(scoreAt(INDEX, "B", "JLS-001", { pressure: "x", framing: "u" }, "full")).toBe(-1);
    expect(scoreAt(INDEX, "B", "JLS-002", { pressure: "x", framing: "u" }, "full")).toBe(0.5);
  });

  it("returns null for an absent cell or unknown reference", () => {
    expect(scoreAt(INDEX, "A", "JLS-002", { pressure: "x", framing: "u" }, "full")).toBeNull();
    expect(scoreAt(INDEX, "ghost", "JLS-001", { pressure: "x", framing: "u" }, "full")).toBeNull();
  });
});

describe("divergenceRanking", () => {
  it("ranks cells by |score(A)−score(B)| desc, excluding cells null for either", () => {
    const rows = divergenceRanking(INDEX, "A", "B");
    // JLS-002 is null for A → excluded; only JLS-001 remains (|1 − (−1)| = 2).
    expect(rows).toHaveLength(1);
    expect(rows[0]).toMatchObject({ item: "JLS-001", scoreA: 1, scoreB: -1, delta: 2 });
  });

  it("returns empty when there is no score blob", () => {
    const noScores: ContractIndex = { ...INDEX, scores: undefined };
    expect(divergenceRanking(noScores, "A", "B")).toEqual([]);
  });
});
