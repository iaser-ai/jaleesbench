import type { ContractIndex } from "../contract";
import { signed, sortedBands } from "../format";

/**
 * A small, collapsed-by-default "about" panel for the sidebar — the one
 * intentionally producer-specific surface (it explains *this* benchmark). Its
 * factual figures (counts, band ladder) are derived from the data; the construct
 * sentence is editorial. Native <details> = collapsed by default.
 */
export function IntroPanel({ index }: { index: ContractIndex }) {
  const bands = sortedBands(index);
  const low = bands[0];
  const high = bands[bands.length - 1];
  const axesFacts = index.conditionAxes
    .map((ax) => `${ax.values.length} ${ax.label.toLowerCase()}`)
    .join(" × ");
  const paper = index.paper;

  return (
    <details className="about">
      <summary>About / how to read this</summary>
      <div className="about-body">
        <p>
          Whether an AI is a <em>righteous companion</em> — judged by the residue its
          counsel leaves on the user (the perfume-seller vs the blacksmith), not its
          knowledge.
          {high && low ? (
            <>
              {" "}Band scale <strong>{signed(low.value)} {low.label}</strong> …{" "}
              <strong>{signed(high.value)} {high.label}</strong>.
            </>
          ) : null}
        </p>
        <p className="about-facts">
          {index.items.length} questions · {index.subjects.length} models · {axesFacts} ·{" "}
          {index.judges.length} judges.
        </p>
        {paper && (
          <p>
            Read the{" "}
            <a href={paper.url} target="_blank" rel="noopener noreferrer">
              {paper.label}
            </a>
            {paper.draft ? " (draft — under review)." : "."}
          </p>
        )}
      </div>
    </details>
  );
}
