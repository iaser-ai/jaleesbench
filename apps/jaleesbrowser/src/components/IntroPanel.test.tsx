import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { ContractIndex } from "../contract";
import { IntroPanel } from "./IntroPanel";

const INDEX: ContractIndex = {
  contractVersion: "1.0",
  producer: { name: "t", version: "0" },
  dataset: { title: "T" },
  bands: [
    { value: -1, label: "Burns" },
    { value: 0, label: "Inert" },
    { value: 1, label: "Perfume" },
  ],
  subjects: [
    { id: "a", label: "a" },
    { id: "b", label: "b" },
  ],
  conditionAxes: [
    {
      key: "pressure",
      label: "Pressure",
      values: [
        { id: "x", label: "X" },
        { id: "y", label: "Y" },
      ],
    },
    { key: "framing", label: "Framing", values: [{ id: "u", label: "U" }] },
  ],
  judges: [
    { id: "j1", label: "J1" },
    { id: "j2", label: "J2" },
  ],
  scopes: [{ id: "full", label: "post-pressure", default: true }],
  items: [
    { id: "JLS-001", title: "First" },
    { id: "JLS-002", title: "Second" },
  ],
  shards: {},
  paper: { url: "https://example.com/paper.pdf", label: "The paper", draft: true },
};

describe("IntroPanel", () => {
  it("renders a collapsible 'about' with data-derived facts and the (draft) paper", () => {
    render(<IntroPanel index={INDEX} />);
    expect(screen.getByText("About / how to read this")).toBeInTheDocument(); // summary
    expect(screen.getByText(/righteous companion/)).toBeInTheDocument();
    expect(
      screen.getByText(/2 questions · 2 models · 2 pressure × 1 framing · 2 judges/),
    ).toBeInTheDocument();
    expect(screen.getByText(/-1 Burns/)).toBeInTheDocument(); // band names from data
    expect(screen.getByText(/\+1 Perfume/)).toBeInTheDocument();
    const link = screen.getByRole("link", { name: "The paper" });
    expect(link).toHaveAttribute("href", "https://example.com/paper.pdf");
    expect(link).toHaveAttribute("rel", "noopener noreferrer");
    expect(screen.getByText(/draft — under review/)).toBeInTheDocument();
  });
});
