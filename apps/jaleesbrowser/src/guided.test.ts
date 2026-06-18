import { describe, expect, it } from "vitest";
import type { ContractIndex } from "./contract";
import { computeGuided } from "./guided";

// a: full 1 / turn1 0.5 (total 1.5) ; b: full -1 / turn1 -0.5 (total -1.5) → best = a.
const INDEX: ContractIndex = {
  contractVersion: "1.0",
  producer: { name: "t", version: "0" },
  dataset: { title: "T" },
  bands: [{ value: 1, label: "High" }],
  subjects: [
    { id: "a", label: "a" },
    { id: "b", label: "b" },
  ],
  conditionAxes: [
    { key: "pressure", label: "P", values: [{ id: "x", label: "X" }] },
    { key: "framing", label: "F", values: [{ id: "u", label: "U" }] },
  ],
  judges: [{ id: "j", label: "J" }],
  scopes: [
    { id: "full", label: "after", default: true },
    { id: "turn1", label: "pre" },
  ],
  items: [{ id: "JLS-001", title: "First" }],
  shards: {},
  scores: {
    order: ["subject", "item", "pressure", "framing", "scope"],
    shape: [2, 1, 1, 1, 2],
    data: [1, 0.5, -1, -0.5],
  },
  presets: [
    {
      key: "judges-differed",
      label: "Judges differed",
      entries: [
        {
          label: "JLS-001 — split",
          params: { item: "JLS-001", a: "b", b: "stale", pressure: "x", framing: "u", scope: "full" },
        },
      ],
    },
  ],
};

describe("computeGuided", () => {
  it("returns the three lists in order", () => {
    expect(computeGuided(INDEX).map((l) => l.key)).toEqual(["split", "judges", "flips"]);
  });

  it("uses the strongest model (highest total across stages) as the alternative in every entry", () => {
    for (const list of computeGuided(INDEX)) {
      for (const e of list.entries) expect(e.params.b).toBe("a");
    }
  });

  it("models-split A is the model most diverged from the best at the first stage", () => {
    expect(computeGuided(INDEX).find((l) => l.key === "split")?.entries[0]?.params.a).toBe("b");
  });

  it("pressure-flips A is the biggest mover, excluding the best", () => {
    expect(computeGuided(INDEX).find((l) => l.key === "flips")?.entries[0]?.params.a).toBe("b");
  });

  it("returns nothing without a score blob", () => {
    expect(computeGuided({ ...INDEX, scores: undefined })).toEqual([]);
  });
});
