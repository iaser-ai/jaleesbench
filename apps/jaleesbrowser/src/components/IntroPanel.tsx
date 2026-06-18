import { useEffect, useState } from "react";
import type { Paper } from "../contract";
import { getStored, setStored } from "../storage";

const SEEN_KEY = "orient-seen";

/**
 * The orientation panel: what the benchmark measures and what each control does.
 * Open on a visitor's first load, collapsed thereafter (persisted via a
 * localStorage flag); the toggle is always available.
 */
export function IntroPanel({ paper }: { paper?: Paper }) {
  const [open, setOpen] = useState(() => getStored(SEEN_KEY) !== "1");
  useEffect(() => {
    setStored(SEEN_KEY, "1"); // collapsed by default on the next visit
  }, []);

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
            <strong>JaleesBench</strong> asks whether an AI is a <em>righteous
            companion</em> (al-jalīs al-ṣāliḥ) — judged not by its knowledge or
            professed values but by the <strong>residue its counsel leaves on the
            user</strong>: like sitting with a perfume-seller you walk away better,
            like sitting with a blacksmith you walk away singed. Each response is placed
            on a band scale from <strong>−1 Burns</strong> to <strong>+1 Perfume</strong>.
          </p>
          <p>
            The data spans <strong>140 questions × 8 models × 6 pressures × 3 framings</strong>,
            each scored by <strong>2 judges</strong> over two turns (before and after the
            user pushes back).
          </p>
          <p>The controls:</p>
          <ul>
            <li>
              <strong>Question</strong> — the dilemma a Muslim user brings.
            </li>
            <li>
              <strong>Model A / Model B</strong> — the two systems compared.
            </li>
            <li>
              <strong>Pressure</strong> — how the user pushes back.
            </li>
            <li>
              <strong>Framing</strong> — what the model is told about the user.
            </li>
            <li>
              <strong>Scope</strong> — the first response, or after pressure.
            </li>
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
