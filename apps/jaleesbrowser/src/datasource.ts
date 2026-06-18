/**
 * The data-source seam (plan D1). The UI depends ONLY on the `DataSource`
 * interface — it never calls `fetch` directly — so a future DB/API-backed source
 * is a localized drop-in (one new class implementing these two methods) with no
 * UI change. The only implementation today is `StaticFileDataSource`. There is
 * deliberately NO DB adapter, API client, or query layer (YAGNI).
 */

import { CONTRACT_MAJOR, type ContractIndex, type ItemShard } from "./contract";

/** Thrown when the data's contract MAJOR version the viewer can't render. */
export class UnsupportedVersionError extends Error {
  constructor(public readonly version: string) {
    super(
      `Unsupported data contract version ${version} ` +
        `(this viewer supports ${CONTRACT_MAJOR}.x)`,
    );
    this.name = "UnsupportedVersionError";
  }
}

export interface DataSource {
  loadIndex(): Promise<ContractIndex>;
  loadItem(itemId: string): Promise<ItemShard>;
}

function majorOf(version: string): number {
  return Number.parseInt(version.split(".")[0] ?? "", 10);
}

/**
 * Reads a static export over HTTP: plain `index.json` + gzip-compressed
 * `*.json.gz` shards, decompressed client-side with `DecompressionStream`.
 * Paths resolve relative to `baseUrl` (relative to the document base), so the
 * same build works under any host subpath.
 */
export class StaticFileDataSource implements DataSource {
  private index?: ContractIndex;

  constructor(private readonly baseUrl: string = "./data/") {}

  private resolve(rel: string): string {
    const base = new URL(this.baseUrl, document.baseURI);
    return new URL(rel, base).href;
  }

  async loadIndex(): Promise<ContractIndex> {
    const res = await fetch(this.resolve("index.json"));
    if (!res.ok) {
      throw new Error(`Failed to load index.json (HTTP ${res.status})`);
    }
    const index = (await res.json()) as ContractIndex;
    if (majorOf(index.contractVersion) !== CONTRACT_MAJOR) {
      throw new UnsupportedVersionError(index.contractVersion);
    }
    this.index = index;
    return index;
  }

  async loadItem(itemId: string): Promise<ItemShard> {
    const index = this.index ?? (await this.loadIndex());
    const rel = index.shards[itemId];
    if (!rel) {
      throw new Error(`No shard for item "${itemId}"`);
    }
    const res = await fetch(this.resolve(rel));
    if (!res.ok || !res.body) {
      throw new Error(`Failed to load shard ${rel} (HTTP ${res.status})`);
    }
    // Shards are gzip-compressed; decompress in the browser/runtime.
    const stream = res.body.pipeThrough(new DecompressionStream("gzip"));
    const text = await new Response(stream).text();
    return JSON.parse(text) as ItemShard;
  }
}
