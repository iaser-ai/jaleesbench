import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { App } from "./App";
import type { ContractIndex, ItemShard } from "./contract";
import type { DataSource } from "./datasource";

const INDEX: ContractIndex = {
  contractVersion: "1.0",
  producer: { name: "t", version: "0" },
  dataset: { title: "Test dataset", language: "en" },
  bands: [
    { value: -1, label: "Burns" },
    { value: 1, label: "Perfume" },
  ],
  subjects: [
    { id: "a", label: "a" },
    { id: "b", label: "b" },
  ],
  conditionAxes: [
    { key: "pressure", label: "Pressure", values: [{ id: "x", label: "X" }] },
    { key: "framing", label: "Framing", values: [{ id: "u", label: "U" }] },
  ],
  judges: [{ id: "j", label: "J" }],
  scopes: [
    { id: "full", label: "post-pressure", default: true },
    { id: "turn1", label: "initial" },
  ],
  items: [
    { id: "JLS-001", title: "First" },
    { id: "JLS-002", title: "Second" },
  ],
  shards: {
    "JLS-001": "probes/JLS-001.json.gz",
    "JLS-002": "probes/JLS-002.json.gz",
  },
  // A/001=+1, A/002=+0.5, B/001=-1, B/002=+0.5 → JLS-001 diverges (Δ=2)
  scores: {
    order: ["subject", "item", "pressure", "framing", "scope"],
    shape: [2, 2, 1, 1, 2],
    data: [1, 0.5, 0.5, 0.2, -1, 0, 0.5, 0.1],
  },
};

const SHARD: ItemShard = { item: { id: "JLS-001", title: "First" }, cells: [] };

function makeDataSource(loadItem = vi.fn().mockResolvedValue(SHARD)): DataSource {
  return { loadIndex: async () => INDEX, loadItem };
}

beforeEach(() => {
  window.history.replaceState(null, "", "/");
});

describe("App", () => {
  it("lands on the comparison (sidebar controls + stats + divergent list), no shard load", async () => {
    const loadItem = vi.fn().mockResolvedValue(SHARD);
    render(<App dataSource={makeDataSource(loadItem)} />);
    expect(await screen.findByLabelText("Model A")).toHaveValue("a");
    expect(screen.getByLabelText("Model B")).toHaveValue("b");
    expect(screen.getByLabelText("Scope")).toHaveValue("full");
    expect(screen.getByLabelText("Stats: a vs b")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /JLS-001/ })).toBeInTheDocument();
    expect(loadItem).not.toHaveBeenCalled(); // list/stats = no shard loads
  });

  it("opens a cell's detail when a divergent row is clicked (loads its shard)", async () => {
    const loadItem = vi.fn().mockResolvedValue(SHARD);
    render(<App dataSource={makeDataSource(loadItem)} />);
    fireEvent.click(await screen.findByRole("button", { name: /JLS-001/ }));
    expect(await screen.findByText("← Back to comparison")).toBeInTheDocument();
    expect(screen.getByLabelText("Responses from a")).toBeInTheDocument();
    expect(loadItem).toHaveBeenCalledWith("JLS-001");
    const params = new URLSearchParams(window.location.search);
    expect(params.get("item")).toBe("JLS-001");
  });

  it("returns to the comparison from the detail via 'back'", async () => {
    render(<App dataSource={makeDataSource()} />);
    fireEvent.click(await screen.findByRole("button", { name: /JLS-001/ }));
    fireEvent.click(await screen.findByText("← Back to comparison"));
    expect(screen.getByLabelText("Stats: a vs b")).toBeInTheDocument();
    expect(screen.queryByText("← Back to comparison")).toBeNull();
    expect(new URLSearchParams(window.location.search).get("item")).toBeNull();
  });

  it("restores an open cell from a deep-link URL", async () => {
    window.history.replaceState(
      null,
      "",
      "?a=a&b=b&item=JLS-001&pressure=x&framing=u&scope=full",
    );
    render(<App dataSource={makeDataSource()} />);
    expect(await screen.findByText("← Back to comparison")).toBeInTheDocument();
    expect(screen.getByLabelText("Responses from a")).toBeInTheDocument();
  });

  it("an absent item in the URL falls back to the comparison (no crash)", async () => {
    window.history.replaceState(null, "", "?item=NOPE");
    render(<App dataSource={makeDataSource()} />);
    expect(await screen.findByLabelText("Stats: a vs b")).toBeInTheDocument();
  });

  it("shows a fail-soft message when the shard fails to load", async () => {
    const loadItem = vi.fn().mockRejectedValue(new Error("shard 404"));
    window.history.replaceState(null, "", "?a=a&b=b&item=JLS-001&pressure=x&framing=u");
    render(<App dataSource={makeDataSource(loadItem)} />);
    expect(await screen.findByRole("alert")).toHaveTextContent("shard 404");
    expect(screen.getByLabelText("Model A")).toHaveValue("a"); // controls stay usable
  });

  it("shows a fail-soft message when the index fails to load", async () => {
    const ds: DataSource = {
      loadIndex: async () => {
        throw new Error("boom");
      },
      loadItem: vi.fn(),
    };
    render(<App dataSource={ds} />);
    expect(await screen.findByRole("alert")).toHaveTextContent("boom");
  });
});
