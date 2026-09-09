# Spec 24: JaleesBench-Mini — disciplined probe-subset reduction

**Protocol**: EXPERIMENT (soft) · **Issue**: #24 · **Date**: 2026-09-09
**Experiment record**: `codev/experiments/24-jaleesbench-mini/notes.md`

## What and why

JaleesBench scores a subject on 140 probes × 6 pressures × 3 framings × 2 scopes
× 2 judges. A full run costs on the order of $150 per subject plus judging. The
question is whether a small, fixed subset of probes ("JaleesBench-Mini")
reproduces the *full suite* of reported numbers for a subject it has never
seen, within a tolerance fixed before the subset is chosen. The output is a
frozen, versioned mini probe list, the selection/validation code, and a
standalone short paper on the item-reduction method.

The methodology in issue #24 is agreed with Waleed and is fixed. This spec
turns it into a falsifiable hypothesis with the operational definitions
needed to score it, and records the interpretation choices the issue leaves
open. Nothing below relaxes the issue.

## Hypothesis (preregistered)

**H1 (primary).** There exists a subset of at most **70 probes** (half the
bank, ≥ 50 % collection saving), selected by constrained greedy forward
selection on 11 subjects, that meets *all* acceptance criteria below for the
held-out 12th subject in every leave-one-subject-out fold.

**H2 (secondary).** At the smallest k where the optimized method passes, the
random baseline passes in fewer than 50 % of its 1000 draws, and the
stratified baseline passes in fewer than 50 % of its draws — i.e. optimization,
not just size, is what makes the mini work.

**Falsified if:** no k ≤ 70 on the grid passes leave-one-subject-out (H1), or
random/stratified draws pass as often as the optimized subset at that k (H2).
A negative result is still written up with the smallest passing k, whatever it
is. If no k < 140 passes, the finding is "the 0.05 full-suite criterion cannot
be met by a subset on this bank" and the paper reports that.

## Estimands (all on the reported −1..+1 scale)

For subject s and probe set P, a slice score is the **pooled mean band** over
every judgment whose probe is in P and whose (framing, scope) matches, times
`SCORE_SCALE = 0.5`. This is the convention of `paper_stats.py`; with the
bank's equal counts per probe it equals the mean of per-probe means, and it
tolerates Fanar's few missing cells without special-casing.

| Id | Estimand | Definition |
|----|----------|------------|
| E1 | Headline Jalees Score | unstated / full |
| E2 | Ranking and sign | sign of E1; pairwise order of E1 across subjects |
| E3 | Steadfastness | (unstated / full) − (unstated / turn1) |
| E4 | Framing staircase | stated / full **and** guided / full, two numbers |

A mini estimate is the same quantity computed on P = mini; the reference is
P = all 140. An estimand that is undefined for a subject (fanar-sadiq has no
stated or guided judgments) is skipped for that subject, not scored as zero.

Per-pressure steadfastness (6 cells per subject) is computed and reported for
the chosen mini but is **not** a gate.

## Acceptance criteria (preregistered, before any selection is run)

1. **|mini − full| ≤ 0.05** for E1, E3, and both E4 numbers, for every
   subject and every fold. One universal threshold.
2. **E2**: zero sign flips; Kendall τ = 1 (no discordant pair) restricted to
   subject pairs whose full-bench E1 differ by more than 0.10.
3. The same thresholds apply in every validation mode: leave-one-subject-out,
   per-judge, and the prospective test.

A subset **passes at k** when criteria 1–2 hold for every held-out subject in
leave-one-subject-out CV. Under LOO, E2 is evaluated on the vector of
cross-validated predictions (each subject's mini score taken from the fold
that held it out) against the full-bench vector. **k\*** is the smallest grid
k that passes; the frozen mini is the subset selected on all 12 subjects at
k\*, and its in-sample fit is reported but never headlined.

## Coverage constraints on any optimized subset

- ≥ 1 selected probe carrying each of the five pillars (restraint,
  cross_cutting, justice, patience, courage).
- Each islamic class's share of the mini within **±10 percentage points** of
  its bank share (clean 54/140 = 38.6 %, leaky 44/140 = 31.4 %, intrinsic
  42/140 = 30.0 %). *Interpretation choice:* the issue says "±10 %"; absolute
  percentage points is the reading that stays feasible at small k, and it is
  the one preregistered here.

## Selection methods compared (frozen seed 20260909)

1. Random: 1000 draws per k.
2. Stratified: proportional over islamic class × pillar-set strata, 1000 draws
   per k.
3. Optimized: constrained greedy forward selection minimizing the max absolute
   deviation over all defined estimands (E1, E3, E4) × all training subjects.
   Candidates that would make the coverage constraints unsatisfiable at the
   target k are excluded at each step. Ties break on lowest probe index.
4. Stretch: simulated annealing (swap moves) from the greedy solution, and an
   exact MILP if it is cheap to set up, to bound greedy's optimality gap.

k grid: 20, 25, …, 100, then 110, 120.

## Validation ladder

- **V1** leave-one-subject-out CV on the 12 subjects with unstated/full data
  (10 main + fanar + fanar-sadiq). The headlined number.
- **V2** per-judge: criteria re-evaluated with Opus-only and Gemini-only
  judgments, on the frozen mini and per fold.
- **V3** Arabic replication: on the Arabic run, mini vs full for the subjects
  that have both languages; does the AR/EN correlation (paper: ρ = 0.83)
  survive, and do the Arabic mini errors sit under 0.05? The Arabic run is
  never used in selection, so this is an out-of-sample check in its own right.
- **V3b (added, free)** the four follow-up-track variants that exist with full
  140-probe data (ansari-steadfast, claude-sonnet-thinking, gemma-4-thinking,
  glm-thinking) are never used in selection; the frozen mini is scored on them
  as extra never-seen subjects. Reported, clearly labeled as variants.
- **V4** prospective: a subject Waleed names, run on both mini and full 140.
  Spends money — **stop and ask the architect before any collection**.

## Uncertainty

Mini scores carry a bootstrap-over-probes 95 % CI (resampling the k probes,
5000 draws, paired for E3). Report the CI half-width inflation vs full and
compare to √(140/k).

## Scope

In: selection + validation code as a tested module in `jaleesbench/`, the
frozen probe-ID list as a bundled data file versioned against probe-bank v4,
a checked-in results JSON, the experiment notes, and a standalone paper draft
under `docs/paper/`.

Out: any change to the bank, judges, or scoring conventions; replacing the
full bench in any claim; automated V4 collection (human-gated).
