import { useEffect, useState } from "react";
import type { ContractIndex } from "../contract";
import { signed, sortedBands } from "../format";
import { getStored, setStored } from "../storage";

const SEEN_KEY = "orient-seen";

/**
 * The orientation panel — the one intentionally producer-specific surface: it is
 * the "about this dataset" copy that explains *this* benchmark. (The §9.6 "no
 * JaleesBench-specific strings" rule is about the generic data-rendering
 * components, so the viewer renders any producer's data; this editorial panel is
 * the orientation, not a data renderer.) Its factual figures — counts, axis
 * labels, the band ladder — are nonetheless derived from the data.
 *
 * Open on a visitor's first load, collapsed thereafter (persisted); always toggleable.
 */
export function IntroPanel({ index }: { index: ContractIndex }) {
  const [open, setOpen] = useState(() => getStored(SEEN_KEY) !== "1");
  useEffect(() => {
    setStored(SEEN_KEY, "1"); // collapsed by default on the next visit
  }, []);

  const bands = sortedBands(index);
  const low = bands[0];
  const high = bands[bands.length - 1];
  const axesFacts = index.conditionAxes
    .map((ax) => `${ax.values.length} ${ax.label.toLowerCase()}`)
    .join(" × ");
  const paper = index.paper;

  return (
    <section className="intro">
      <button
        type="button"
        className="intro-toggle"
        aria-expanded={open}
        onClick={() => setOpen((o) => !o)}
      >
        About this dataset {open ? "▾" : "▸"}
      </button>
      {open && (
        <div className="intro-body">
          <p>
            This benchmark asks whether an AI is a <em>righteous companion</em>
            {" "}(al-jalīs al-ṣāliḥ) — judged not by its knowledge or professed values
            but by the <strong>residue its counsel leaves on the user</strong>: like
            sitting with a perfume-seller you walk away better, like sitting with a
            blacksmith you walk away singed. Each response is placed on a band scale
            {high && low ? (
              <>
                {" "}from <strong>{signed(low.value)} {low.label}</strong> to{" "}
                <strong>{signed(high.value)} {high.label}</strong>
              </>
            ) : null}
            .
          </p>
          <p>
            The data spans{" "}
            <strong>
              {index.items.length} questions · {index.subjects.length} models ·{" "}
              {axesFacts} · {index.judges.length} judges
            </strong>
            , scored over two turns (before and after the user pushes back).
          </p>
          <p>The controls:</p>
          <ul>
            <li>
              <strong>Question</strong> — the situation brought to the model.
            </li>
            <li>
              <strong>Model A / Model B</strong> — the two systems compared.
            </li>
            {index.conditionAxes.map((ax) => (
              <li key={ax.key}>
                <strong>{ax.label}</strong> — one of the conditions varied (
                {ax.values.length} options).
              </li>
            ))}
            {index.scopes && index.scopes.length > 1 && (
              <li>
                <strong>Scope</strong> —{" "}
                {index.scopes.map((s) => s.label).join(" vs ")}.
              </li>
            )}
          </ul>
          <p>
            <strong>Compare</strong> two models to find the questions where they differ
            most, then click a row to read the transcripts and judge verdicts.
          </p>
          {paper && (
            <p>
              Read the{" "}
              <a href={paper.url} target="_blank" rel="noopener noreferrer">
                {paper.label}
              </a>
              {paper.draft ? " (draft — under review, not yet published)." : "."}
            </p>
          )}
        </div>
      )}
    </section>
  );
}
