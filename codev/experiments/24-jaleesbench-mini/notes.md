# Experiment 24: JaleesBench-Mini — disciplined probe-subset reduction

**Status**: Complete (both preregistered hypotheses falsified; prospective test pending Waleed's subject choice) · **Date**: 2026-09-09 · **Issue**: #24

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

Both preregistered hypotheses are falsified. Under leave-one-subject-out CV
the constrained greedy subset first meets every 0.05 criterion at **k = 110**
(a 21 % saving), not at k ≤ 70; and at k = 110 random subsets pass 72 % of
the time (stratified 75 %), so optimization is not what makes the mini work.
The reason is a sampling floor: a subject's per-probe scores have SD ≈ 0.5 on
the −1..+1 scale, so a k-probe subset's headline standard error is ≈ 0.044 at
k = 70 and ≈ 0.023 at k = 110 for a typical subject, and keeping the worst of
~44 held-out cells under 0.05 needs an SE near 0.02. Greedy fits the training
subjects far better than that (in-sample worst 0.03 from k = 55) but the
structure it exploits does not transfer to a held-out subject: its held-out
error is non-monotone in k (0.094 at 40, 0.114 at 65) and at k ≥ 50 the
failing fold is almost always Ansari, the +0.48 outlier.

| Metric | Value | Notes |
|--------|-------|-------|
| k\* (greedy LOO, all criteria at 0.05) | 110 | H1 required ≤ 70 |
| Greedy held-out worst error at k = 40 / 70 / 100 / 110 / 120 | 0.094 / 0.093 / 0.062 / 0.041 / 0.022 | max over subjects × E1,E3,E4 |
| Greedy in-sample worst error at k = 40 / 70 / 110 | 0.046 / 0.031 / 0.018 | overfits |
| Random pass rate at k = 80 / 100 / 110 / 120 | 0.11 / 0.52 / 0.72 / 0.93 | 1000 draws; H2 required < 0.5 at k\* |
| Stratified pass rate at k = 100 / 110 / 120 | 0.46 / 0.75 / 0.95 | class × pillar-set strata |
| Frozen mini (k = 110) in-sample / LOO worst | 0.018 / 0.041 | LOO: glm-5.1 E1 0.041, Ansari E3 0.030 |
| E2 at k = 110 | 0 sign flips, τ = 1 on separated pairs | in-sample and LOO |
| Per-judge LOO worst: Opus / Gemini | 0.043 pass / 0.052 **fail** | Gemini-only glm-5.1 E1; both pass in-sample |
| Arabic (9 subjects, never in selection) worst | 0.034 pass | ρ(AR,EN) = 0.833 full and mini |
| Variants (4, never in selection) worst | 0.024 pass | ansari-steadfast, 3 thinking |
| Per-pressure steadfastness cells > 0.05 | 3 of 72 (max 0.062) | reported, not gated |
| Bootstrap CI half-width inflation | 1.04–1.09 | √(140/110) = 1.13 |
| Greedy in-sample optimality gap | ≥ 0.011 | annealing 0.012, MILP incumbent 0.007 (300 s limit) |
| Exploratory k\*: threshold 0.075 / 0.10 | 95 / 40 | full suite; headline-only 35 / 20 |

Output artifacts: `jaleesbench/results/mini_stats.json`,
`jaleesbench/results/mini_explore.json`, `jaleesbench/jaleesbench/data/mini_v1.json`,
`docs/paper/figures/fig_mini_k.pdf`, `docs/paper/jaleesbench-mini-paper.tex`.

## What Worked / What Didn't

Worked: preregistering the criteria before running anything — the pilot's
"greedy k = 30 reproduces the headline" evaporated the moment the full suite
and the 0.05 bar were fixed up front. Leave-one-subject-out as the headline
number: in-sample fit alone would have advertised a 55-probe mini with 0.03
error. The never-in-selection checks (Arabic, follow-up variants) cost nothing
and confirm the k = 110 mini out of sample. The analytic sampling floor
explains the whole k curve and could have been computed before any selection.

Didn't: optimized selection. Greedy, annealing and MILP all improve the
in-sample objective (0.018 → 0.012 → 0.007) while the held-out error is set by
sampling variance; a better optimizer would only overfit more. Stratified
draws are no better than random. Per-judge stability fails marginally for
Gemini alone (0.052) under LOO — the mini should be quoted as a pooled-judge
number. The largest-remainder stratified allocation with alphabetical
tie-breaking silently favored whole classes; fixed to a seeded random
tie-break before the full run.

## Next Steps

1. **V4 prospective test** — Waleed names the subject; run mini (110 probes)
   and full 140, compare at 0.05 via `python -m jaleesbench.mini score`.
   Costs money; not started.
2. Decide the mini's stated use. As preregistered it is a 21 % saving, so it
   is a screening tool only; a 0.075 tolerance would allow k = 95 (32 %) and a
   headline-only mini at 0.075 would allow k = 35 (75 %), but those are
   exploratory and not the criteria we fixed.
3. Paper draft at `docs/paper/jaleesbench-mini-paper.tex` for Waleed's edit;
   V4 section is a placeholder until the subject is chosen.
