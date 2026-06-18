import { describe, expect, it } from "vitest";
import type { ContractIndex, ItemShard } from "./contract";
import { bandColor, cellKey, indexCells, signed } from "./format";

const INDEX: ContractIndex = {
  contractVersion: "1.0",
  producer: { name: "t", version: "0" },
  dataset: { title: "T" },
  bands: [
    { value: -1, label: "Burns", color: "#a02020" },
    { value: 0, label: "Inert" }, // no color → positional fallback
    { value: 1, label: "Perfume", color: "#1a6840" },
  ],
  subjects: [{ id: "a", label: "A" }],
  conditionAxes: [
    { key: "pressure", label: "P", values: [{ id: "x", label: "X" }] },
    { key: "framing", label: "F", values: [{ id: "u", label: "U" }] },
  ],
  judges: [{ id: "j", label: "J" }],
  items: [{ id: "JLS-001", title: "First" }],
  shards: { "JLS-001": "probes/JLS-001.json.gz" },
};

const SHARD: ItemShard = {
  item: { id: "JLS-001", title: "First" },
  cells: [
    {
      subject: "a",
      conditions: { pressure: "x", framing: "u" },
      transcript: [{ role: "user", content: "hi" }],
      verdicts: [],
    },
  ],
};

describe("format", () => {
  it("uses the producer color when present", () => {
    expect(bandColor(INDEX, -1)).toBe("#a02020");
    expect(bandColor(INDEX, 1)).toBe("#1a6840");
  });

  it("falls back to a positional color when a band has none", () => {
    // value 0 is the middle of 3 bands → middle of the ramp.
    expect(bandColor(INDEX, 0)).toBe("#888888");
  });

  it("signs band values for display", () => {
    expect(signed(1)).toBe("+1");
    expect(signed(-0.5)).toBe("-0.5");
    expect(signed(0)).toBe("0");
  });

  it("builds a stable cell key and indexes cells by (subject, conditions)", () => {
    const axisKeys = INDEX.conditionAxes.map((a) => a.key);
    const map = indexCells(SHARD, axisKeys);
    const key = cellKey("a", { pressure: "x", framing: "u" }, axisKeys);
    expect(map.get(key)?.transcript[0].content).toBe("hi");
    // condition order follows axisKeys, not object insertion order
    expect(cellKey("a", { framing: "u", pressure: "x" }, axisKeys)).toBe(key);
    expect(map.get(cellKey("a", { pressure: "x", framing: "OTHER" }, axisKeys))).toBeUndefined();
  });
});
