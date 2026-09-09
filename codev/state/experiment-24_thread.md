# experiment-24 — Issue #24: JaleesBench-Mini (EXPERIMENT, soft)

## 2026-09-09 — Hypothesis phase

- Spec file named in the builder prompt did not exist; wrote it from issue #24
  (methodology is baked by Waleed) plus the pilot's METHODOLOGY.md in the main
  checkout's `tmp/subset-experiment/`.
- Preregistered before touching data: H1 = a constrained greedy subset of
  ≤ 70 probes passes the 0.05 full-suite criteria under leave-one-subject-out;
  H2 = random/stratified pass < 50 % of draws at that k.
- Interpretation choices recorded in the spec: pooled-mean-band estimands
  (paper_stats convention), class ratio = ±10 *percentage points*, E2 under
  LOO uses the cross-validated prediction vector, k* = smallest passing grid k.
- Data inventory: 12 subjects have unstated/full (10 main + fanar +
  fanar-sadiq; fanar-sadiq lacks stated/guided; fanar has ~12 missing cells).
  Arabic run has 9 subjects (8 shared with EN + claude-opus-4-8). Four
  follow-up variants (ansari-steadfast, 3 thinking) have full 140 data and are
  never used in selection — added as a free extra held-out check (V3b).
- Skeleton EXPERIMENT protocol.json has empty `checks`, so no npm hardwiring to
  override here (unlike AIR/BUGFIX).
- V4 (prospective) costs money: will stop and ask the architect for the subject
  before any collection.

## 2026-09-09 — Design phase

- Plan written. One pure-numpy module `jaleesbench/mini.py`; per-probe
  (sum, count) table so estimands are masked ratios and greedy is vectorized.
- Adding `scipy` to the dev group for the MILP optimality check (HiGHS); it is
  a stretch item and time-boxed.
- Arabic target is Spearman ρ (paper reports 0.83 over 8 subjects).


## 2026-09-09 — Execute phase

- Module + 20 tests written and committed (c70686a). Full-bench references
  reproduce paper_stats.json to 3 decimals.
- Caught during test writing: largest-remainder stratified rounding with
  alphabetical tie-break favored whole classes when many strata tied; now
  seeded-random tie-break.
- **Preregistered grid result (before any exploratory work):** greedy LOO
  first passes at k = 110 (worst 0.041), k = 120 (0.022). Every k ≤ 100
  fails; the LOO worst error is non-monotone (0.094 at 40, 0.106 at 60,
  0.114 at 65). In-sample fit is 0.03 from k = 55 on — a large
  in-sample/held-out gap, i.e. greedy fits the training subjects' noise.
  At k ≥ 80 the only failing held-out subject is Ansari (the +0.48 outlier).
  Random subsets: pass rate 0.52 at k = 100, 0.72 at 110, 0.93 at 120.
  **H1 falsified (k* = 110 > 70). H2 falsified (random passes 72 % at k*).**
- Runner extended so a negative result still produces the whole ladder,
  flagged criteria_met (true here, at k = 110).

## 2026-09-09 — Analyze phase

- Frozen mini at k = 110 (f7989c5). Ladder: LOO 0.041 pass; per-judge Opus
  pass / Gemini 0.052 fail (glm-5.1 E1); Arabic 0.034 pass, ρ = 0.833
  preserved; variants 0.024 pass; per-pressure 3/72 cells > 0.05; CI
  inflation 1.04–1.09 vs √(140/110) = 1.13; annealing/MILP show greedy's
  in-sample gap ≥ 0.011 with no held-out relevance.
- Exploratory: k* = 95 at 0.075, 40 at 0.10; headline-only 35 at 0.075.
  Sampling floor SE(k) ≈ 0.5·√(1/k − 1/140) explains the curve.
- Wrote notes Results, review, figure (`figures` command), paper draft.
- V4 is blocked on Waleed's subject choice (money) — asking the architect.

- Gate experiment-complete approved (Waleed via architect main). V4 subject
  designated: IFM K2-Horizon-375B-A23B; collection is a separate project,
  score against mini_v1 when judgments arrive. Exploratory subsection stays.
