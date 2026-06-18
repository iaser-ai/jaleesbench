import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import type { ContractIndex } from "../contract";
import type { Selection } from "../urlstate";
import { Compare } from "./Compare";

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
    { key: "pressure", label: "Pressure", values: [{ id: "x", label: "X" }] },
    { key: "framing", label: "Framing", values: [{ id: "u", label: "U" }] },
  ],
  judges: [{ id: "j", label: "J" }],
  scopes: [{ id: "full", label: "after", default: true }],
  items: [
    { id: "JLS-001", title: "First" },
    { id: "JLS-002", title: "Second" },
  ],
  shards: {},
  // A/001=+1, A/002=+0.5, B/001=-1, B/002=+0.5 → divergence 001=2, 002=0
  scores: {
    order: ["subject", "item", "pressure", "framing", "scope"],
    shape: [2, 2, 1, 1, 1],
    data: [1, 0.5, -1, 0.5],
  },
};

const sel: Selection = {
  view: "compare",
  item: "JLS-001",
  a: "A",
  b: "B",
  conditions: { pressure: "x", framing: "u" },
  scope: "full",
};

describe("Compare", () => {
  it("ranks rows by divergence and opens the detail on row click", () => {
    const onOpenDetail = vi.fn();
    render(
      <Compare index={INDEX} selection={sel} onChange={() => {}} onOpenDetail={onOpenDetail} />,
    );
    const rows = screen.getAllByRole("button"); // the clickable table rows
    expect(rows[0]).toHaveTextContent("JLS-001"); // highest |Δ|
    fireEvent.click(rows[0]);
    expect(onOpenDetail).toHaveBeenCalledWith(
      expect.objectContaining({ item: "JLS-001", delta: 2 }),
    );
  });

  it("changes the compared model via the picker", () => {
    const onChange = vi.fn();
    render(
      <Compare index={INDEX} selection={sel} onChange={onChange} onOpenDetail={() => {}} />,
    );
    fireEvent.change(screen.getByLabelText("Model B"), { target: { value: "A" } });
    expect(onChange).toHaveBeenCalledWith(expect.objectContaining({ b: "A" }));
  });

  it("shows a fail-soft message when there is no score blob", () => {
    const noScores: ContractIndex = { ...INDEX, scores: undefined };
    render(
      <Compare index={noScores} selection={sel} onChange={() => {}} onOpenDetail={() => {}} />,
    );
    expect(screen.getByText(/No comparable scores/)).toBeInTheDocument();
  });
});
