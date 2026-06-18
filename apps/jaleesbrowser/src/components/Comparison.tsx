import { useMemo } from "react";
import type { Cell, ContractIndex, ItemShard, Turn } from "../contract";
import { cellKey, indexCells } from "../format";
import type { Selection } from "../urlstate";
import { Verdicts } from "./Verdicts";

/**
 * The side-by-side comparison: two columns (Model A / Model B), each showing the
 * full transcript and the judge verdicts for the selected condition + scope.
 *
 * Layout uses a 2-column grid with CSS subgrid (styles.css) so the two columns'
 * turns row-align on desktop while the DOM stays grouped by column (clean mobile
 * stacking). A missing cell renders a fail-soft "no data" state for that column.
 */
export function Comparison({
  index,
  shard,
  selection,
}: {
  index: ContractIndex;
  shard: ItemShard;
  selection: Selection;
}) {
  const axisKeys = useMemo(
    () => index.conditionAxes.map((a) => a.key),
    [index.conditionAxes],
  );
  const cells = useMemo(() => indexCells(shard, axisKeys), [shard, axisKeys]);
  const cellA = cells.get(cellKey(selection.a, selection.conditions, axisKeys));
  const cellB = cells.get(cellKey(selection.b, selection.conditions, axisKeys));
  const maxTurns = Math.max(
    cellA?.transcript.length ?? 0,
    cellB?.transcript.length ?? 0,
  );

  // header + N turns + verdicts → explicit row tracks so the columns' subgrids align.
  const rowTracks = `repeat(${2 + maxTurns}, auto)`;

  return (
    <div className="comparison" style={{ gridTemplateRows: rowTracks }}>
      <Column
        index={index}
        label={subjectLabel(index, selection.a)}
        cell={cellA}
        maxTurns={maxTurns}
        scope={selection.scope}
      />
      <Column
        index={index}
        label={subjectLabel(index, selection.b)}
        cell={cellB}
        maxTurns={maxTurns}
        scope={selection.scope}
      />
    </div>
  );
}

function Column({
  index,
  label,
  cell,
  maxTurns,
  scope,
}: {
  index: ContractIndex;
  label: string;
  cell?: Cell;
  maxTurns: number;
  scope?: string;
}) {
  return (
    <section className="column" aria-label={`Responses from ${label}`}>
      <header className="column-header">
        {label}
        {!cell && <span className="no-data-tag"> · no data</span>}
      </header>
      {Array.from({ length: maxTurns }, (_, i) => (
        <TurnCell key={i} turn={cell?.transcript[i]} />
      ))}
      <div className="column-verdicts">
        {cell ? (
          <Verdicts index={index} cell={cell} scope={scope} />
        ) : (
          <p className="no-data">No data for this combination.</p>
        )}
      </div>
    </section>
  );
}

function TurnCell({ turn }: { turn?: Turn }) {
  if (!turn) {
    return <div className="turn turn-empty" aria-hidden="true" />;
  }
  return (
    <div className={`turn turn-${turn.role}`}>
      <span className="turn-role">{turn.role === "user" ? "User" : "Assistant"}</span>
      {/* Escaped plain text; CSS preserves line breaks. Never raw HTML. */}
      <div className="turn-content">{turn.content}</div>
    </div>
  );
}

function subjectLabel(index: ContractIndex, id: string): string {
  return index.subjects.find((s) => s.id === id)?.label ?? id;
}
