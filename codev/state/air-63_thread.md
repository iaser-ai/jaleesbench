# air-63 — JaleesWeights paper: restructure around prompt fading, Gemma only, guide not included

## 2026-11-11 — implement

Scope (issue #63): reorder the paper to the owner's narrative (a guide steers; a prompt given
once fades, chart early; the fix is two stages of fine-tuning, both needed; the trained model
holds, chart), drop the second model, and report the trained model with no guide. No new
experiment, nothing spent.

What I checked before editing:

- Every long-conversation number in the paper against
  `jaleesweights/experiments/58_prompt_fading/summary_fading.json` and `notes.md`. They match.
- The results-table numbers are pinned in `jaleesweights/tests/test_score.py` and come from the
  data release; none changed.
- The "preference optimization alone" sentence mixed the three Gemma attempts with two on the
  other model family. Recomputed the Gemma three from the released judgments with the released
  scoring code (free, read from the main checkout's installed data): −0.349, −0.340, −0.311
  against −0.335; paired differences −0.014, −0.006, +0.024, every interval spanning zero; they
  trained on 249, 179 and 516 pairs. The old text's "179 to 1,200 pairs" and "−0.025 to +0.023"
  included the other family, so the paper now says 179 to 516 and −0.014 to +0.024. "Training
  accuracies up to 1.0" is dropped; I could not tie it cleanly to the Gemma arms.
- The reference row "Inkling, best open base model bare" (+0.398). The benchmark pool in this
  repository has grown since the cited benchmark paper. On the same held-out half, Opus-judged,
  the newest pool member (Inkling 2 Small) scores +0.588 after pushback, above both Inkling
  (+0.398) and the trained Gemma (+0.499). So "past the best open base model" is true of the
  cited paper's pool and not of the repository's current one. I removed the row and the two
  sentences that leaned on it; this is a call for the owner and is raised in the PR.

Decisions I made that the owner should see (all listed in the PR):

- Kept: base model with the guide (the fading chart, and the benchmark's guided score +0.569 in
  the table, now labelled as the guide repeated with every user turn, with a sentence on why it
  differs from the chart's +0.43 starting point).
- Cut, as the architect confirmed mid-task: the trained model plus guide (+0.802 row, "The guide
  still helps" subsection, the "+0.3 on top of the tuned weights" limitation).
- Kept, shortened to nothing new: the paragraph on the stage-2 model given a one-sentence
  statement of the user's faith. It is not the guide, it was the experiment's originally
  registered tuned arm, and leaving it out would hide a registered arm that declined.
- The second model family appears once, in Availability, as runs in the repository that the
  paper does not report. No numbers.
- Availability now says the data release predates the long-conversation experiment and does not
  hold its conversations or judgments; the summary and per-scenario scores are in the repository.

Tests: none added. This is a document change; the existing suite is run as the check.

## 2026-11-11 — built, checked, committed

New section order: Introduction (with the prompted model's fading chart as Figure 1, top of
page 2) → The problem: a prompt fades (measurement; the long-conversation design; the guide
wears off) → The fix: fine-tuning in two stages (stage 1, stage 2, model) → Results (the trained
model holds over a long conversation, with the comparison chart; at the start of a
conversation, with the table; neither stage is enough alone; nothing else got worse) →
Limitations → Availability → Conclusion → the guide.

Two wording corrections made while rewriting sentences I had to touch anyway, both in the
cautious direction and both checked against the benchmark paper's own table: Gemma is "near
the bottom" of the pool (9th of 12 there, not last), and the open-weight models "mostly sit in
the bottom half" (five of six; the sixth is 4th).

Build: `latexmk -xelatex`, no LaTeX errors, no undefined references, no overfull boxes, no
bibtex warnings. 13 pages (was 12): the cuts shortened the text, but the tables and figures are
pinned in place and the long example table in Limitations now starts a page.

Also changed, one sentence each, because they said what the paper is: the root `README.md`
("two open models" → Gemma-4-31B) and `jaleesweights/README.md` (the Tinker path is "a second
model … the paper does not report it"). Not touched: the finer cross-references to paper claims
in `jaleesweights/README.md`, `archive/README.md` and `TUTORIAL.md`, and the scoring command,
which still prints the second model's rows. Listed in the PR.

Checks: `uv run --directory jaleesbench pytest -q` 119 passed, 1 skipped;
`uv run --directory jaleesweights pytest -q` 114 passed, 1 skipped.

## 2026-11-11 — PR #64 open, waiting at the pr gate

PR #64 opened with the full list of cuts and six decisions for the owner in its body. The
optional three-way review was skipped: a document change, with each number checked against
the committed summary. Waiting for a human decision on the pr gate.

## 2026-11-11 — architect's integration review: five fixes

Review feedback on PR #64, not a gate approval. All five done, nothing paid:

1. "the two tuned models" → "the two tuned checkpoints" (first Results subsection and the
   Figure 2 caption).
2. Results intro now says the one exception to "no system message" is a single paragraph,
   and that paragraph says it is the only place a tuned checkpoint has a system message. Still
   pending the owner's decision on whether the paragraph stays.
3. Availability opener now agrees with the later caveat: the data behind the training runs and
   the table are released; the long-conversation conversations and judgments are not.
4. `jaleesweights/archive/README.md`: the paper cross-references now match the paper (three
   preference-only arms on Gemma; the Inkling arms and the Inkling-Small sweep marked as not in
   the paper), and a new table records the three Gemma arms' pair counts (249, 179, 516),
   scores and paired differences with intervals, with the free command that reprints them. I
   ran that command against the installed data and the output matches the table.
5. `test_score.py`: the test is renamed `test_score_reproduces_the_released_results_table` and
   its docstring and comments say which rows the paper prints and which are only in the data
   release. No asserted number changed. `jaleesweights/README.md` now describes the scoring
   output and the test the same way.

Checks: paper rebuilt, no errors, undefined references, overfull boxes or bibtex warnings, 13
pages. `jaleesbench` 119 passed, 1 skipped; `jaleesweights` 114 passed, 1 skipped (the
table test, which needs the data). Run with the installed data from the main checkout
(read-only, through the `JW_REFERENCE` and `JW_BENCH_RESULTS` variables) the renamed test
passes.
