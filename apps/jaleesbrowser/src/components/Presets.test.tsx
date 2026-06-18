import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import type { ContractIndex } from "../contract";
import { Presets } from "./Presets";

// a: total 1.5, b: total -1.5 → best = a (the alternative in every entry).
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

describe("Presets", () => {
  it("renders the three in-app guided lists", () => {
    render(<Presets index={INDEX} onApply={() => {}} />);
    expect(screen.getByText("Models split (first response)")).toBeInTheDocument();
    expect(screen.getByText("Judges differed")).toBeInTheDocument();
    expect(screen.getByText("Biggest pressure flips")).toBeInTheDocument();
  });

  it("applies an entry as a Selection with the strongest model as the alternative", () => {
    const onApply = vi.fn();
    render(<Presets index={INDEX} onApply={onApply} />);
    fireEvent.click(screen.getByRole("button", { name: /b vs a/ }));
    expect(onApply).toHaveBeenCalledWith(
      expect.objectContaining({ item: "JLS-001", a: "b", b: "a" }),
    );
  });

  it("renders nothing without a score blob", () => {
    const { container } = render(
      <Presets index={{ ...INDEX, scores: undefined }} onApply={() => {}} />,
    );
    expect(container).toBeEmptyDOMElement();
  });
});
