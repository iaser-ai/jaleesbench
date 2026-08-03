# bugfix-19 — jaleesbrowser leaderboard pools framings (Issue #19)

## Investigate (2026-08-02)

**Reproduced.** Re-computed the leaderboard columns from
`apps/jaleesbrowser/public/data/index.json` two ways:

- Pooled across all three framings (what `computeLeaderboard` does today):
  gpt-5.5 post +0.63, inkling +0.62; Δ gpt-5.5 −0.11, nemotron −0.14,
  gemini-3.5-flash −0.30 — exactly the mismatched values in the issue.
- Unstated-only: post +0.48 / +0.27 / +0.26 / +0.25 …; Δ gpt-5.5 −0.08,
  nemotron −0.07, gemini −0.26 — matching the paper's Steadfastness column.

**Root cause**: `computeLeaderboard` (`apps/jaleesbrowser/src/leaderboard.ts:66-94`)
pushes every condition combo into `postAll`/`initialAll`, i.e. it pools across
the breakdown axis (framing). The paper (`jaleesbench/jaleesbench/paper_stats.py:112-131`)
computes Jalees Score and Steadfastness from `(subject, "unstated", scope)` only.
The index's `subjects[].overall` blob is the same pooled quantity — the browser
faithfully reproduces a number the paper never reports.

**Fix plan** (contract-generic, per the issue): restrict `initial`/`post`/`delta`
to combos whose breakdown-axis value is the axis's **first declared value**
(already the canonical rank key). No axis → keep pooled (generic degradation).
Update the `Leaderboard.tsx` caption; update `leaderboard.ts` docstring (it
currently claims post reproduces `subjects[].overall` — no longer true).

**Open question resolved (builder judgment)**: keep the now-redundant Unstated
breakdown column. It preserves the three-step framing staircase reading, and the
visible post == Unstated equality is itself the reader's cross-check that the
headline score is the published Jalees Score. Smaller diff too (rank key stays
`byValue[0]`).

**Residual noted (out of scope)**: a few unstated means differ from the paper
table by ±0.01 (e.g. gpt-5.5 computed +0.2747 vs paper +0.28, sonnet-5 +0.2646
vs +0.27, gemma Δ −0.2851 vs −0.28). The blob stores per-cell judge means; the
paper pools per-judgment, so cells with unequal judge counts weight differently.
Not caused by, and not fixable by, this change — worth a separate issue if the
architect cares.

**Test impact**: `leaderboard.test.ts` expectations for A's post/Δ change
(post 0.5→0.0, Δ −0.3→−0.8); component test "re-sorts on a column click" uses
post-pooling to diverge from canonical order — will re-anchor it on a column
that still diverges (e.g. initial). Will add regression tests: unstated-only
restriction for post AND initial, plus pooled fallback when no breakdown axis.

Scope fits BUGFIX (< 50 LOC net in `apps/jaleesbrowser`). Vitest suite is the
check surface (porch fix checks are Python-only per the issue note).

## Fix (2026-08-02)

Implemented as planned: `computeLeaderboard` now gates `postAll`/`initialAll`
pushes on `headline = !axis || c[axis.key] === axis.values[0].id`; `byValue`
still buckets every combo, so the framing staircase columns are unchanged.
Kept the Unstated column (see judgment above). Caption now reads: "the initial,
post-pressure, and Δ columns cover the Unstated Framing only, and the Framing
columns give the post-pressure score under each Framing".

Tests: rebuilt both test tensors so the first framing value varies per pressure
and turn-1 differs by framing — pooling now shifts every headline column, so
the regression tests genuinely bite. **Verified the regression is real**:
temporarily reverting the one-line gate makes 2 tests fail
(`restricts initial/post/delta…`, `excludes absent cells…`); with the fix, all
82 tests and `npm run build` pass. Re-anchored the component sort tests on the
initial column (post-sorting no longer diverges from canonical order, by
design). Added a no-breakdown-axis index test covering the pooled fallback.

Net diff: 4 files, +111/−47.

## PR (2026-08-02)

PR #20 opened (Fixes #19). CMAP: gemini=APPROVE, codex=REQUEST_CHANGES,
claude=APPROVE. Codex's issue was real but not about the fix: the worktree was
spawned from local `main`, which was one commit (`d85f1ba`, paper PDF +
architect state) ahead of `origin/main`, so that commit rode into the PR.
Addressed by rebasing the branch onto `origin/main` (dropping `d85f1ba`) and
force-pushing with lease; re-ran the vitest suite (82 pass) and build after the
rebase. `d85f1ba` still needs a separate push to `origin/main` by the architect
— flagged in the PR comment. Codex judged the functional fix sound; no code
changes requested.

Requested the `pr` gate; waiting for human approval.
