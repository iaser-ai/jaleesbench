import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { ItemShard } from "../contract";
import { ItemHeader } from "./ItemHeader";

const SHARD: ItemShard = {
  item: {
    id: "JLS-001",
    title: "The team message",
    tags: {
      chapter: "Backbiting",
      pillars: ["restraint", "justice"],
      hearts: [],
      islamic: "clean",
    },
    context: "Proof text <b>here</b>",
  },
  cells: [],
};

describe("ItemHeader", () => {
  it("renders the title, non-empty tags generically, and context", () => {
    render(<ItemHeader shard={SHARD} />);
    expect(screen.getByText(/JLS-001 — The team message/)).toBeInTheDocument();
    expect(screen.getByText("chapter")).toBeInTheDocument();
    expect(screen.getByText("Backbiting")).toBeInTheDocument();
    expect(screen.getByText("restraint, justice")).toBeInTheDocument(); // array joined
    expect(screen.getByText("clean")).toBeInTheDocument();
    expect(screen.queryByText("hearts")).toBeNull(); // empty array omitted
    // context rendered as escaped literal text, not interpreted HTML
    expect(screen.getByText(/Proof text <b>here<\/b>/)).toBeInTheDocument();
  });

  it("renders cleanly with no tags or context", () => {
    render(<ItemHeader shard={{ item: { id: "X", title: "Y" }, cells: [] }} />);
    expect(screen.getByText(/X — Y/)).toBeInTheDocument();
  });
});
