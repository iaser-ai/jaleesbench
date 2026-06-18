import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { App } from "./App";
import type { ContractIndex, ItemShard } from "./contract";
import type { DataSource } from "./datasource";

const INDEX: ContractIndex = {
  contractVersion: "1.0",
  producer: { name: "test", version: "0" },
  dataset: { title: "Test dataset", language: "en" },
  bands: [{ value: 1, label: "High" }],
  subjects: [
    { id: "a", label: "A" },
    { id: "b", label: "B" },
  ],
  conditionAxes: [],
  judges: [{ id: "j1", label: "J1" }],
  items: [{ id: "JLS-001", title: "First" }],
  shards: { "JLS-001": "data/probes/JLS-001.json.gz" },
};

class FakeDataSource implements DataSource {
  async loadIndex(): Promise<ContractIndex> {
    return INDEX;
  }
  async loadItem(): Promise<ItemShard> {
    throw new Error("not used in this test");
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

describe("App", () => {
  it("renders the dataset title and counts from the index", async () => {
    render(<App dataSource={new FakeDataSource()} />);
    expect(
      await screen.findByRole("heading", { name: "Test dataset" }),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/1 questions · 2 subjects · 1 judges/),
    ).toBeInTheDocument();
  });

  it("shows a fail-soft message when the source errors", async () => {
    render(<App dataSource={new FailingDataSource()} />);
    expect(await screen.findByRole("alert")).toHaveTextContent("boom");
  });
});
