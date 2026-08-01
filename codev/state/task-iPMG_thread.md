# task-iPMG — Fanar (QCRI) as subject 11

## Task

Land a pre-proven harness change as a PR. The architect's working tree is already
mid-collection with this exact diff (smoke test + 4-sitting pilot clean, full
2,520-sitting run in flight), so the diff was handed over verbatim rather than
re-derived. My job was application + a focused unit test + PR — explicitly NOT
running collection and NOT touching `results/`.

## What landed

Four pieces, all from the supplied diff, applied byte-for-byte:

1. **`fanar` provider** (`providers.py`) — OpenAI-compatible client at
   `https://api.fanar.qa/v1`, `FANAR_API_KEY`, `timeout=300` (matching the
   `ansari` client's shape).
2. **`fanar` SUBJECTS entry** (`collect.py`) — model `"Fanar"` (the routed
   flagship; Sadiq/C-2-27B variants exist but aren't run), all three framings,
   `max_tokens: 8192`.
3. **Per-subject `max_tokens` override** — `spec.get("max_tokens", MAX_TOKENS)`
   in `call_subject`, threaded through all four provider branches (openai-compat,
   anthropic, gemini). This is the only change that touches other subjects, and
   it's a no-op for them: no other spec carries a `max_tokens` key, so they all
   resolve to the global `MAX_TOKENS = 16384` exactly as before.
4. **Dispatch lists** — `fanar` added to the openai-compatible branch and to both
   patient-retry lists (5 retries, 30s-linear backoff), alongside `ansari` and
   `tinker`.

### Why the override exists

Fanar's API has a **16,000-token TOTAL context — input and output share it**. The
global 16384 cap is both larger than the whole window and blind to input length,
so it 413s as a hard failure, not a truncation. 8192 leaves room for the framing
block + conversation. This is a different failure shape from the Nemotron/Inkling
reasoning-token problem (which wanted a *larger* cap), which is why a per-subject
override rather than a global retune is the right mechanism.

## Test

Added `test_call_subject_per_subject_max_tokens_override` to `tests/test_seam.py`,
next to the other `call_subject` routing tests — that file already owns "what
exactly gets sent to the provider", which is precisely what the override changes.

Both halves of the contract in one test: `fanar` sends its own 8192, and
`gemma-4-31b` (no override, and a Friendli subject so it uses the same
`max_tokens` request param rather than gpt-5.5's `max_completion_tokens`) still
sends `MAX_TOKENS`. Asserting against `collect.SUBJECTS[...]`/`collect.MAX_TOKENS`
rather than hardcoded 8192/16384 keeps the test honest if either value is retuned.

Full suite: **74 passed**. No live API call was made — `conftest.FakeOpenAI`
covers it, and no `FANAR_API_KEY` was needed in the worktree.

## Notes for the cohort

- `test_units.py::test_subjects_reproduce_paper_grid` asserts
  `len(paper_stats.SUBJECTS) == 10` and `paper_stats.SUBJECTS <= collect.SUBJECTS`.
  Adding an 11th collectable subject does **not** break it (the assertion is on
  `paper_stats`, not `collect`), and it shouldn't — `paper_stats` should only grow
  to 11 once Fanar's results are actually collected and judged. Whoever lands the
  Fanar results is the one who flips that number.
- Diff scope verified byte-identical to the handed-over diff before commit; the
  only file I authored is the test.
- `results/` untouched, no collection run.
