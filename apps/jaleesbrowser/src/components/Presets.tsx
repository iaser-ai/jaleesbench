import type { ContractIndex } from "../contract";
import { decodeSelection, type Selection } from "../urlstate";

/**
 * Guided presets — curated deep-links from `index.presets`. Each entry's flat
 * param map is fed through the same URL decoder, so applying a preset is just a
 * validated Selection (axis keys stay generic).
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
    <section className="presets" aria-label="Guided examples">
      <h3>Guided examples</h3>
      {presets.map((preset) => (
        <div key={preset.key} className="preset-group">
          <strong>{preset.label}</strong>
          {preset.description && <p className="preset-desc">{preset.description}</p>}
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
    </section>
  );
}

function paramsToSelection(
  params: Record<string, string>,
  index: ContractIndex,
): Selection {
  return decodeSelection(`?${new URLSearchParams(params).toString()}`, index);
}
