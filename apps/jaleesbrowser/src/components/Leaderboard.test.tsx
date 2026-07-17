import { fireEvent, render, screen, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import type { ContractIndex } from "../contract";
import { Leaderboard } from "./Leaderboard";

// Same tensor as leaderboard.test.ts: canonical order is B before A (B wins on
// the first framing value's post score), while A wins on the overall post mean.
const perPressure = (f1: number[], f2: number[]) => [...f1, ...f2];
const subjectData = (f1full: number, f2full: number, turn1: number) => [
  ...perPressure([f1full, turn1], [f2full, turn1]),
  ...perPressure([f1full, turn1], [f2full, turn1]),
  ...perPressure([f1full, turn1], [f2full, turn1]),
];

const INDEX: ContractIndex = {
  contractVersion: "1.0",
  producer: { name: "t", version: "0" },
  dataset: { title: "T" },
  bands: [
    { value: -1, label: "Burns" },
    { value: 1, label: "Perfume" },
  ],
  subjects: [
    { id: "A", label: "model-a" },
    { id: "B", label: "model-b" },
  ],
  conditionAxes: [
    {
      key: "pressure",
      label: "Pressure",
      values: [
        { id: "p1", label: "P1" },
        { id: "p2", label: "P2" },
        { id: "p3", label: "P3" },
      ],
    },
    {
      key: "framing",
      label: "Framing",
      values: [
        { id: "f1", label: "Unstated" },
        { id: "f2", label: "Stated" },
      ],
    },
  ],
  judges: [{ id: "j", label: "J" }],
  scopes: [
    { id: "full", label: "post-pressure", default: true },
    { id: "turn1", label: "initial" },
  ],
  items: [{ id: "JLS-001", title: "First" }],
  shards: {},
  scores: {
    order: ["subject", "item", "pressure", "framing", "scope"],
    shape: [2, 1, 3, 2, 2],
    data: [...subjectData(0.0, 1.0, 0.8), ...subjectData(0.4, 0.4, 0.2)],
  },
};

const bodyRows = () => screen.getAllByRole("row").slice(1); // drop the header row

describe("Leaderboard", () => {
  it("renders one row per subject in canonical order, with scope and framing columns", () => {
    render(<Leaderboard index={INDEX} onOpenSubject={() => {}} />);
    expect(screen.getByRole("button", { name: "initial" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "post-pressure" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Unstated" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Stated" })).toBeInTheDocument();
    const rows = bodyRows();
    expect(rows).toHaveLength(2);
    expect(within(rows[0]).getByText("model-b")).toBeInTheDocument();
    expect(within(rows[1]).getByText("model-a")).toBeInTheDocument();
    // model-a: initial +0.80, post +0.50, Δ −0.30, Unstated 0.00, Stated +1.00
    expect(within(rows[1]).getByText("+0.80")).toBeInTheDocument();
    expect(within(rows[1]).getByText("-0.30")).toBeInTheDocument();
  });

  it("re-sorts on a column click but keeps the canonical rank numbers", () => {
    render(<Leaderboard index={INDEX} onOpenSubject={() => {}} />);
    fireEvent.click(screen.getByRole("button", { name: "post-pressure" }));
    const rows = bodyRows();
    // model-a wins on overall post (0.5 > 0.4) — but its canonical rank stays 2.
    expect(within(rows[0]).getByText("model-a")).toBeInTheDocument();
    expect(within(rows[0]).getByText("2")).toBeInTheDocument();
    expect(within(rows[1]).getByText("1")).toBeInTheDocument();
  });

  it("toggles the sort direction on a second click", () => {
    render(<Leaderboard index={INDEX} onOpenSubject={() => {}} />);
    const post = screen.getByRole("button", { name: /post-pressure/ });
    fireEvent.click(post);
    fireEvent.click(post); // ascending → model-b (0.4) first
    expect(within(bodyRows()[0]).getByText("model-b")).toBeInTheDocument();
  });

  it("opens a subject on click", () => {
    const onOpenSubject = vi.fn();
    render(<Leaderboard index={INDEX} onOpenSubject={onOpenSubject} />);
    fireEvent.click(screen.getByRole("button", { name: "model-a" }));
    expect(onOpenSubject).toHaveBeenCalledWith("A");
  });

  it("shows a message when the index ships no score blob", () => {
    render(<Leaderboard index={{ ...INDEX, scores: undefined }} onOpenSubject={() => {}} />);
    expect(screen.getByText(/no score summary/)).toBeInTheDocument();
  });
});
