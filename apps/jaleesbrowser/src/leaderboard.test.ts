import { describe, expect, it } from "vitest";
import type { ContractIndex } from "./contract";
import { breakdownAxis, computeLeaderboard } from "./leaderboard";

// 2 subjects × 1 item × 3 pressures × 2 framings × 2 scopes (full is default).
// Flat row-major, scope fastest: [full, turn1] per (framing) per (pressure).
//
// A: post f1 = 0.0, post f2 = 1.0 (→ post overall 0.5); turn1 all 0.8.
// B: post all 0.4; turn1 all 0.2.
// Canonical rank is by the FIRST framing value's post score (f1): B (0.4) beats
// A (0.0) even though A's overall post (0.5) beats B's (0.4).
const perPressure = (f1: number[], f2: number[]) => [...f1, ...f2];
const subjectData = (f1full: number, f2full: number, turn1: number) => [
  ...perPressure([f1full, turn1], [f2full, turn1]),
  ...perPressure([f1full, turn1], [f2full, turn1]),
  ...perPressure([f1full, turn1], [f2full, turn1]),
];

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
    {
      key: "pressure",
      label: "P",
      values: [
        { id: "p1", label: "P1" },
        { id: "p2", label: "P2" },
        { id: "p3", label: "P3" },
      ],
    },
    {
      key: "framing",
      label: "F",
      values: [
        { id: "f1", label: "F1" },
        { id: "f2", label: "F2" },
      ],
    },
  ],
  judges: [{ id: "j", label: "J" }],
  scopes: [
    { id: "full", label: "post", default: true },
    { id: "turn1", label: "initial" },
  ],
  items: [{ id: "JLS-001", title: "First" }],
  shards: {},
  scores: {
    order: ["subject", "item", "pressure", "framing", "scope"],
    shape: [2, 1, 3, 2, 2],
    data: [...subjectData(0.0, 1.0, 0.8), ...subjectData(0.4, 0.4, 0.2)],
  },
};

describe("breakdownAxis", () => {
  it("picks the axis with the fewest values", () => {
    expect(breakdownAxis(INDEX)?.key).toBe("framing");
  });

  it("is null when there are no axes", () => {
    expect(breakdownAxis({ ...INDEX, conditionAxes: [] })).toBeNull();
  });
});

describe("computeLeaderboard", () => {
  it("computes per-scope means, delta, and per-breakdown-value means", () => {
    const rows = computeLeaderboard(INDEX);
    const a = rows.find((r) => r.subject === "A")!;
    expect(a.initial).toBeCloseTo(0.8);
    expect(a.post).toBeCloseTo(0.5);
    expect(a.delta).toBeCloseTo(-0.3);
    expect(a.byValue.map((v) => v!)).toEqual([0.0, 1.0]);
    const b = rows.find((r) => r.subject === "B")!;
    expect(b.initial).toBeCloseTo(0.2);
    expect(b.post).toBeCloseTo(0.4);
    expect(b.delta).toBeCloseTo(0.2);
  });

  it("ranks by the first breakdown value at the post scope, not the overall post mean", () => {
    const rows = computeLeaderboard(INDEX);
    expect(rows.map((r) => r.subject)).toEqual(["B", "A"]);
  });

  it("excludes absent cells from every mean", () => {
    // Null out A's (p1, f2) post cell: offset 0*12 + 0*4 + 1*2 + 0 = 2.
    const data = [...INDEX.scores!.data];
    data[2] = null;
    const rows = computeLeaderboard({ ...INDEX, scores: { ...INDEX.scores!, data } });
    const a = rows.find((r) => r.subject === "A")!;
    // f2 post is now the mean of two cells (both 1.0); overall post of 5 cells.
    expect(a.byValue[1]).toBeCloseTo(1.0);
    expect(a.post).toBeCloseTo((0 + 0 + 0 + 1 + 1) / 5);
  });

  it("returns empty when there is no score blob", () => {
    expect(computeLeaderboard({ ...INDEX, scores: undefined })).toEqual([]);
  });
});
