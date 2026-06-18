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
  // Distinctive labels prove the score header reads them from the data
  // (it would fail if the component hardcoded "initial"/"post-pressure").
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
  it("renders both columns' transcripts and verdicts", () => {
    render(<Comparison index={INDEX} shard={SHARD} selection={sel()} />);
    expect(screen.getByLabelText("Responses from ansari")).toBeInTheDocument();
    expect(screen.getByLabelText("Responses from gpt")).toBeInTheDocument();
    expect(screen.getByText("Ansari stays steadfast")).toBeInTheDocument();
    expect(screen.getByText("GPT caves")).toBeInTheDocument();
  });

  it("shows the per-model score header using the data's scope labels", () => {
    render(<Comparison index={INDEX} shard={SHARD} selection={sel()} />);
    // ansari: turn1 ("pre") mean 0 → full ("after") mean +1 — labels from index.scopes
    expect(screen.getByText(/0 pre → \+1 after/)).toBeInTheDocument();
    // gpt: no turn1 verdict → "—"
    expect(screen.getByText(/— → -1 after/)).toBeInTheDocument();
  });

  it("shows opposed bands for a polarizing cell", () => {
    render(<Comparison index={INDEX} shard={SHARD} selection={sel()} />);
    expect(screen.getByText(/Perfume \(\+1\)/)).toBeInTheDocument();
    expect(screen.getByText(/Burns \(-1\)/)).toBeInTheDocument();
  });

  it("tolerates a verdict with no rationale", () => {
    render(<Comparison index={INDEX} shard={SHARD} selection={sel()} />);
    expect(screen.getByText("bad")).toBeInTheDocument(); // gpt summary, no rationale, no crash
  });

  it("renders model text as literal (no HTML injection)", () => {
    const { container } = render(
      <Comparison index={INDEX} shard={SHARD} selection={sel()} />,
    );
    expect(container.querySelector("script")).toBeNull();
    expect(screen.getAllByText(/<script>alert\(1\)<\/script>/).length).toBeGreaterThan(0);
  });

  it("filters verdicts by the selected scope", () => {
    render(<Comparison index={INDEX} shard={SHARD} selection={sel({ scope: "turn1" })} />);
    expect(screen.getByText(/Inert \(0\)/)).toBeInTheDocument(); // ansari turn1 verdict
    expect(screen.queryByText(/Perfume/)).toBeNull(); // full-scope verdict hidden
  });

  it("shows a fail-soft no-data state for a missing cell", () => {
    render(<Comparison index={INDEX} shard={SHARD} selection={sel({ b: "qwen" })} />);
    expect(screen.getByText("No data for this combination.")).toBeInTheDocument();
    expect(screen.getByLabelText("Responses from qwen")).toBeInTheDocument();
  });
});
