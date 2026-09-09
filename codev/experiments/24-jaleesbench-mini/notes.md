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

*(filled in the Design phase)*

## Environment & Reproduction

*(filled in the Execute phase)*

## Code

*(filled in the Execute phase)*

## Results

*(filled in the Analyze phase)*

| Metric | Value | Notes |
|--------|-------|-------|
| | | |

## What Worked / What Didn't

*(filled in the Analyze phase)*

## Next Steps

*(filled in the Analyze phase)*
