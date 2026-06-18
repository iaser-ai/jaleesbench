import { afterEach, beforeAll, describe, expect, it, vi } from "vitest";
import type { ContractIndex, ItemShard } from "./contract";
import { StaticFileDataSource, UnsupportedVersionError } from "./datasource";
import realIndex from "../public/data/index.json";

/** Gzip a string using the web CompressionStream (symmetric to the
 * DataSource's DecompressionStream) — keeps the test free of Node-only APIs. */
async function gzipText(text: string): Promise<ArrayBuffer> {
  const stream = new Response(text).body!.pipeThrough(new CompressionStream("gzip"));
  return new Response(stream).arrayBuffer();
}

const INDEX: ContractIndex = {
  contractVersion: "1.0",
  producer: { name: "test", version: "0" },
  dataset: { title: "Test dataset", language: "en" },
  bands: [
    { value: -1, label: "Low" },
    { value: 1, label: "High" },
  ],
  subjects: [
    { id: "a", label: "A" },
    { id: "b", label: "B" },
  ],
  conditionAxes: [
    { key: "pressure", label: "Pressure", values: [{ id: "x", label: "X" }] },
  ],
  judges: [{ id: "j1", label: "J1" }],
  scopes: [{ id: "full", label: "Full", default: true }],
  items: [{ id: "JLS-001", title: "First" }],
  shards: { "JLS-001": "probes/JLS-001.json.gz" },
};

const SHARD: ItemShard = {
  item: { id: "JLS-001", title: "First" },
  cells: [
    {
      subject: "a",
      conditions: { pressure: "x" },
      transcript: [{ role: "user", content: "hi" }],
      verdicts: [{ judge: "j1", scope: "full", band: 1, bandLabel: "High" }],
    },
  ],
};

let shardGz: ArrayBuffer;
beforeAll(async () => {
  shardGz = await gzipText(JSON.stringify(SHARD));
});

function json(obj: unknown, status = 200): Response {
  return new Response(JSON.stringify(obj), { status });
}
function gz(): Response {
  return new Response(shardGz, { status: 200 });
}

/** A fetch stub that routes by substring of the requested URL. */
function routeFetch(handlers: Record<string, () => Response>) {
  return vi.fn((input: RequestInfo | URL) => {
    const url = String(input);
    for (const [needle, make] of Object.entries(handlers)) {
      if (url.includes(needle)) return Promise.resolve(make());
    }
    return Promise.resolve(new Response("not found", { status: 404 }));
  });
}

describe("StaticFileDataSource", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("loads and version-checks the index", async () => {
    vi.stubGlobal("fetch", routeFetch({ "index.json": () => json(INDEX) }));
    const idx = await new StaticFileDataSource().loadIndex();
    expect(idx.subjects).toHaveLength(2);
    expect(idx.shards["JLS-001"]).toBe("probes/JLS-001.json.gz");
  });

  it("throws UnsupportedVersionError on a MAJOR mismatch", async () => {
    vi.stubGlobal(
      "fetch",
      routeFetch({ "index.json": () => json({ ...INDEX, contractVersion: "2.0" }) }),
    );
    await expect(new StaticFileDataSource().loadIndex()).rejects.toBeInstanceOf(
      UnsupportedVersionError,
    );
  });

  it("rejects on malformed index JSON", async () => {
    vi.stubGlobal(
      "fetch",
      routeFetch({ "index.json": () => new Response("{ not json", { status: 200 }) }),
    );
    await expect(new StaticFileDataSource().loadIndex()).rejects.toThrow();
  });

  it("rejects on a non-OK index response", async () => {
    vi.stubGlobal(
      "fetch",
      routeFetch({ "index.json": () => new Response("nope", { status: 500 }) }),
    );
    await expect(new StaticFileDataSource().loadIndex()).rejects.toThrow(/HTTP 500/);
  });

  it("loads and gunzips a shard, resolving the path against the base", async () => {
    const fetchMock = routeFetch({
      "index.json": () => json(INDEX),
      "JLS-001.json.gz": () => gz(),
    });
    vi.stubGlobal("fetch", fetchMock);
    const shard = await new StaticFileDataSource("./data/").loadItem("JLS-001");
    expect(shard.item.id).toBe("JLS-001");
    expect(shard.cells[0].subject).toBe("a");
    expect(shard.cells[0].verdicts[0].bandLabel).toBe("High");
    // baseUrl "./data/" + relative shard "probes/…" must resolve under /data/probes/.
    const shardUrl = String(
      fetchMock.mock.calls.find((c) => String(c[0]).includes(".json.gz"))?.[0],
    );
    expect(shardUrl).toMatch(/\/data\/probes\/JLS-001\.json\.gz$/);
  });

  it("loads a shard the host already decompressed (Content-Encoding: gzip)", async () => {
    // Some hosts serve `.gz` with Content-Encoding: gzip, so fetch returns plain
    // JSON; the DataSource must NOT try to gunzip it again.
    vi.stubGlobal(
      "fetch",
      routeFetch({
        "index.json": () => json(INDEX),
        "JLS-001.json.gz": () => json(SHARD),
      }),
    );
    const shard = await new StaticFileDataSource("./data/").loadItem("JLS-001");
    expect(shard.item.id).toBe("JLS-001");
    expect(shard.cells[0].verdicts[0].bandLabel).toBe("High");
  });

  it("throws for an unknown item id", async () => {
    vi.stubGlobal("fetch", routeFetch({ "index.json": () => json(INDEX) }));
    await expect(new StaticFileDataSource().loadItem("NOPE")).rejects.toThrow(
      /No shard/,
    );
  });

  it("the committed fixture matches the contract (v1, relative probes/ paths)", () => {
    expect(realIndex.contractVersion.split(".")[0]).toBe("1");
    const paths = Object.values(realIndex.shards);
    expect(paths.length).toBeGreaterThan(0);
    for (const p of paths) {
      expect(p).toMatch(/^probes\//); // relative to index.json, no leading slash
    }
  });
});
