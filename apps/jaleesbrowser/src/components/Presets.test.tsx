import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import type { ContractIndex } from "../contract";
import { Presets } from "./Presets";

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
  scopes: [{ id: "full", label: "after", default: true }],
  items: [{ id: "JLS-001", title: "First" }],
  shards: {},
  presets: [
    {
      key: "polarizing",
      label: "Polarizing — models split",
      description: "one near Perfume, another near Burns",
      entries: [
        {
          label: "JLS-001 — a vs b",
          params: {
            view: "detail",
            item: "JLS-001",
            a: "a",
            b: "b",
            pressure: "x",
            framing: "u",
            scope: "full",
          },
        },
      ],
    },
  ],
};

describe("Presets", () => {
  it("lists the presets and applies an entry's deep-link as a Selection", () => {
    const onApply = vi.fn();
    render(<Presets index={INDEX} onApply={onApply} />);
    expect(screen.getByText("Polarizing — models split")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "JLS-001 — a vs b" }));
    expect(onApply).toHaveBeenCalledWith(
      expect.objectContaining({
        view: "detail",
        item: "JLS-001",
        a: "a",
        b: "b",
        conditions: { pressure: "x", framing: "u" },
        scope: "full",
      }),
    );
  });

  it("renders nothing when there are no presets", () => {
    const { container } = render(
      <Presets index={{ ...INDEX, presets: undefined }} onApply={() => {}} />,
    );
    expect(container).toBeEmptyDOMElement();
  });
});
