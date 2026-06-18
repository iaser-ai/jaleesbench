import { useCallback, useEffect, useRef, useState } from "react";
import { BandLegend } from "./components/BandLegend";
import { Comparison } from "./components/Comparison";
import { DivergentCases } from "./components/DivergentCases";
import { IntroPanel } from "./components/IntroPanel";
import { ItemHeader } from "./components/ItemHeader";
import { ModelStats } from "./components/ModelStats";
import { Presets } from "./components/Presets";
import { ThemeToggle } from "./components/ThemeToggle";
import type { ContractIndex, ItemShard } from "./contract";
import type { DataSource } from "./datasource";
import { type DivergenceRow, defaultScopeId } from "./scores";
import { decodeSelection, encodeSelection, isDetail, type Selection } from "./urlstate";

/**
 * Two-pane shell: a left sidebar holds the controls (Model A/B, scope, presets,
 * theme, a small "about"); the main pane is one continuous flow — A-vs-B aggregate
 * stats and the most-divergent-cases list, and (when a row is opened) that cell's
 * drill-in detail with a "back". No Detail/Compare tabs; the surface is derived
 * from whether a cell is open. The UI depends only on the `DataSource` interface.
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

  useEffect(() => {
    if (!index) return;
    const onPop = () => setSelection(decodeSelection(window.location.search, index));
    window.addEventListener("popstate", onPop);
    return () => window.removeEventListener("popstate", onPop);
  }, [index]);

  // Load the open cell's shard (cached). Only when a cell is open — the stats +
  // divergence list compute from the index alone, no shard loads.
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

  const setControl = useCallback(
    (patch: Partial<Selection>) => selection && onChange({ ...selection, ...patch }),
    [selection, onChange],
  );

  const onPick = useCallback(
    (row: DivergenceRow) => {
      if (!selection || !index) return;
      onChange({
        ...selection,
        item: row.item,
        conditions: row.conditions,
        scope: selection.scope ?? defaultScopeId(index),
      });
    },
    [selection, index, onChange],
  );

  const onBack = useCallback(() => {
    if (selection) onChange({ ...selection, item: undefined });
  }, [selection, onChange]);

  if (error) {
    return (
      <div className="app">
        <main className="main">
          <p role="alert">Could not load results: {error}</p>
        </main>
      </div>
    );
  }
  if (!index || !selection) {
    return (
      <div className="app">
        <main className="main">
          <p>Loading…</p>
        </main>
      </div>
    );
  }

  const dir = (index.dataset.language ?? "en").toLowerCase().startsWith("ar")
    ? "rtl"
    : "ltr";

  return (
    <div className="app" dir={dir}>
      <aside className="sidebar">
        <div className="sidebar-head">
          <h1>{index.dataset.title}</h1>
          <ThemeToggle />
        </div>
        <p className="subtitle">
          Compare two models and find where they differ — then read the transcripts and
          judge verdicts.
        </p>
        <div className="controls">
          <label className="picker">
            <span>Model A</span>
            <select
              aria-label="Model A"
              value={selection.a}
              onChange={(e) => setControl({ a: e.target.value })}
            >
              {index.subjects.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.label}
                </option>
              ))}
            </select>
          </label>
          <label className="picker">
            <span>Model B</span>
            <select
              aria-label="Model B"
              value={selection.b}
              onChange={(e) => setControl({ b: e.target.value })}
            >
              {index.subjects.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.label}
                </option>
              ))}
            </select>
          </label>
          {index.scopes && index.scopes.length > 0 && selection.scope !== undefined && (
            <label className="picker">
              <span>Scope</span>
              <select
                aria-label="Scope"
                value={selection.scope}
                onChange={(e) => setControl({ scope: e.target.value })}
              >
                {index.scopes.map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.label}
                  </option>
                ))}
              </select>
            </label>
          )}
        </div>
        <Presets index={index} onApply={onChange} />
        <IntroPanel index={index} />
      </aside>

      <main className="main">
        {isDetail(selection) ? (
          shardError ? (
            <p className="no-data shard-error" role="alert">
              Could not load this question’s data: {shardError}
            </p>
          ) : !shard ? (
            <p>Loading responses…</p>
          ) : (
            <>
              <button type="button" className="back" onClick={onBack}>
                ← Back to comparison
              </button>
              <ItemHeader shard={shard} />
              <BandLegend index={index} />
              <Comparison index={index} shard={shard} selection={selection} />
            </>
          )
        ) : (
          <>
            <ModelStats index={index} a={selection.a} b={selection.b} />
            <DivergentCases
              index={index}
              a={selection.a}
              b={selection.b}
              onPick={onPick}
            />
          </>
        )}
      </main>
    </div>
  );
}
