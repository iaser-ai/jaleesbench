import { useCallback, useEffect, useRef, useState } from "react";
import { Comparison } from "./components/Comparison";
import { IntroPanel } from "./components/IntroPanel";
import { ItemHeader } from "./components/ItemHeader";
import { Pickers } from "./components/Pickers";
import { Presets } from "./components/Presets";
import { ThemeToggle } from "./components/ThemeToggle";
import type { ContractIndex, ItemShard } from "./contract";
import type { DataSource } from "./datasource";
import { decodeSelection, encodeSelection, type Selection } from "./urlstate";

/**
 * The application root: loads the index via the injected DataSource, drives the
 * selectors + URL deep-link state, lazily loads the selected probe's shard
 * (cached by item id), and renders the side-by-side comparison. Every load
 * failure is fail-soft (a visible message, never a blank page).
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
  const itemId = selection?.item;
  useEffect(() => {
    if (!index || !itemId) return;
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
  }, [index, itemId, dataSource]);

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

  const dir = (index.dataset.language ?? "en").toLowerCase().startsWith("ar")
    ? "rtl"
    : "ltr";

  return (
    <main dir={dir} className="app-shell">
      <aside className="sidebar">
        <header className="app-header">
          <h1>{index.dataset.title}</h1>
          <ThemeToggle />
        </header>

        <IntroPanel index={index} />

        <Pickers index={index} selection={selection} onChange={onChange} />

        <Presets index={index} onApply={onChange} />
      </aside>

      <section className="content">
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
      </section>
    </main>
  );
}
