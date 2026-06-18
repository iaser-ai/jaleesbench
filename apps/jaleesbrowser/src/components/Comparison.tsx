import { type ReactNode, useMemo } from "react";
import type { Cell, ContractIndex, ItemShard, Turn } from "../contract";
import { cellKey, indexCells, meanBandAtScope, signed } from "../format";
import type { Selection } from "../urlstate";
import { Collapsible } from "./Collapsible";
import { Markdown } from "./Markdown";
import { Verdicts } from "./Verdicts";

/**
 * Side-by-side comparison of two models, laid out in conversation order:
 *   - shared USER prompts (question, then pressure) are rendered ONCE, full-width
 *     (both models got the identical prompt);
 *   - the two assistant responses sit side-by-side;
 *   - the judges' verdict on the FIRST response (initial scope) appears right
 *     after it, and the verdict AFTER the pressure (post scope) appears after the
 *     pressure exchange.
 * A missing cell renders a fail-soft "no data" state on its side.
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
  const labelA = subjectLabel(index, selection.a);
  const labelB = subjectLabel(index, selection.b);
  const maxTurns = Math.max(
    cellA?.transcript.length ?? 0,
    cellB?.transcript.length ?? 0,
  );

  // Default scope = the post-pressure judgment; the other = the initial
  // (first-response) judgment. Labels come from the data, not hardcoded.
  const postScope = (index.scopes ?? []).find((s) => s.default) ?? index.scopes?.[0];
  const initialScope = (index.scopes ?? []).find((s) => s.id !== postScope?.id);

  const roleAt = (i: number) => cellA?.transcript[i]?.role ?? cellB?.transcript[i]?.role;
  const assistantIdx: number[] = [];
  for (let i = 0; i < maxTurns; i++) if (roleAt(i) === "assistant") assistantIdx.push(i);
  const firstAssistant = assistantIdx[0];
  const lastAssistant = assistantIdx[assistantIdx.length - 1];

  const verdictStage = (scope: { id: string; label?: string } | undefined, key: string) =>
    scope === undefined ? null : (
      <div className="verdict-stage" key={key}>
        <p className="verdict-stage-label">Judges — {scope.label ?? scope.id}</p>
        <div className="cmp-row">
          <div className="column-verdicts">
            {cellA ? (
              <Verdicts index={index} cell={cellA} scope={scope.id} />
            ) : (
              <p className="no-data">No data.</p>
            )}
          </div>
          <div className="column-verdicts">
            {cellB ? (
              <Verdicts index={index} cell={cellB} scope={scope.id} />
            ) : (
              <p className="no-data">No data.</p>
            )}
          </div>
        </div>
      </div>
    );

  const rows: ReactNode[] = [
    <div className="cmp-row cmp-headers" key="headers">
      <ColumnHeader index={index} label={labelA} cell={cellA} />
      <ColumnHeader index={index} label={labelB} cell={cellB} />
    </div>,
  ];
  for (let i = 0; i < maxTurns; i++) {
    if (roleAt(i) === "user") {
      const turn = cellA?.transcript[i] ?? cellB?.transcript[i];
      rows.push(<SharedTurn key={`t${i}`} turn={turn} />);
    } else {
      rows.push(
        <div className="cmp-row" key={`t${i}`}>
          <TurnCell turn={cellA?.transcript[i]} />
          <TurnCell turn={cellB?.transcript[i]} />
        </div>,
      );
      if (i === firstAssistant) rows.push(verdictStage(initialScope, `v-init-${i}`));
      if (i === lastAssistant) rows.push(verdictStage(postScope, `v-post-${i}`));
    }
  }

  return <div className="comparison">{rows}</div>;
}

function ColumnHeader({
  index,
  label,
  cell,
}: {
  index: ContractIndex;
  label: string;
  cell?: Cell;
}) {
  const postScope = (index.scopes ?? []).find((s) => s.default) ?? index.scopes?.[0];
  const initialScope = (index.scopes ?? []).find((s) => s.id !== postScope?.id);
  const initial = cell && initialScope ? meanBandAtScope(cell, initialScope.id) : null;
  const post = cell && postScope ? meanBandAtScope(cell, postScope.id) : null;

  return (
    <header className="column-header">
      <span className="column-model">{label}</span>
      {cell ? (
        <span className="column-score">
          {" ("}
          {initial !== null ? `${signed(initial)} ${initialScope?.label ?? ""}` : "—"}
          {" → "}
          {post !== null ? `${signed(post)} ${postScope?.label ?? ""}` : "—"}
          {")"}
        </span>
      ) : (
        <span className="no-data-tag"> · no data</span>
      )}
    </header>
  );
}

function SharedTurn({ turn }: { turn?: Turn }) {
  if (!turn) return null;
  return (
    <div className="turn turn-user shared-turn">
      <span className="turn-role">User</span>
      <Collapsible>
        <Markdown text={turn.content} className="turn-content" />
      </Collapsible>
    </div>
  );
}

function TurnCell({ turn }: { turn?: Turn }) {
  if (!turn) {
    return <div className="turn turn-empty" aria-hidden="true" />;
  }
  return (
    <div className={`turn turn-${turn.role}`}>
      <span className="turn-role">{turn.role === "user" ? "User" : "Assistant"}</span>
      <Collapsible>
        <Markdown text={turn.content} className="turn-content" />
      </Collapsible>
    </div>
  );
}

function subjectLabel(index: ContractIndex, id: string): string {
  return index.subjects.find((s) => s.id === id)?.label ?? id;
}
