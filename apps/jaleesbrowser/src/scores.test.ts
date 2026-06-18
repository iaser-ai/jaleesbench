import { describe, expect, it } from "vitest";
import type { ContractIndex } from "./contract";
import { divergenceRanking, scoreAt, subjectStats } from "./scores";

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

  it("breaks |Δ| ties by declared axis-value order, not lexically", () => {
    // pressure declared order is [b, a] (NON-lexical). Two cells with equal Δ=2;
    // the one with pressure "b" must rank first (declared order), not "a".
    const tied: ContractIndex = {
      ...INDEX,
      conditionAxes: [
        {
          key: "pressure",
          label: "P",
          values: [
            { id: "b", label: "B" },
            { id: "a", label: "A" },
          ],
        },
        { key: "framing", label: "F", values: [{ id: "u", label: "U" }] },
      ],
      items: [{ id: "JLS-001", title: "First" }],
      // shape [subject2, item1, pressure2, framing1, scope1]; A=+1 both, B=-1 both.
      scores: {
        order: ["subject", "item", "pressure", "framing", "scope"],
        shape: [2, 1, 2, 1, 1],
        data: [1, 1, -1, -1],
      },
    };
    const rows = divergenceRanking(tied, "A", "B");
    expect(rows.map((r) => r.conditions.pressure)).toEqual(["b", "a"]);
  });
});

describe("subjectStats", () => {
  // 2 subjects × 1 item × 1 pressure × 2 framings × 2 scopes.
  const SINDEX: ContractIndex = {
    contractVersion: "1.0",
    producer: { name: "t", version: "0" },
    dataset: { title: "T" },
    bands: [{ value: 1, label: "High" }],
    subjects: [
      { id: "a", label: "a" },
      { id: "b", label: "b" },
    ],
    conditionAxes: [
      { key: "pressure", label: "Pressure", values: [{ id: "x", label: "X" }] },
      {
        key: "framing",
        label: "Framing",
        values: [
          { id: "u", label: "U" },
          { id: "s", label: "S" },
        ],
      },
    ],
    judges: [{ id: "j", label: "J" }],
    scopes: [
      { id: "full", label: "after", default: true },
      { id: "turn1", label: "pre" },
    ],
    items: [{ id: "JLS-001", title: "First" }],
    shards: {},
    // order subject,item,pressure,framing,scope:
    // a: u/full 0.4, u/turn1 0.8, s/full 1.0, s/turn1 0.8 ; b: -1,-0.5,-0.5,-0.5
    scores: {
      order: ["subject", "item", "pressure", "framing", "scope"],
      shape: [2, 1, 1, 2, 2],
      data: [0.4, 0.8, 1.0, 0.8, -1, -0.5, -0.5, -0.5],
    },
  };

  it("computes overall, recognition, steadfastness, and per-axis breakdowns", () => {
    const s = subjectStats(SINDEX, "a");
    expect(s.overall).toBeCloseTo(0.7); // (0.4 + 1.0)/2 at full
    expect(s.recognition).toBeCloseTo(0.6); // s.full(1.0) − u.full(0.4)
    expect(s.steadfastness).toBeCloseTo(-0.1); // full mean 0.7 − turn1 mean 0.8
    const framing = s.byAxis.find((ax) => ax.key === "framing");
    expect(framing?.values.map((v) => v.mean)).toEqual([0.4, 1.0]); // U, S at full
    const pressure = s.byAxis.find((ax) => ax.key === "pressure");
    expect(pressure?.values[0].mean).toBeCloseTo(0.7); // X = mean over framings at full
  });
});
