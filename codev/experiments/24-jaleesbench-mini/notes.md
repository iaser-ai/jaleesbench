# Experiment 24: JaleesBench-Mini — disciplined probe-subset reduction

**Status**: In Progress · **Date**: 2026-09-09 · **Issue**: #24

## Goal

Can a fixed subset of the 140 JaleesBench probes reproduce the full suite of a
subject's reported numbers — headline score, ranking and sign, steadfastness,
and the stated/guided framing staircase — for a subject it has never seen,
with every error at or under 0.05?

Preregistered hypothesis and criteria are in
`codev/specs/24-jaleesbench-mini-disciplined-p.md` (written before any
selection code ran). In short:

- **H1**: a constrained-greedy subset of ≤ 70 probes passes all criteria in
  every leave-one-subject-out fold.
- **H2**: at that k, fewer than half of random and stratified draws pass.
- **Criteria**: |mini − full| ≤ 0.05 on E1, E3, E4 for every subject and fold;
  zero sign flips; τ = 1 on pairs the full bench separates by > 0.10.
- **Falsified if** no k ≤ 70 passes, or random/stratified pass as often.

## Approach

Constrained greedy forward selection on a per-probe aggregate table, scored
by the max absolute deviation over all defined estimands × training subjects,
with random and stratified draws as baselines and annealing/MILP as an
optimality check. Leave-one-subject-out CV is the headline validation; the
Arabic run and four follow-up variants are extra never-in-selection checks.
Full design in `codev/plans/24-jaleesbench-mini-disciplined-p.md`.

Alternatives considered: selecting on the headline alone (the pilot; rejected
because it distorted steadfastness by up to 0.13), and nested greedy (one
ranking of probes cut at each k; rejected because the coverage constraints
depend on k, so selection is run per k).

## Environment & Reproduction

Offline; reads the existing judgment files from the main checkout's
`jaleesbench/results/` (gitignored, read-only). No provider calls.

```
cd jaleesbench
uv sync                                   # numpy + scipy in the dev group
uv run python -m jaleesbench.mini run --results /abs/path/to/jaleesbench/results
uv run pytest -q                          # 94 tests; the real-data check needs JALEESBENCH_RESULTS=/abs/path
```

Seeds: selection/random/annealing 20260909, bootstrap 12345 (as paper_stats).
Probe bank v4 (`jaleesbench/data/probes.json`). Judgments: `judgments.jsonl`
with the `judgments_v2.jsonl` overlay via `score.load_judgments`, plus
`judgments_ar.jsonl`, `judgments_ansari_mod.jsonl`, `judgments_thinking.jsonl`
for the never-in-selection checks. Full run: ~4 min for the grid, then the
ladder at k* (annealing 20k iterations, MILP with a 300 s HiGHS limit).

## Code

- `jaleesbench/jaleesbench/mini.py` — table, estimands, criteria, coverage
  constraints, greedy/random/stratified/annealing/MILP selection, LOO,
  per-judge/Arabic/variant/per-pressure/bootstrap validation, `run` and
  `score` commands.
- `jaleesbench/tests/test_mini.py` — 20 tests on a synthetic bank plus a
  real-data check that the full-bench references reproduce `paper_stats.json`.
- `jaleesbench/results/mini_stats.json` — every number below (checked in).
- `jaleesbench/jaleesbench/data/mini_v1.json` — the frozen list.

## Results

*(filled in the Analyze phase)*

| Metric | Value | Notes |
|--------|-------|-------|
| | | |

## What Worked / What Didn't

*(filled in the Analyze phase)*

## Next Steps

*(filled in the Analyze phase)*
