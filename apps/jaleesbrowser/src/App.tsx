import { useEffect, useState } from "react";
import type { ContractIndex } from "./contract";
import { type DataSource, StaticFileDataSource } from "./datasource";

const defaultDataSource: DataSource = new StaticFileDataSource();

/**
 * Phase 2 smoke shell: load the index via the DataSource and report counts. The
 * pickers (Phase 3) and the side-by-side comparison (Phase 4) build on this.
 */
export function App({ dataSource = defaultDataSource }: { dataSource?: DataSource }) {
  const [index, setIndex] = useState<ContractIndex | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    dataSource
      .loadIndex()
      .then((idx) => !cancelled && setIndex(idx))
      .catch((e) => !cancelled && setError(e instanceof Error ? e.message : String(e)));
    return () => {
      cancelled = true;
    };
  }, [dataSource]);

  if (error) {
    return (
      <main>
        <p role="alert">Could not load results: {error}</p>
      </main>
    );
  }
  if (!index) {
    return (
      <main>
        <p>Loading…</p>
      </main>
    );
  }
  return (
    <main>
      <h1>{index.dataset.title}</h1>
      <p>
        {index.items.length} questions · {index.subjects.length} subjects ·{" "}
        {index.judges.length} judges
      </p>
    </main>
  );
}
