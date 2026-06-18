import { useMemo, useState } from "react";
import type { ContractIndex } from "../contract";
import { signed } from "../format";
import { type DivergenceRow, divergenceRanking } from "../scores";
import type { Selection } from "../urlstate";

const TOP_N = 50;

/**
 * Two models, A vs B, with the questions/conditions where they differ most. The
 * ranking is computed instantly from the index's score blob — no shard loads. A
 * row click opens the drill-in detail for that exact cell.
 */
export function Compare({
  index,
  selection,
  onChange,
  onOpenDetail,
}: {
  index: ContractIndex;
  selection: Selection;
  onChange: (next: Selection) => void;
  onOpenDetail: (row: DivergenceRow) => void;
}) {
  const [showAll, setShowAll] = useState(false);
  const rows = useMemo(
    () => divergenceRanking(index, selection.a, selection.b),
    [index, selection.a, selection.b],
  );
  const shown = showAll ? rows : rows.slice(0, TOP_N);
  const labelA = subjectLabel(index, selection.a);
  const labelB = subjectLabel(index, selection.b);

  return (
    <section className="compare">
      <div className="compare-pickers">
        <label className="picker">
          <span>Model A</span>
          <select
            value={selection.a}
            onChange={(e) => onChange({ ...selection, a: e.target.value })}
            aria-label="Model A"
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
            value={selection.b}
            onChange={(e) => onChange({ ...selection, b: e.target.value })}
            aria-label="Model B"
          >
            {index.subjects.map((s) => (
              <option key={s.id} value={s.id}>
                {s.label}
              </option>
            ))}
          </select>
        </label>
      </div>

      {rows.length === 0 ? (
        <p className="no-data">No comparable scores for this pair.</p>
      ) : (
        <>
          <p className="compare-caption">
            Questions where <strong>{labelA}</strong> and <strong>{labelB}</strong>{" "}
            differ most ({rows.length} cells):
          </p>
          <table className="compare-table">
            <thead>
              <tr>
                <th>Question</th>
                {index.conditionAxes.map((ax) => (
                  <th key={ax.key}>{ax.label}</th>
                ))}
                <th>{labelA}</th>
                <th>{labelB}</th>
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
                  onClick={() => onOpenDetail(row)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" || e.key === " ") {
                      e.preventDefault();
                      onOpenDetail(row);
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
            <button
              type="button"
              className="show-more"
              onClick={() => setShowAll(true)}
            >
              Show more ({rows.length - TOP_N} more)
            </button>
          )}
        </>
      )}
    </section>
  );
}

function subjectLabel(index: ContractIndex, id: string): string {
  return index.subjects.find((s) => s.id === id)?.label ?? id;
}
function itemTitle(index: ContractIndex, id: string): string {
  const it = index.items.find((i) => i.id === id);
  return it ? `${it.id} — ${it.title}` : id;
}
function axisValueLabel(index: ContractIndex, key: string, valueId: string): string {
  const axis = index.conditionAxes.find((a) => a.key === key);
  return axis?.values.find((v) => v.id === valueId)?.label ?? valueId;
}
