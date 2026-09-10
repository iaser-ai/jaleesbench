# Review 24: JaleesBench-Mini — disciplined probe-subset reduction

**Protocol**: EXPERIMENT (soft) · **Issue**: #24 · **Outcome**: both preregistered hypotheses falsified; frozen mini at k = 110 meets the criteria, including the prospective test
**Record**: `codev/experiments/24-jaleesbench-mini/notes.md`

## What was built

- `jaleesbench/jaleesbench/mini.py`: aggregate table, estimands (E1/E3/E4,
  E2 criteria), coverage constraints, greedy / random / stratified /
  annealing / MILP selection, leave-one-subject-out, per-judge, Arabic,
  variant, per-pressure and bootstrap validation; `run`, `explore`, `figures`,
  `score` commands. 20 tests in `tests/test_mini.py` (94 total pass), including
  a real-data check that the full-bench references reproduce
  `paper_stats.json` to three decimals.
- Frozen list `jaleesbench/jaleesbench/data/mini_v1.json` (k = 110, bank v4,
  seed 20260909), results `results/mini_stats.json` and
  `results/mini_explore.json` (whitelisted in `.gitignore`), figure
  `docs/paper/figures/fig_mini_k.pdf`, paper draft
  `docs/paper/jaleesbench-mini-paper.tex`.

## What was learned

1. **Preregistration changed the answer.** The pilot's greedy k = 30 mini was
   real in-sample and vanished under the full-suite criteria with LOO. Any
   result scored after the fact would have picked the k = 55 in-sample fit.
2. **Compute the sampling floor before optimizing.** Per-probe SD ≈ 0.5 fixes
   the standard error of any k-subset at ≈ 0.5·√(1/k − 1/140). Requiring the
   worst of ~44 held-out cells under 0.05 needs an SE near 0.02, i.e. k ≈ 110,
   regardless of selection method. This one line of arithmetic predicts the
   whole experiment and should be step zero of any item-reduction study.
3. **In-sample optimality is a trap.** Greedy 0.018 → annealing 0.012 → MILP
   0.007 on the training objective, with no held-out benefit; the held-out
   curve is non-monotone in k. Report LOO, never in-sample.
4. **Free out-of-sample data was lying around.** The Arabic run and four
   follow-up variants were never used in selection and confirmed the mini at
   0.034 / 0.024 worst error. Look for held-out data you already have.
5. **Per-judge is the weak rung.** Gemini-only fails LOO by 0.002 at k = 110.
   Quote the mini as a pooled-judge number, or expect k ≈ 120 for per-judge.
6. **Tie-breaks are decisions.** Largest-remainder allocation with an
   alphabetical tie-break favored whole classes when many one-probe strata
   tied; a seeded random tie-break fixed it. Found only because a test
   computed the expected class counts.

## Deviations from the plan

- The runner was extended (before the full run) to produce the whole ladder
  even when no grid k passes, flagged `criteria_met`. Not needed in the end
  (k = 110 passes) but kept.
- Exploratory sensitivity (`explore`) and the figure command were added after
  the preregistered run; both are labeled exploratory in the notes and paper.
- V4 (prospective) not run: it spends money and the subject is Waleed's
  choice. The `score` command is the path once judgments exist.

## Flaky Tests

None observed. Full suite: 94 passed.

## Follow-up: V4 pending data

Gate approved by Waleed 2026-09-09 with two decisions: the V4 subject is
**IFM K2-Horizon-375B-A23B** (released 2026-09-03, never seen by selection),
to be collected on the full 140 as a separate main-bench project once
Cerebras API access lands; and the paper keeps its exploratory
looser-tolerance subsection, labeled as such. When the judgments exist, run
`python -m jaleesbench.mini score --results <path> --subject <name>`, record
the result in the notes, and fill the paper's prospective-test subsection.
**Update 2026-09-10: V4 run and passed.** K2-Horizon collected on the full
140 (air-25), scored with `mini score`: worst error 0.019 (E4 stated), all
estimands inside 0.05. Artifact `jaleesbench/results/mini_v4_k2-horizon.json`
(whitelisted). The paper's prospective-test subsection now reports it, with
the empty-`reasoning` wire disclosure from collect.py.
