# Review: JaleesWeights — commit the fine-tuning work as a runnable `jaleesweights/` folder

**Spec**: `codev/specs/36-jaleesweights-commit-the-fine-.md` · **Plan**: `codev/plans/36-jaleesweights-commit-the-fine-.md` · **PR**: #37 · **Thread**: `codev/state/spir-36_thread.md`

Started at the end of the implement phase; completed in the review phase.

## What was built

A new top-level `jaleesweights/` project holding the two-stage recipe behind the
JaleesWeights paper in three runnable paths — Gemma-4-31B on Modal (as run), Inkling-Small
on Tinker (as run), and a local demonstration on a smaller Gemma-family model — plus an
archive of the dropped approaches, the 4-bit chain and the dose sweep as they ran. The data
goes out as two checksummed archives on a GitHub release, staged locally and gated on the
owner. Every step is a Typer command that loads only the keys it uses, writes to a run
directory, prints a preflight and stops on `--dry-run`.

## What was verified, and how

- The six deterministic builders reproduce the eight frozen training files byte for byte
  from the released data; `score` reproduces the paper's main table and is repeatable.
- A fresh clone in an empty directory with no keys installs, fetches the data from the
  staged archives, runs every free step, and passes both test suites (82 + 110).
- Every paid step, pointed at the complete reference data, finds nothing to do and builds no
  client; the Modal drivers and the demonstration print their preflights without an account
  or a GPU.
- The branch history, the changed files and both archives were searched for private names
  and key patterns: none.

## What was not verified

No paid step was re-run. The local demonstration has never executed on a GPU; the README
names its first smoke test. Whether the judge and base models are still served under the
same ids was not tested.

## Deviations from the spec and plan

- The main-run archive carries the benchmark's `judgments_v2.jsonl` overlay (found during
  phase 3; the benchmark's own tests need it). JaleesWeights reads the base file, as the
  runs did.
- Run records keep `config.json` (path fields rewritten) and `metrics.jsonl`; the checkpoint
  index was dropped (owner's change at the plan gate).
- The paired-interval bootstrap was made repeatable (the one authorised change to the
  as-run arithmetic); the two paired intervals the paper prints differ from the repeatable
  values by up to 0.005.
- `gemma_collect` records sampled chains with a `chain` field under one subject, the
  Inkling-Small convention, rather than the Modal sampler's lane subjects; both are handled.
- Review-driven guards beyond the plan: no builder can write into the reference data; a real
  Modal launch requires a checked local source for every uploaded input; an incomplete
  `--resume-from` is refused in all four trainers rather than silently training fresh.

## Open items for the owner

Spec open questions 1–9 at their defaults; the hadith-translation copyright of the proof
texts; publication of the data release (nothing published; the report is at
`/private/tmp/agent-mail/spir-36-release-report.md`).

## Flaky Tests

None encountered. The benchmark's real-data test (`test_full_bench_references_match_paper_stats`)
was previously skipped in builder worktrees for lack of data and now runs against the
installed main run.

## Architecture Updates

To be written in the review phase: `codev/resources/arch.md` gains the third `uv` project,
where the reference data and the main run live, the run-directory convention, and the
clone-only nature of the `jaleesweights` package.

## Lessons Learned Updates

To be written in the review phase. Candidates: reword before the first commit and search
the branch's history, not just the tree; the benchmark locates its data and credentials
from its installed position, so dependants must install it editable; `modal run` needs a
token before it calls a local entrypoint, so free preflights need a plain-Python entry;
background `consult` lanes were killed (exit 144) repeatedly late in the session while
foreground runs completed — run them in the foreground when that happens; do not edit the
tree while a review round is running.
