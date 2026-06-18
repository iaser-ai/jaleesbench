import { useMemo, useState } from "react";
import type { ContractIndex } from "../contract";
import { signed } from "../format";
import { type DivergenceRow, divergenceRanking } from "../scores";

const TOP_N = 12;

/**
 * A compact, scannable list of the cells where the two models differ most — the
 * secondary path into the transcripts. Ranked from the score blob (no shard
 * loads); a row click opens that cell's detail.
 */
export function DivergentCases({
  index,
  a,
  b,
  onPick,
}: {
  index: ContractIndex;
  a: string;
  b: string;
  onPick: (row: DivergenceRow) => void;
}) {
  const [showAll, setShowAll] = useState(false);
  const rows = useMemo(() => divergenceRanking(index, a, b), [index, a, b]);
  if (rows.length === 0) return null;
  const shown = showAll ? rows : rows.slice(0, TOP_N);

  return (
    <section className="divergent">
      <h3>Most divergent cases</h3>
      <p className="divergent-caption">
        Where these two differ most — click a row to read the transcripts.
      </p>
      <table className="compare-table">
        <thead>
          <tr>
            <th>Question</th>
            {index.conditionAxes.map((ax) => (
              <th key={ax.key}>{ax.label}</th>
            ))}
            <th>A</th>
            <th>B</th>
            <th>Δ</th>
          </tr>
        </thead>
        <tbody>
          {shown.map((row, i) => (
            <tr
              key={`${row.item}-${i}`}
              className="compare-row"
              role="button"
              tabIndex={0}
              onClick={() => onPick(row)}
              onKeyDown={(e) => {
                if (e.key === "Enter" || e.key === " ") {
                  e.preventDefault();
                  onPick(row);
                }
              }}
            >
              <td>{itemTitle(index, row.item)}</td>
              {index.conditionAxes.map((ax) => (
                <td key={ax.key}>{axisValueLabel(index, ax.key, row.conditions[ax.key])}</td>
              ))}
              <td>{signed(row.scoreA)}</td>
              <td>{signed(row.scoreB)}</td>
              <td>{signed(row.delta)}</td>
            </tr>
          ))}
        </tbody>
      </table>
      {!showAll && rows.length > TOP_N && (
        <button type="button" className="show-more" onClick={() => setShowAll(true)}>
          Show more ({rows.length - TOP_N} more)
        </button>
      )}
    </section>
  );
}

function itemTitle(index: ContractIndex, id: string): string {
  const it = index.items.find((i) => i.id === id);
  return it ? `${it.id} — ${it.title}` : id;
}
function axisValueLabel(index: ContractIndex, key: string, valueId: string): string {
  const axis = index.conditionAxes.find((a) => a.key === key);
  return axis?.values.find((v) => v.id === valueId)?.label ?? valueId;
}
