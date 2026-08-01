# task-QKrM — Fanar-Sadiq as subject 12

## Scope
Land the pre-proven harness entry for `fanar-sadiq` (QCRI's Islamic-RAG variant
of Fanar) as subject 12 in `jaleesbench/jaleesbench/collect.py`. Pure data
addition — the diff was supplied verbatim and is already proven live (840/840
sittings collected clean: 4-sitting pilot + full run, zero failures).

## What landed
One SUBJECTS entry:
- key `fanar-sadiq`, provider `fanar` (landed on main via PR #15), model `Fanar-Sadiq`
- `max_tokens: 8192` — same 16,000-token TOTAL-context API as `fanar`, so the
  per-subject override must leave room for input
- `framings: ["unstated"]` — same ruling as Ansari: a purpose-built Islamic
  assistant, so Stated/Guided framings don't apply

No mechanism changes. PR #15's `max_tokens`-override test in `tests/test_seam.py`
already exercises that path.

## Test-count check
Task said to update test count expectations only if some test asserts the
SUBJECTS size. Checked: nothing asserts `len(collect.SUBJECTS)`.
`tests/test_units.py:105` asserts `len(paper_stats.SUBJECTS) == 10`, which is
the *paper* subject list in `paper_stats.py` — untouched by this change. No
test edits needed. Full suite: 74 passed.

## Noted, not changed
The pre-existing `fanar` comment says "Sadiq/C-2-27B variants exist but aren't
run" — now stale for Sadiq. Left alone: the instruction was to apply the diff
verbatim, and the diff does not touch that line. Flagged to the architect
rather than silently fixed.

## Constraints honored
Did not run collection. Did not touch `results/`.
