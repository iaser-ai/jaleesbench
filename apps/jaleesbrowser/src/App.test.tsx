import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it } from "vitest";
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
  async loadItem(): Promise<ItemShard> {
    throw new Error("unused");
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

beforeEach(() => {
  window.history.replaceState(null, "", "/");
});

describe("App", () => {
  it("renders generic pickers and a default selection summary", async () => {
    render(<App dataSource={new FakeDataSource()} />);
    expect(
      await screen.findByRole("heading", { name: "Test dataset" }),
    ).toBeInTheDocument();
    expect(screen.getByLabelText("Model A")).toHaveValue("ansari");
    expect(screen.getByLabelText("Model B")).toHaveValue("gpt");
    expect(screen.getByLabelText("Pressure")).toHaveValue("secularize");
    expect(screen.getByLabelText("Framing")).toHaveValue("unstated");
    expect(screen.getByLabelText("Scope")).toHaveValue("full");
    expect(screen.getByText(/Comparing/)).toHaveTextContent("ansari");
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
