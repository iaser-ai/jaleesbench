import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { ContractIndex, ItemShard } from "../contract";
import type { Selection } from "../urlstate";
import { Comparison } from "./Comparison";

const INDEX: ContractIndex = {
  contractVersion: "1.0",
  producer: { name: "t", version: "0" },
  dataset: { title: "T" },
  bands: [
    { value: -1, label: "Burns", color: "#a02020" },
    { value: 0, label: "Inert" },
    { value: 1, label: "Perfume", color: "#1a6840" },
  ],
  subjects: [
    { id: "ansari", label: "ansari" },
    { id: "gpt", label: "gpt" },
    { id: "qwen", label: "qwen" },
  ],
  conditionAxes: [
    { key: "pressure", label: "Pressure", values: [{ id: "insistence", label: "Insistence" }] },
    { key: "framing", label: "Framing", values: [{ id: "unstated", label: "Unstated" }] },
  ],
  judges: [
    { id: "opus", label: "Opus" },
    { id: "gemini", label: "Gemini" },
  ],
  // Distinctive scope labels prove the header reads them from the data.
  scopes: [
    { id: "full", label: "after", default: true },
    { id: "turn1", label: "pre" },
  ],
  items: [{ id: "JLS-006", title: "Polarizing" }],
  shards: { "JLS-006": "probes/JLS-006.json.gz" },
};

const XSS = "My question <script>alert(1)</script>";

const SHARD: ItemShard = {
  item: { id: "JLS-006", title: "Polarizing" },
  cells: [
    {
      subject: "ansari",
      conditions: { pressure: "insistence", framing: "unstated" },
      transcript: [
        { role: "user", content: XSS },
        { role: "assistant", content: "Ansari first reply" },
        { role: "user", content: "the pressure turn" },
        { role: "assistant", content: "Ansari stays steadfast" },
      ],
      verdicts: [
        { judge: "opus", scope: "full", band: 1, bandLabel: "Perfume", summary: "good", rationale: "ansari rationale" },
        { judge: "opus", scope: "turn1", band: 0, bandLabel: "Inert", summary: "meh" },
      ],
    },
    {
      subject: "gpt",
      conditions: { pressure: "insistence", framing: "unstated" },
      transcript: [
        { role: "user", content: XSS },
        { role: "assistant", content: "GPT first reply" },
        { role: "user", content: "the pressure turn" },
        { role: "assistant", content: "GPT caves" },
      ],
      // No rationale on this verdict (e.g. a judgments_v2 override).
      verdicts: [{ judge: "opus", scope: "full", band: -1, bandLabel: "Burns", summary: "bad" }],
    },
  ],
};

function sel(over: Partial<Selection> = {}): Selection {
  return {
    view: "detail",
    item: "JLS-006",
    a: "ansari",
    b: "gpt",
    conditions: { pressure: "insistence", framing: "unstated" },
    scope: "full",
    ...over,
  };
}

describe("Comparison", () => {
  it("renders both models' responses side by side", () => {
    render(<Comparison index={INDEX} shard={SHARD} selection={sel()} />);
    expect(screen.getByText("Ansari stays steadfast")).toBeInTheDocument();
    expect(screen.getByText("GPT caves")).toBeInTheDocument();
  });

  it("renders each shared user prompt once, not duplicated per column", () => {
    render(<Comparison index={INDEX} shard={SHARD} selection={sel()} />);
    // Both models received the identical prompt → it appears exactly once.
    expect(screen.getAllByText(/<script>alert\(1\)<\/script>/)).toHaveLength(1);
    expect(screen.getAllByText("the pressure turn")).toHaveLength(1);
  });

  it("renders model text as literal (no HTML injection)", () => {
    const { container } = render(<Comparison index={INDEX} shard={SHARD} selection={sel()} />);
    expect(container.querySelector("script")).toBeNull();
  });

  it("shows the per-model score header using the data's scope labels", () => {
    render(<Comparison index={INDEX} shard={SHARD} selection={sel()} />);
    expect(screen.getByText(/pre → \+1 after/)).toBeInTheDocument(); // ansari: turn1 0 → full +1
    expect(screen.getByText(/— → -1 after/)).toBeInTheDocument(); // gpt: no turn1 → "—"
  });

  it("shows each stage's judges: initial after the first response, post after pressure", () => {
    render(<Comparison index={INDEX} shard={SHARD} selection={sel()} />);
    expect(screen.getByText(/Judges — pre/)).toBeInTheDocument();
    expect(screen.getByText(/Judges — after/)).toBeInTheDocument();
    expect(screen.getByText(/Perfume \(\+1\)/)).toBeInTheDocument(); // ansari, post
    expect(screen.getByText(/Burns \(-1\)/)).toBeInTheDocument(); // gpt, post
    expect(screen.getByText(/Inert \(0\)/)).toBeInTheDocument(); // ansari, initial
  });

  it("tolerates a verdict with no rationale", () => {
    render(<Comparison index={INDEX} shard={SHARD} selection={sel()} />);
    expect(screen.getByText("bad")).toBeInTheDocument(); // gpt summary, no rationale, no crash
  });

  it("shows a fail-soft no-data state for a missing cell", () => {
    render(<Comparison index={INDEX} shard={SHARD} selection={sel({ b: "qwen" })} />);
    expect(screen.getAllByText(/No data/).length).toBeGreaterThan(0);
  });

  it("collapses to a single model when model B is none (\"\")", () => {
    const { container } = render(
      <Comparison index={INDEX} shard={SHARD} selection={sel({ b: "" })} />,
    );
    // single-column container marker
    expect(container.querySelector(".comparison.single")).not.toBeNull();
    // model A is shown; the second column (GPT) is gone entirely
    expect(screen.getByText("Ansari stays steadfast")).toBeInTheDocument();
    expect(screen.queryByText("GPT caves")).toBeNull();
    expect(screen.queryByText("gpt")).toBeNull(); // no B column header
    // model A's verdicts still render (both judges within the one column)
    expect(screen.getByText(/Perfume \(\+1\)/)).toBeInTheDocument();
    expect(screen.getByText(/Inert \(0\)/)).toBeInTheDocument();
    // the B-side verdict is gone, and there is no "No data" filler for a dropped column
    expect(screen.queryByText(/Burns \(-1\)/)).toBeNull();
    expect(screen.queryByText(/No data/)).toBeNull();
  });
});
