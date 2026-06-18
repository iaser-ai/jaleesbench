import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { App } from "./App";
import type { ContractIndex, ItemShard } from "./contract";
import type { DataSource } from "./datasource";

const INDEX: ContractIndex = {
  contractVersion: "1.0",
  producer: { name: "t", version: "0" },
  dataset: { title: "Test dataset", language: "en" },
  bands: [{ value: 1, label: "High" }],
  subjects: [
    { id: "ansari", label: "ansari" },
    { id: "gpt", label: "gpt" },
    { id: "qwen", label: "qwen" },
  ],
  conditionAxes: [
    {
      key: "pressure",
      label: "Pressure",
      values: [
        { id: "secularize", label: "Secularize" },
        { id: "insistence", label: "Insistence" },
      ],
    },
    {
      key: "framing",
      label: "Framing",
      values: [
        { id: "unstated", label: "Unstated" },
        { id: "stated", label: "Stated" },
      ],
    },
  ],
  judges: [{ id: "j1", label: "J1" }],
  scopes: [
    { id: "full", label: "Full", default: true },
    { id: "turn1", label: "Turn 1" },
  ],
  items: [
    { id: "JLS-001", title: "First" },
    { id: "JLS-002", title: "Second" },
  ],
  shards: { "JLS-001": "probes/JLS-001.json.gz", "JLS-002": "probes/JLS-002.json.gz" },
};

class FakeDataSource implements DataSource {
  async loadIndex(): Promise<ContractIndex> {
    return INDEX;
  }
  async loadItem(itemId: string): Promise<ItemShard> {
    return { item: { id: itemId, title: "x" }, cells: [] };
  }
}

class FailingDataSource implements DataSource {
  async loadIndex(): Promise<ContractIndex> {
    throw new Error("boom");
  }
  async loadItem(): Promise<ItemShard> {
    throw new Error("boom");
  }
}

/** Index loads, but the per-item shard fetch fails. */
class ShardFailDataSource implements DataSource {
  async loadIndex(): Promise<ContractIndex> {
    return INDEX;
  }
  async loadItem(): Promise<ItemShard> {
    throw new Error("shard 404");
  }
}

beforeEach(() => {
  window.history.replaceState(null, "", "/");
});

describe("App", () => {
  it("renders generic pickers, the band legend, and the comparison", async () => {
    render(<App dataSource={new FakeDataSource()} />);
    expect(
      await screen.findByRole("heading", { name: "Test dataset" }),
    ).toBeInTheDocument();
    expect(screen.getByLabelText("Model A")).toHaveValue("ansari");
    expect(screen.getByLabelText("Model B")).toHaveValue("gpt");
    expect(screen.getByLabelText("Pressure")).toHaveValue("secularize");
    expect(screen.getByLabelText("Framing")).toHaveValue("unstated");
    expect(screen.getByLabelText("Scope")).toHaveValue("full");
    expect(screen.getByLabelText("Band legend")).toBeInTheDocument();
    // The comparison mounts once the shard loads (two columns from the selection).
    expect(await screen.findByLabelText("Responses from ansari")).toBeInTheDocument();
    expect(screen.getByLabelText("Responses from gpt")).toBeInTheDocument();
  });

  it("compare view renders without loading a shard (no detail-only controls)", async () => {
    const loadItem = vi.fn().mockResolvedValue({ item: { id: "x", title: "x" }, cells: [] });
    const ds: DataSource = { loadIndex: async () => INDEX, loadItem };
    window.history.replaceState(null, "", "?view=compare&a=ansari&b=gpt");
    render(<App dataSource={ds} />);
    expect(await screen.findByLabelText("Model A")).toHaveValue("ansari");
    expect(screen.queryByLabelText("Question")).toBeNull(); // detail-only
    expect(screen.queryByLabelText("Band legend")).toBeNull(); // detail-only
    expect(loadItem).not.toHaveBeenCalled(); // compare = no shard loads
  });

  it("toggles between detail and compare, updating the URL", async () => {
    render(<App dataSource={new FakeDataSource()} />);
    expect(await screen.findByLabelText("Question")).toBeInTheDocument(); // detail default
    fireEvent.click(screen.getByRole("button", { name: "Compare" }));
    expect(screen.queryByLabelText("Question")).toBeNull();
    expect(new URLSearchParams(window.location.search).get("view")).toBe("compare");
    fireEvent.click(screen.getByRole("button", { name: "Detail" }));
    expect(screen.getByLabelText("Question")).toBeInTheDocument();
  });

  it("a compare-row click opens detail at the default scope (not the prior scope)", async () => {
    const INDEX2: ContractIndex = {
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
      shards: { "JLS-001": "probes/JLS-001.json.gz" },
      scores: {
        order: ["subject", "item", "pressure", "framing", "scope"],
        shape: [2, 1, 1, 1, 2],
        data: [1, 0.3, -1, 0.2], // a/full=1, a/turn1=0.3, b/full=-1, b/turn1=0.2
      },
    };
    const loadItem = vi
      .fn()
      .mockResolvedValue({ item: { id: "JLS-001", title: "First" }, cells: [] });
    const ds: DataSource = { loadIndex: async () => INDEX2, loadItem };
    window.history.replaceState(null, "", "?view=compare&a=a&b=b&scope=turn1");
    render(<App dataSource={ds} />);
    fireEvent.click(await screen.findByRole("button", { name: /JLS-001/ }));
    const params = new URLSearchParams(window.location.search);
    expect(params.get("view")).toBe("detail");
    expect(params.get("scope")).toBe("full"); // default scope (the ranking's), not turn1
  });

  it("shows a fail-soft message when the shard fails to load (pickers stay usable)", async () => {
    render(<App dataSource={new ShardFailDataSource()} />);
    expect(await screen.findByRole("alert")).toHaveTextContent("shard 404");
    expect(screen.getByLabelText("Model A")).toHaveValue("ansari"); // pickers still work
  });

  it("writes the selection to the URL when a picker changes", async () => {
    render(<App dataSource={new FakeDataSource()} />);
    fireEvent.change(await screen.findByLabelText("Model B"), {
      target: { value: "qwen" },
    });
    const params = new URLSearchParams(window.location.search);
    expect(params.get("b")).toBe("qwen");
    expect(params.get("item")).toBe("JLS-001");
    expect(params.get("pressure")).toBe("secularize");
    expect(params.get("scope")).toBe("full");
  });

  it("restores the exact selection from a deep-link URL", async () => {
    window.history.replaceState(
      null,
      "",
      "?item=JLS-002&a=gpt&b=qwen&pressure=insistence&framing=stated&scope=turn1",
    );
    render(<App dataSource={new FakeDataSource()} />);
    expect(await screen.findByLabelText("Question")).toHaveValue("JLS-002");
    expect(screen.getByLabelText("Model A")).toHaveValue("gpt");
    expect(screen.getByLabelText("Model B")).toHaveValue("qwen");
    expect(screen.getByLabelText("Pressure")).toHaveValue("insistence");
    expect(screen.getByLabelText("Scope")).toHaveValue("turn1");
  });

  it("falls back to defaults for an invalid deep-link without crashing", async () => {
    window.history.replaceState(null, "", "?item=NOPE&a=ghost&pressure=bogus");
    render(<App dataSource={new FakeDataSource()} />);
    expect(await screen.findByLabelText("Question")).toHaveValue("JLS-001");
    expect(screen.getByLabelText("Model A")).toHaveValue("ansari");
    expect(screen.getByLabelText("Pressure")).toHaveValue("secularize");
  });

  it("renders the comparison for a valid default when the URL references an absent subject/axis", async () => {
    // a=ghost (absent subject) and pressure=bogus (absent axis value) must fall back
    // to valid defaults in the *rendered comparison*, not leak the raw ids.
    window.history.replaceState(null, "", "?a=ghost&b=qwen&pressure=bogus");
    render(<App dataSource={new FakeDataSource()} />);
    expect(await screen.findByLabelText("Responses from ansari")).toBeInTheDocument(); // a → default
    expect(screen.getByLabelText("Responses from qwen")).toBeInTheDocument(); // b kept (valid)
    expect(screen.queryByLabelText("Responses from ghost")).toBeNull();
    expect(screen.getByLabelText("Pressure")).toHaveValue("secularize"); // bad axis → default
  });

  it("filters the question picker by id/title", async () => {
    render(<App dataSource={new FakeDataSource()} />);
    fireEvent.change(await screen.findByLabelText("Filter questions"), {
      target: { value: "First" },
    });
    const question = screen.getByLabelText("Question") as HTMLSelectElement;
    const values = Array.from(question.options).map((o) => o.value);
    expect(values).toContain("JLS-001");
    expect(values).not.toContain("JLS-002");
  });

  it("shows a fail-soft message when the source errors", async () => {
    render(<App dataSource={new FailingDataSource()} />);
    expect(await screen.findByRole("alert")).toHaveTextContent("boom");
  });
});
