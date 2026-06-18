import type { ContractIndex } from "../contract";
import { bandColor, signed, sortedBands } from "../format";

/** A colored band chip with its label + signed value (color is never the only cue). */
export function BandChip({
  index,
  value,
  label,
}: {
  index: ContractIndex;
  value: number;
  label: string;
}) {
  return (
    <span className="band-chip" style={{ backgroundColor: bandColor(index, value) }}>
      {label} ({signed(value)})
    </span>
  );
}

/** The band ladder, explained from the data (low → high). */
export function BandLegend({ index }: { index: ContractIndex }) {
  return (
    <div className="band-legend" aria-label="Band legend">
      {sortedBands(index).map((b) => (
        <span className="legend-item" key={b.value}>
          <span
            className="legend-swatch"
            style={{ backgroundColor: bandColor(index, b.value) }}
            aria-hidden="true"
          />
          {b.label} ({signed(b.value)})
        </span>
      ))}
    </div>
  );
}
