import { describe, expect, it } from "vitest";
import type { ContractIndex } from "./contract";
import { breakdownAxis, computeLeaderboard } from "./leaderboard";

// 2 subjects × 1 item × 3 pressures × 2 framings × 2 scopes (full is default).
// Flat row-major, scope fastest: per pressure, [f1 full, f1 turn1, f2 full, f2 turn1].
//
// A: f1 post per pressure 0.0/0.6/−0.6 (mean 0.0), f1 turn1 all 0.8;
//    f2 post all 1.0, f2 turn1 all 0.2.
// B: f1 = f2, post all 0.4, turn1 all 0.2.
// The headline columns are the FIRST framing value (f1) only — pooling across
// framings would give A post 0.5 and initial 0.5 instead (issue #19).
const subjectData = (cells: [number, number, number, number][]) => cells.flat();

const A_CELLS: [number, number, number, number][] = [
  [0.0, 0.8, 1.0, 0.2],
  [0.6, 0.8, 1.0, 0.2],
  [-0.6, 0.8, 1.0, 0.2],
];
const B_CELLS: [number, number, number, number][] = [
  [0.4, 0.2, 0.4, 0.2],
  [0.4, 0.2, 0.4, 0.2],
  [0.4, 0.2, 0.4, 0.2],
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
    data: [...subjectData(A_CELLS), ...subjectData(B_CELLS)],
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
  it("restricts initial, post, and delta to the first breakdown value (no pooling)", () => {
    const rows = computeLeaderboard(INDEX);
    const a = rows.find((r) => r.subject === "A")!;
    // f1-only slice; pooling across framings would give initial 0.5 and post 0.5.
    expect(a.initial).toBeCloseTo(0.8);
    expect(a.post).toBeCloseTo(0.0);
    expect(a.delta).toBeCloseTo(-0.8);
    expect(a.byValue.map((v) => v!)).toEqual([0.0, 1.0]);
    expect(a.post).toBe(a.byValue[0]);
    const b = rows.find((r) => r.subject === "B")!;
    expect(b.initial).toBeCloseTo(0.2);
    expect(b.post).toBeCloseTo(0.4);
    expect(b.delta).toBeCloseTo(0.2);
  });

  it("ranks by the first breakdown value at the post scope", () => {
    // B's f1 post (0.4) beats A's (0.0) even though A's all-framings pooled
    // post mean (0.5) would beat B's (0.4).
    const rows = computeLeaderboard(INDEX);
    expect(rows.map((r) => r.subject)).toEqual(["B", "A"]);
  });

  it("pools every cell when there is no breakdown axis", () => {
    const noAxis: ContractIndex = {
      ...INDEX,
      conditionAxes: [],
      subjects: [{ id: "A", label: "A" }],
      items: [
        { id: "JLS-001", title: "First" },
        { id: "JLS-002", title: "Second" },
      ],
      scores: {
        order: ["subject", "item", "scope"],
        shape: [1, 2, 2],
        data: [0.2, 0.1, 0.4, 0.1],
      },
    };
    const rows = computeLeaderboard(noAxis);
    expect(rows[0].post).toBeCloseTo(0.3);
    expect(rows[0].initial).toBeCloseTo(0.1);
    expect(rows[0].delta).toBeCloseTo(0.2);
    expect(rows[0].byValue).toEqual([]);
  });

  it("excludes absent cells from every mean", () => {
    // Null out A's (p2, f1) post cell: offset ((0*3 + 1)*2 + 0)*2 + 0 = 4.
    // A's f1 post becomes mean(0.0, −0.6) = −0.3 (not −0.2, i.e. not null-as-0).
    const data = [...INDEX.scores!.data];
    data[4] = null;
    const rows = computeLeaderboard({ ...INDEX, scores: { ...INDEX.scores!, data } });
    const a = rows.find((r) => r.subject === "A")!;
    expect(a.post).toBeCloseTo(-0.3);
    expect(a.byValue[0]).toBeCloseTo(-0.3);
    expect(a.initial).toBeCloseTo(0.8);
    // Null out A's (p1, f2) post cell too: f2 post is the mean of the two left.
    data[2] = null;
    const rows2 = computeLeaderboard({ ...INDEX, scores: { ...INDEX.scores!, data } });
    const a2 = rows2.find((r) => r.subject === "A")!;
    expect(a2.byValue[1]).toBeCloseTo(1.0);
    expect(a2.post).toBeCloseTo(-0.3); // f2 cells never enter the headline mean
  });

  it("returns empty when there is no score blob", () => {
    expect(computeLeaderboard({ ...INDEX, scores: undefined })).toEqual([]);
  });
});
