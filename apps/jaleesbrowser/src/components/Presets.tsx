import { useMemo } from "react";
import type { ContractIndex } from "../contract";
import { computeGuided } from "../guided";
import { decodeSelection, type Selection } from "../urlstate";

/**
 * Guided example lists, computed in-app from the score blob (see guided.ts). Each
 * entry's flat param map is fed through the same URL decoder, so applying one is
 * just a validated Selection (axis keys stay generic).
 */
export function Presets({
  index,
  onApply,
}: {
  index: ContractIndex;
  onApply: (sel: Selection) => void;
}) {
  const lists = useMemo(() => computeGuided(index), [index]);
  if (lists.length === 0) return null;
  return (
    <section className="presets" aria-label="Guided examples">
      <h3>Guided examples</h3>
      {lists.map((list) => (
        <div key={list.key} className="preset-group">
          <strong>{list.label}</strong>
          {list.description && <p className="preset-desc">{list.description}</p>}
          <ul>
            {list.entries.map((entry, i) => (
              <li key={`${list.key}-${i}`}>
                <button
                  type="button"
                  className="preset-entry"
                  onClick={() => onApply(paramsToSelection(entry.params, index))}
                >
                  {entry.label}
                </button>
              </li>
            ))}
          </ul>
        </div>
      ))}
    </section>
  );
}

function paramsToSelection(
  params: Record<string, string>,
  index: ContractIndex,
): Selection {
  return decodeSelection(`?${new URLSearchParams(params).toString()}`, index);
}
