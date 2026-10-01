# Review: JaleesWeights — commit the fine-tuning work as a runnable `jaleesweights/` folder

**Spec**: `codev/specs/36-jaleesweights-commit-the-fine-.md` · **Plan**: `codev/plans/36-jaleesweights-commit-the-fine-.md` · **PR**: #37 · **Thread**: `codev/state/spir-36_thread.md`

## Summary

A new top-level `jaleesweights/` project holding the two-stage recipe behind the
JaleesWeights paper in three runnable paths — Gemma-4-31B on Modal and Inkling-Small on
Tinker exactly as run, plus a local demonstration on a smaller Gemma-family model — with an
archive of the dropped approaches, the 4-bit chain and the dose sweep as they ran, a
checksummed two-archive data release staged for the owner's approval, and a README a new
team can follow. Eight plan phases, one PR; no paid step was re-run, and nothing was
published.

## Spec Compliance

- [x] `jaleesweights/` at the top level with README, final pipeline, archive (Phases 1, 8)
- [x] Every scratch script and data file in the place its class says; nothing left-out in git or an archive — 204 files listed in the owner report: 56 final, 67 archive, 81 left out (Phases 1, 3; report in Phase 8)
- [x] Fresh clone, no original-machine files, README only: one-command install (Phase 2; walk-through Phase 8)
- [x] Download step installs reference data and main run where expected, verifies checksums, clear message on mismatch or unpublished release (Phase 3)
- [x] Every free step runs; eight rebuilt files byte-identical to the reference copies (Phase 4; re-done in the fresh clone, Phase 8)
- [x] Scoring reproduces the paper's main table — scores, drops, single-score intervals exact; paired intervals within 0.01; repeatable (Phase 4)
- [x] Paid steps through Modal, Tinker or a judge API start, find their inputs, report nothing to do against the reference data or stop before launch naming what they rent; a missing key or account is named (Phases 5, 6)
- [x] The local demonstration runs the recipe end to end on one GPU machine with no Modal; model, precision and batch as settings, default the owner's Gemma-4-12B (Phase 7)
- [x] The demonstration's GPU code is the Modal function bodies taken out of their wrapper; the diff is listed in the PR; it compiles and prints usage without a GPU; README names the first smoke test (Phase 7, PR body)
- [x] README says the demonstration's numbers are not the paper's (Phase 8)
- [x] A JaleesWeights step asks only for the keys it uses; Opus-only judging needs no Gemini credential (Phases 2, 5)
- [x] No step reads outside the clone or depends on the working directory; locations settled by the clone or an explicit input, never by where a package is installed (Phase 2)
- [x] No original-account checkpoint, volume or secret required; later steps take earlier outputs as inputs (Phases 5, 6)
- [x] Reference data never written; every step writes to a run directory and reads earlier outputs from there (Phases 2, 4 — central guard)
- [x] README: accounts and keys, Modal volume and secret, run orders for both models, rough costs and billed account per step, free steps, weights not included, capability panel mode (Phase 8)
- [x] README hardware section for the demonstration, measured vs derived, not executed before handoff (Phase 8)
- [x] Archive index: every archived script and data file, approach, paper claim; not maintained (Phase 8)
- [x] Dependencies declared with a committed lock; GPU stack as a separate group; Modal images pin the same versions (Phase 2)
- [x] Search of every changed file, every branch commit and both archives: no key, no `.env` content, no private names, no left-out file — 0 hits (Phase 8)
- [x] Owner-facing report outside git listing all 204 files with class and destination plus the search result (Phase 8)
- [x] Nothing publicly downloadable without the owner's approval; no release, draft or public, created (all phases)
- [x] No paid step run without approval (all phases)
- [x] Benchmark tests still pass (110); new offline tests (83) need no keys or data (all phases)
- [x] `codev/state/*` out of git except this builder's thread; spec, plan and review committed (all phases)

## Deviations from Plan

- **Phase 2**: a CUDA torch index scoped to the `gpu` group was tried and dropped — it
  leaked into the default graph on Linux and the PyPI wheel is a CUDA build anyway; `torch`
  and `transformers` are in the default install through the Tinker cookbook, as in the
  benchmark, and the README says so. `paths.py` gained a clone guard (import fails outside
  the clone).
- **Phase 3**: the main-run archive also carries the benchmark's `judgments_v2.jsonl`
  overlay (found when the benchmark's own paper-stats test failed on an installed main
  run); the NOTICE went into the archives in this phase rather than phase 8, so the
  archives were built once; run records follow the owner's plan-gate change (settings
  with path fields rewritten, metrics kept, checkpoint index dropped).
- **Phase 4**: a central `paths.output_path` guard protects the reference data after a
  reviewer showed `comparisons` could write beside a reference source; a CLI regression test
  against the paper's table was added; `sft_small` filters subject, framing and the
  training half.
- **Phase 6**: `modal run` needs a token before it calls a local entrypoint, so each driver
  also runs as a plain Python module for the free preflight; a real launch requires a
  checked local source for every uploaded input; the sampling driver's defaults are the
  recipe of record, not the archived base-model arm.
- **Phase 7**: `gemma_collect` records sampled chains with a `chain` field under one subject
  (the Inkling-Small convention); `--resume-from` must be a complete checkpoint;
  `score` gained `--extra-*` options so the demonstration's arms can be scored.
- **Integration review (post phase 8)**: the Modal trainers also refuse an incomplete
  `--resume-from` inside the container; `env.load_keys` delegates to the benchmark's
  `load_env` so there is one `.env` parser (values literal, no quote stripping).

## Consultation Feedback

Spec (1 round), plan (1 round), eight implement phases (phase 4 and phase 6 took three
rounds, phases 2, 7 and 8 two, the rest one). Every concern was accepted unless marked
otherwise. Late in the session several background lanes were killed before writing their
file (exit 144); each was re-run, in the foreground where needed, and completed.

### Specify (Round 1)

#### Gemini — APPROVE, no issues.
#### Codex — REQUEST_CHANGES
- Committing as-run originals first would publish private wording in history → **Addressed**: reword before the first commit; search covers every branch commit.
- Test 11 contradicted open question 3 → **Addressed**: scoped to what this work introduces.
- "Six rebuilt files" undercounted → **Addressed**: eight named files.
- Licensing out of scope → **Addressed**: promoted to an owner question (later decided: Apache-2.0 / CC BY 4.0 + NOTICE).
- Reference data immutability and new-run workspace → **Addressed**: defined; later a central guard.
#### Claude — COMMENT
- Repeatable bootstrap cannot reproduce two printed intervals → **Addressed**: authorised deviation; owner question 8.
- Benchmark resolves paths from its installed position → **Addressed**: explicit requirement; editable install.
- Completeness manifest vs privacy rule → **Addressed**: owner report outside git.
- Licence/terms; Modal bootstrap unproven; wording; headings → **Addressed** (a Security and privacy section; other headings kept per the phase prompt).

### Plan (Round 1)

#### Gemini — APPROVE, no issues.
#### Codex — REQUEST_CHANGES
- Phase 7 option gaps; chaining untested; no preflight for paid training; torch missing from the GPU group; wrong counts; spot-checked archives → **Addressed** (all six).
#### Claude — REQUEST_CHANGES
- Inkling-Small scoring is new code; no preflight; `58 − 1` wrong; `config.json` home paths; three Modal images; 1 MB vs `uv.lock`; `uv lock` on macOS; minors → **Addressed** (all).

### Phase 1 (Round 1)

Gemini, Codex, Claude — APPROVE. No concerns raised.

### Phase 2 (Rounds 1–2)

#### Gemini — APPROVE (both rounds).
#### Codex — REQUEST_CHANGES → APPROVE
- GPU stack not kept out of the default install → **Addressed in part**: honest accounting (torch/transformers come from the Tinker cookbook); custom CUDA index dropped.
- `judgment_key` and `main_run_files()` missing → **Addressed**.
#### Claude — APPROVE (both rounds)
- Clone guard; `.env` parser divergence; default assertion; CUDA promise → **Addressed** (guard added; parser later unified in the integration review).

### Phase 3 (Round 1)

#### Gemini, Codex — APPROVE.
#### Claude — APPROVE
- `--only` unvalidated; second-archive failure after first extraction; thread's absolute paths; tracked state file → **Addressed** (validation; verify-all-before-extract; paths replaced by placeholders); the tracked state file was checked by the architect: clean at HEAD.

### Phase 4 (Rounds 1–3)

#### Codex — COMMENT → REQUEST_CHANGES → APPROVE
- `inputs` self-check exited 0 on mismatch; chain test lacked a consumer; `sft_small` filters → **Addressed**.
- Reference data writable by a builder → **Addressed**: central guard.
- Blank cells where the paper prints `---`; no output regression test → **Rebutted in part**: cells are computed and printed with a note (the paper's blanks are "not reported", not "not computed"); the regression test was **Addressed**.
#### Gemini — REQUEST_CHANGES (mid-edit snapshot of the filtering fix) → APPROVE → APPROVE.
#### Claude — REQUEST_CHANGES → APPROVE → APPROVE
- Same as Codex round 1 plus dead variable and de-dup docstring → **Addressed**; training-half guard, fixture tests → **Addressed**.

### Phase 5 (Round 1)

#### Gemini, Codex — APPROVE.
#### Claude — APPROVE
- Pin `judge_all` wiring; trailing blank lines → **Addressed**; dry-run mkdir and traceback-vs-clean-error → **N/A** (cosmetic; left).

### Phase 6 (Rounds 1–3)

#### Codex — REQUEST_CHANGES → REQUEST_CHANGES → APPROVE
- Local-source validation; sampling defaults; eval docstring → **Addressed**.
- Enforce 316 / 502 rows → **Rebutted in part**: the 420-cell inputs are enforced and empty files refused; 316 / 502 are judge-dependent outputs, not design constants. Required local source for real launches; coverage → **Addressed**.
#### Gemini — REQUEST_CHANGES (mid-edit snapshot) → REQUEST_CHANGES (mid-edit snapshot) → APPROVE. Both snapshots named a parameter that existed at HEAD; from then on the tree was not edited during a round.
#### Claude — APPROVE → APPROVE → COMMENT
- Capability docstring contradiction; documented invocations missing `--local-*` → **Addressed**.

### Phase 7 (Rounds 1–2)

#### Gemini — APPROVE (both; the first attempt was killed and re-run).
#### Codex — REQUEST_CHANGES → APPROVE
- Incomplete `--resume-from` trained fresh; output path prepared too late → **Addressed**.
#### Claude — COMMENT → COMMENT
- No scoring for demo arms; colliding default names; dtype naming; guided sampling discarded → **Addressed**; `--k > 1` without a temperature; inputs schema checked late → **Addressed**.

### Phase 8 (Rounds 1–2)

#### Gemini — APPROVE (both).
#### Codex — REQUEST_CHANGES → COMMENT
- Review document missing; archive wildcards → **Addressed**; README option scopes and config path → **Addressed**.
#### Claude — REQUEST_CHANGES → APPROVE
- PR body lacked the demonstration diff summary → **Addressed**; minors (review doc, "Two notes", NOTICE quoted verbatim) → **Addressed**; `status.yaml` absolute paths → **N/A** (porch-managed); top-level README layout row and stale sentence → **Addressed**.

### Architect integration review on PR #37

- Modal trainers' silent fresh run on incomplete `--resume-from` → **Addressed** (guard inside the container, tested).
- Demonstration diff summary in the PR body → **Addressed**.
- Two `.env` parsers → **Addressed** (`load_keys` delegates to the benchmark's loader).
- `preflight_cli` fragility comment; clone-only comment → **Addressed**.

## Lessons Learned

### What Went Well

- Reading all 44 scripts and the paper before writing the spec made the classification
  exact (reviewers audited it against the scratch folder and found it complete), and the
  free checks done for the spec — byte-identical rebuilds, the paper's table recomputed —
  became the acceptance tests of the build.
- "As-run text first, port in later commits" gave every reviewer a small, honest diff for
  code that could not be re-run.
- The release was built, scanned and listed without ever being uploaded; the owner decides
  with the full contents list in hand.

### Challenges Encountered

- The scope changed three times at the spec gate within an hour (local Gemma instead of
  Modal; both; then "a demonstration, not a replica"). Each revision stayed small because
  the spec's structure separated the paths.
- Review lanes read the worktree live; editing during a round produced two false
  "TypeError" findings. Stopping edits during rounds fixed it.
- Background `consult` lanes were killed (exit 144) repeatedly late in the session;
  foreground runs completed. A tooling issue to raise.
- `modal run` cannot run a local entrypoint without a token, which made the planned
  `--dry-run` route unusable for a free check; the plain-module entry was the answer.

### What Would Be Done Differently

- Name the eight rebuilt files and the exact search scope (history, not tree) in the first
  draft of the spec; both were caught by review.
- Decide the `config.json` path-field question in the spec rather than in the plan.
- Check `uv`'s path-dependency and index semantics before writing the plan's packaging
  section.

### Methodology Improvements

- Porch's phase prompt tells the builder to run consultations in the background; when the
  harness kills background tasks, the builder has no signal except a missing file. A
  `consult` exit code that distinguishes "killed" from "reviewed" and a porch re-run step
  would help.
- A note in the implement prompt — "do not edit the tree while a review round runs" —
  would have saved two false findings.

## Architecture Updates

- Routed: hot (`arch-critical.md`) — the three independent `uv` projects and the editable
  dependency; where the main run and reference data live and that they are read-only; the
  single `.env` parser; the preflight / `--dry-run` / resume-safe convention. The hot file's
  map now lists `arch.md`'s four sections.
- Routed: cold (`arch.md`, previously a starter) — Repository shape; Where data lives;
  Paths and credentials; Paid steps.

## Lessons Learned Updates

- Routed: hot (`lessons-critical.md`) — private wording gone before the first commit and
  checked over `git log -p`; port research code as-run-first and prove the free steps
  byte-identical before touching paid steps; do not edit the tree during a review round.
- Routed: cold (`lessons-learned.md`, previously a starter) — Publishing from a public
  repository; Porting as-run research code; Tooling (uv path dependencies and torch index,
  `modal run` tokens, review lanes reading live, killed background consults).

## Flaky Tests

No flaky tests encountered. The benchmark's real-data test
(`test_full_bench_references_match_paper_stats`) was previously skipped in builder
worktrees for lack of data and now runs against the installed main run.

## Follow-up Items

- Owner: approve the release contents (report at `/private/tmp/agent-mail/spir-36-release-report.md`), then a draft release `jaleesweights-data-v1`, then publication; the verify phase re-runs `fetch_data` without `--from-dir` after that.
- Owner: the hadith-translation copyright of the benchmark's proof texts (open); open questions 1–9 stand at their defaults.
- A CI workflow running both `pytest` suites (the architect is opening an issue).
- A team with a GPU: run the demonstration's smoke tests and report; the first real
  stage-1 run on Modal with `--limit 4`.
- The two pre-existing comment lines in `jaleesbench/jaleesbench/collect.py` that name the
  upstream team (owner question 3).
