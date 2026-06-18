import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import type { ContractIndex } from "../contract";
import { DivergentCases } from "./DivergentCases";

const BASE: ContractIndex = {
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
  scores: {
    order: ["subject", "item", "pressure", "framing", "scope"],
    shape: [2, 2, 1, 1, 1],
    data: [1, 0.5, -1, 0.5], // A/001=1, A/002=0.5, B/001=-1, B/002=0.5 → 001 diverges (2)
  },
};

describe("DivergentCases", () => {
  it("ranks rows by divergence and opens the detail on row click", () => {
    const onPick = vi.fn();
    render(<DivergentCases index={BASE} a="A" b="B" onPick={onPick} />);
    const rows = screen.getAllByRole("button");
    expect(rows[0]).toHaveTextContent("JLS-001"); // highest |Δ|
    fireEvent.click(rows[0]);
    expect(onPick).toHaveBeenCalledWith(
      expect.objectContaining({ item: "JLS-001", delta: 2 }),
    );
  });

  it("shows the top 12 rows with a 'show more' that reveals the rest", () => {
    const n = 20;
    const items = Array.from({ length: n }, (_, i) => ({
      id: `JLS-${String(i + 1).padStart(3, "0")}`,
      title: `Q${i + 1}`,
    }));
    const big: ContractIndex = {
      ...BASE,
      items,
      scores: {
        order: ["subject", "item", "pressure", "framing", "scope"],
        shape: [2, n, 1, 1, 1],
        data: [...items.map(() => 1), ...items.map(() => -1)],
      },
    };
    render(<DivergentCases index={big} a="A" b="B" onPick={() => {}} />);
    expect(screen.getAllByRole("button")).toHaveLength(13); // 12 rows + show more
    fireEvent.click(screen.getByRole("button", { name: /Show more/ }));
    expect(screen.getAllByRole("button")).toHaveLength(20);
  });

  it("renders nothing when there is no score blob", () => {
    const { container } = render(
      <DivergentCases index={{ ...BASE, scores: undefined }} a="A" b="B" onPick={() => {}} />,
    );
    expect(container).toBeEmptyDOMElement();
  });
});
