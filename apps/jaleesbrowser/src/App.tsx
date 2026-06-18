import { useCallback, useEffect, useRef, useState } from "react";
import { BandLegend } from "./components/BandLegend";
import { Compare } from "./components/Compare";
import { Comparison } from "./components/Comparison";
import { IntroPanel } from "./components/IntroPanel";
import { ItemHeader } from "./components/ItemHeader";
import { Pickers } from "./components/Pickers";
import { Presets } from "./components/Presets";
import { ThemeToggle } from "./components/ThemeToggle";
import type { ContractIndex, ItemShard } from "./contract";
import type { DataSource } from "./datasource";
import { type DivergenceRow, defaultScopeId } from "./scores";
import { decodeSelection, encodeSelection, type Selection, type View } from "./urlstate";

/**
 * The application root: loads the index via the injected DataSource, drives the
 * pickers + URL deep-link state, lazily loads the selected probe's shard (cached
 * by item id), and renders the side-by-side comparison. Every load failure is
 * fail-soft (a visible message, never a blank page).
 *
 * The UI depends ONLY on the `DataSource` interface (injected by `main.tsx`).
 */
export function App({ dataSource }: { dataSource: DataSource }) {
  const [index, setIndex] = useState<ContractIndex | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [selection, setSelection] = useState<Selection | null>(null);
  const [shard, setShard] = useState<ItemShard | null>(null);
  const [shardError, setShardError] = useState<string | null>(null);
  const shardCache = useRef<Map<string, ItemShard>>(new Map());

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

  // Lazily load the selected probe's shard (cached by item id; one shard holds
  // every subject × condition cell, so switching subjects/conditions never refetches).
  // Only in the detail view — compare ranks from the index alone, no shard loads.
  const itemId = selection?.item;
  const isDetail = selection?.view === "detail";
  useEffect(() => {
    if (!index || !itemId || !isDetail) return;
    let cancelled = false;
    setShardError(null);
    const cached = shardCache.current.get(itemId);
    if (cached) {
      setShard(cached);
      return;
    }
    setShard(null);
    dataSource
      .loadItem(itemId)
      .then((s) => {
        if (cancelled) return;
        shardCache.current.set(itemId, s);
        setShard(s);
      })
      .catch((e) => !cancelled && setShardError(e instanceof Error ? e.message : String(e)));
    return () => {
      cancelled = true;
    };
  }, [index, itemId, isDetail, dataSource]);

  const onChange = useCallback(
    (next: Selection) => {
      setSelection(next);
      if (index) {
        window.history.replaceState(null, "", encodeSelection(next, index));
      }
    },
    [index],
  );

  // A compare row → the drill-in detail for that exact cell (same A/B). Open at
  // the scope the ranking used (the default scope) so the detail is consistent
  // with the divergence the user clicked, regardless of any prior scope.
  const onOpenDetail = useCallback(
    (row: DivergenceRow) => {
      if (!selection || !index) return;
      const scope = defaultScopeId(index);
      onChange({
        ...selection,
        view: "detail",
        item: row.item,
        conditions: row.conditions,
        ...(scope !== undefined ? { scope } : {}),
      });
    },
    [selection, index, onChange],
  );

  const setView = useCallback(
    (view: View) => selection && onChange({ ...selection, view }),
    [selection, onChange],
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

  const dir = (index.dataset.language ?? "en").toLowerCase().startsWith("ar")
    ? "rtl"
    : "ltr";

  return (
    <main dir={dir}>
      <header className="app-header">
        <h1>{index.dataset.title}</h1>
        <ThemeToggle />
      </header>

      <IntroPanel paper={index.paper} />

      <nav className="mode-toggle" aria-label="View mode">
        <button
          type="button"
          aria-pressed={selection.view === "detail"}
          onClick={() => setView("detail")}
        >
          Detail
        </button>
        <button
          type="button"
          aria-pressed={selection.view === "compare"}
          onClick={() => setView("compare")}
        >
          Compare
        </button>
      </nav>

      <Presets index={index} onApply={onChange} />

      {selection.view === "compare" ? (
        <Compare
          index={index}
          selection={selection}
          onChange={onChange}
          onOpenDetail={onOpenDetail}
        />
      ) : (
        <>
          <Pickers index={index} selection={selection} onChange={onChange} />
          <BandLegend index={index} />
          {shardError ? (
            <p className="shard-error no-data" role="alert">
              Could not load this question’s data: {shardError}
            </p>
          ) : !shard ? (
            <p>Loading responses…</p>
          ) : (
            <>
              <ItemHeader shard={shard} />
              <Comparison index={index} shard={shard} selection={selection} />
            </>
          )}
        </>
      )}
    </main>
  );
}
