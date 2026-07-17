import { useMemo, useState } from "react";
import type { ContractIndex } from "../contract";
import { sortedBands } from "../format";
import { breakdownAxis, computeLeaderboard, type LeaderboardRow } from "../leaderboard";
import { defaultScopeId } from "../scores";

/**
 * The leaderboard view: one row per subject, ranked by the canonical ordering
 * (first breakdown-axis value at the post scope — Unstated post-pressure for
 * JaleesBench). Columns are click-to-sort; the Rank column always shows the
 * CANONICAL rank, so re-sorting never re-numbers the ranking. Clicking a model
 * jumps into the detail view for that subject. Generic over the contract —
 * every label (scopes, axis values, band endpoints) comes from the index.
 */

type SortKey = "initial" | "post" | "delta" | number; // number = byValue index

function fmt(v: number | null): string {
  if (v === null) return "—";
  return (v > 0 ? "+" : "") + v.toFixed(2);
}

function sortValue(r: LeaderboardRow, key: SortKey): number | null {
  if (key === "initial") return r.initial;
  if (key === "post") return r.post;
  if (key === "delta") return r.delta;
  return r.byValue[key] ?? null;
}

export function Leaderboard({
  index,
  onOpenSubject,
}: {
  index: ContractIndex;
  onOpenSubject: (subject: string) => void;
}) {
  const rows = useMemo(() => computeLeaderboard(index), [index]);
  const axis = breakdownAxis(index);
  // null = the canonical order computeLeaderboard returns; dir −1 = descending.
  const [sort, setSort] = useState<{ key: SortKey; dir: 1 | -1 } | null>(null);

  const canonicalRank = useMemo(
    () => new Map(rows.map((r, i) => [r.subject, i + 1])),
    [rows],
  );

  const sorted = useMemo(() => {
    if (!sort) return rows;
    return [...rows].sort((x, y) => {
      const vx = sortValue(x, sort.key);
      const vy = sortValue(y, sort.key);
      if (vx === null || vy === null) return vx === null ? (vy === null ? 0 : 1) : -1;
      return (vy - vx) * (sort.dir === -1 ? 1 : -1);
    });
  }, [rows, sort]);

  if (rows.length === 0) {
    return <p className="no-data">This dataset ships no score summary to rank.</p>;
  }

  const scopes = index.scopes ?? [];
  const postId = defaultScopeId(index);
  const postLabel = scopes.find((s) => s.id === postId)?.label ?? "overall";
  const initialLabel = scopes.find((s) => s.id !== postId)?.label ?? "initial";
  const bands = sortedBands(index);
  const lo = bands[0];
  const hi = bands[bands.length - 1];
  const rankColumn = axis?.values[0];

  const toggle = (key: SortKey) =>
    setSort((cur) =>
      cur && cur.key === key ? { key, dir: cur.dir === -1 ? 1 : -1 } : { key, dir: -1 },
    );

  const header = (key: SortKey, label: string) => (
    <th
      key={String(key)}
      aria-sort={sort?.key === key ? (sort.dir === -1 ? "descending" : "ascending") : undefined}
    >
      <button type="button" className="lb-sort" onClick={() => toggle(key)}>
        {label}
        {sort?.key === key ? (sort.dir === -1 ? " ↓" : " ↑") : ""}
      </button>
    </th>
  );

  return (
    <section className="leaderboard">
      <h2>Leaderboard</h2>
      <p className="compare-caption">
        Mean judged band on the {fmt(lo?.value ?? null)}…{fmt(hi?.value ?? null)} scale
        {lo && hi ? ` (${lo.label} … ${hi.label})` : ""}. Ranked by the{" "}
        {rankColumn?.label ?? postLabel} {postLabel} score
        {axis ? `; the ${axis.label} columns break down the ${postLabel} score` : ""}.
        Δ is {postLabel} − {initialLabel}. Click a model to browse its responses.
      </p>
      <table className="compare-table leaderboard-table">
        <thead>
          <tr>
            <th>#</th>
            <th>Model</th>
            {header("initial", initialLabel)}
            {header("post", postLabel)}
            {header("delta", "Δ")}
            {(axis?.values ?? []).map((v, i) => header(i, v.label))}
          </tr>
        </thead>
        <tbody>
          {sorted.map((r) => (
            <tr key={r.subject}>
              <td className="lb-rank">{canonicalRank.get(r.subject)}</td>
              <td>
                <button
                  type="button"
                  className="lb-subject"
                  onClick={() => onOpenSubject(r.subject)}
                  title="Browse this model's responses"
                >
                  {r.label}
                </button>
              </td>
              <td>{fmt(r.initial)}</td>
              <td>{fmt(r.post)}</td>
              <td>{fmt(r.delta)}</td>
              {r.byValue.map((v, i) => (
                <td key={i}>{fmt(v)}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}
