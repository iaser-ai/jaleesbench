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
