import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { ContractIndex } from "../contract";
import { ModelStats } from "./ModelStats";

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
  // a recognition = s.full(1) − u.full(0.4) = +0.6 (unique value across the table)
  scores: {
    order: ["subject", "item", "pressure", "framing", "scope"],
    shape: [2, 1, 1, 2, 2],
    data: [0.4, 0.8, 1.0, 0.8, -1, -0.5, -0.5, -0.5],
  },
};

describe("ModelStats", () => {
  it("renders the A-vs-B headline and per-axis breakdowns from the score blob", () => {
    render(<ModelStats index={INDEX} a="a" b="b" />);
    expect(screen.getByLabelText("Stats: a vs b")).toBeInTheDocument();
    expect(screen.getByText("Overall (mean band)")).toBeInTheDocument();
    expect(screen.getByText(/Recognition gain/)).toBeInTheDocument();
    expect(screen.getByText("Steadfastness (post − initial)")).toBeInTheDocument();
    expect(screen.getByText("By Pressure")).toBeInTheDocument();
    expect(screen.getByText("By Framing")).toBeInTheDocument();
    expect(screen.getByText("+0.6")).toBeInTheDocument(); // a's recognition gain
  });
});
