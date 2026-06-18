import type { ContractIndex } from "../contract";
import { decodeSelection, type Selection } from "../urlstate";

/**
 * Guided presets — curated deep-links from `index.presets`, compact for the
 * sidebar (collapsed by default). Each entry's flat param map is fed through the
 * same URL decoder, so applying a preset is just a validated Selection.
 */
export function Presets({
  index,
  onApply,
}: {
  index: ContractIndex;
  onApply: (sel: Selection) => void;
}) {
  const presets = index.presets ?? [];
  if (presets.length === 0) return null;
  return (
    <details className="presets">
      <summary>Guided examples</summary>
      <div className="presets-body" aria-label="Guided examples">
        {presets.map((preset) => (
          <div key={preset.key} className="preset-group">
            <p className="preset-head">
              <strong>{preset.label}</strong>
              {preset.description ? (
                <span className="preset-desc"> — {preset.description}</span>
              ) : null}
            </p>
            <ul>
              {preset.entries.map((entry, i) => (
                <li key={`${preset.key}-${i}`}>
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
      </div>
    </details>
  );
}

function paramsToSelection(
  params: Record<string, string>,
  index: ContractIndex,
): Selection {
  return decodeSelection(`?${new URLSearchParams(params).toString()}`, index);
}
