import { useCallback, useEffect, useState } from "react";
import { Pickers } from "./components/Pickers";
import type { ContractIndex } from "./contract";
import type { DataSource } from "./datasource";
import { decodeSelection, encodeSelection, type Selection } from "./urlstate";

/**
 * Loads the index via the injected DataSource, then drives the pickers and the
 * URL deep-link state. The selection (question, two models, condition axes,
 * scope) lives in the URL so every view is shareable. Phase 4 replaces the
 * selection summary with the side-by-side comparison.
 *
 * The UI depends ONLY on the `DataSource` interface (injected by `main.tsx`).
 */
export function App({ dataSource }: { dataSource: DataSource }) {
  const [index, setIndex] = useState<ContractIndex | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [selection, setSelection] = useState<Selection | null>(null);

  useEffect(() => {
    let cancelled = false;
    dataSource
      .loadIndex()
      .then((idx) => {
        if (cancelled) return;
        setIndex(idx);
        setSelection(decodeSelection(window.location.search, idx));
      })
      .catch((e) => !cancelled && setError(e instanceof Error ? e.message : String(e)));
    return () => {
      cancelled = true;
    };
  }, [dataSource]);

  // Restore the selection on browser back/forward.
  useEffect(() => {
    if (!index) return;
    const onPop = () => setSelection(decodeSelection(window.location.search, index));
    window.addEventListener("popstate", onPop);
    return () => window.removeEventListener("popstate", onPop);
  }, [index]);

  const onChange = useCallback(
    (next: Selection) => {
      setSelection(next);
      if (index) {
        window.history.replaceState(null, "", encodeSelection(next, index));
      }
    },
    [index],
  );

  if (error) {
    return (
      <main>
        <p role="alert">Could not load results: {error}</p>
      </main>
    );
  }
  if (!index || !selection) {
    return (
      <main>
        <p>Loading…</p>
      </main>
    );
  }

  return (
    <main>
      <h1>{index.dataset.title}</h1>
      <Pickers index={index} selection={selection} onChange={onChange} />
      <p className="selection-summary">
        Comparing <strong>{subjectLabel(index, selection.a)}</strong> vs{" "}
        <strong>{subjectLabel(index, selection.b)}</strong> on{" "}
        <strong>{selection.item}</strong>
        {index.conditionAxes.map((axis) => (
          <span key={axis.key}>
            {" "}
            · {axis.label}: {axisValueLabel(index, axis.key, selection.conditions[axis.key])}
          </span>
        ))}
      </p>
    </main>
  );
}

function subjectLabel(index: ContractIndex, id: string): string {
  return index.subjects.find((s) => s.id === id)?.label ?? id;
}

function axisValueLabel(index: ContractIndex, key: string, valueId: string | undefined): string {
  const axis = index.conditionAxes.find((a) => a.key === key);
  return axis?.values.find((v) => v.id === valueId)?.label ?? valueId ?? "—";
}
