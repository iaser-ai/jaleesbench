# Plan 24: JaleesBench-Mini — design and implementation order

**Spec**: `codev/specs/24-jaleesbench-mini-disciplined-p.md` · **Protocol**: EXPERIMENT (soft)

## Approach

One analysis module, `jaleesbench/jaleesbench/mini.py`, that is pure numpy
over a per-probe aggregate table, plus a runner that writes every result to
one JSON. Nothing touches the provider seam; all data is read from an
existing results directory (the main checkout's, read-only, by absolute
path).

### Data model

`build_table(judgments, probe_ids)` folds judgment records into
`agg[(subject, framing, scope, judge|None, pressure|None)] -> (sum[140], count[140])`.
Every estimand is then a ratio of masked sums: `score(P) = sum[P].sum() /
count[P].sum() * 0.5`. This is exactly `paper_stats.py`'s convention, so
the full-bench references reproduce the published scorecard (checked in
tests against `results/paper_stats.json`, which is in git).

`estimands(agg, subject, P, judge=None)` returns `{E1, E3, E4_stated,
E4_guided}` with `None` where the slice has zero count. `deviation(agg,
subjects, P)` returns the max over subjects × defined estimands of
|mini − full| — the greedy objective.

### Selection

- **Greedy** (`greedy_select(agg, train, k, meta, rng)`): forward selection;
  at each step evaluate every unchosen probe that keeps the coverage
  constraints satisfiable at k (class-count lower/upper bounds from ±10 pp;
  uncovered pillars ≤ remaining slots), pick the min-deviation candidate,
  lowest index on ties. Vectorized: adding probe c changes each slice sum by
  `sum[c]` and count by `count[c]`, so all 140 candidates are scored in one
  array op per estimand.
- **Random / stratified**: 1000 draws per k with `np.random.default_rng(20260909)`;
  stratified uses proportional largest-remainder allocation over
  (islamic, sorted pillars) strata, exactly as the pilot did.
- **Annealing** (stretch): swap moves from the greedy solution, constraint-
  respecting, temperature schedule fixed, seed fixed; reports the best
  deviation found vs greedy's.
- **MILP** (stretch): minimize t subject to |Σ x_i a_ei − b_e| ≤ t per
  estimand e, Σ x = k, class bounds, pillar coverage, x binary, via
  `scipy.optimize.milp` (HiGHS). Uses per-probe mean-band coefficients, which
  makes the objective linear; identical to the pooled mean where counts are
  equal, and off by < 0.001 for Fanar's few missing cells. Requires adding
  `scipy` to the dev dependency group. Time-boxed: if HiGHS does not close a
  k within a few minutes, report the bound and gap instead of the optimum.

### Validation

- **LOO** (`loo(agg, subjects, k, method, ...)`): for each held-out subject,
  select on the other 11, score the held-out one; assemble the cross-validated
  prediction vector; evaluate criteria 1–2 (spec). Run for every grid k and
  every method (random/stratified: per-draw pass rate).
- **k\***: smallest grid k where greedy-LOO passes. Frozen mini = greedy on
  all 12 at k\* → `jaleesbench/data/mini_v1.json` with bank version, seed,
  k, probe ids, and the selection command.
- **Per-judge**: estimands with `judge` fixed; criteria on the frozen mini and
  in LOO.
- **Arabic**: table from `judgments_ar.jsonl`; mini vs full errors for its 9
  subjects; Spearman ρ AR-vs-EN on the 8 shared subjects, full and mini.
- **Variants**: table from `judgments_ansari_mod.jsonl` + `judgments_thinking.jsonl`;
  frozen mini scored on the 4 never-in-selection variants.
- **Per-pressure steadfastness** on the frozen mini, reported only.
- **Bootstrap** over probes (5000 draws, seed 12345 like paper_stats) for
  mini E1/E3/E4 per subject; CI half-width inflation vs full.
- **Prospective (V4)**: not automated. After V1–V3 results exist, message the
  architect with the results and ask for the subject. The same `mini score`
  path scores any new subject once its judgments exist.

### Outputs

- `jaleesbench/results/mini_stats.json` (whitelisted in `.gitignore` like
  paper_stats.json): every number the notes and paper cite.
- `jaleesbench/jaleesbench/data/mini_v1.json`: the frozen list.
- `codev/experiments/24-jaleesbench-mini/notes.md`: the record.
- `docs/paper/jaleesbench-mini-paper.tex` (+ PDF): standalone short paper,
  same preamble/bib as the other two papers, built with `latexmk -xelatex`.

## Phases

1. **Module + tests** — `mini.py` with table, estimands, constraints, greedy,
   random, stratified, LOO, criteria, bootstrap; `tests/test_mini.py` on
   synthetic judgments (constraint feasibility, greedy determinism, criteria
   logic, LOO plumbing, missing-framing tolerance) plus a real-data test that
   skips when `judgments.jsonl` is absent and otherwise checks the full-bench
   references against `paper_stats.json`.
2. **Run V1** — random, stratified, greedy over the k grid; find k\*; freeze.
   Record whether H1/H2 hold *before* looking at anything else.
3. **Run V2/V3/V3b, per-pressure, bootstrap, annealing/MILP gap.**
4. **Analyze** — fill notes.md, write the review, draft the paper, ask the
   architect for the V4 subject.

## Dependencies

- Data: main checkout `jaleesbench/results/{judgments,judgments_v2,judgments_ar,judgments_ansari_mod,judgments_thinking}.jsonl` (read-only, absolute path via `--results`).
- `numpy` (already a dev dep); `scipy` (add to dev group for the MILP stretch).
- LaTeX toolchain already used for the two existing papers.

## Measurements recorded

Per method × k: LOO max abs error per estimand, sign flips, τ on separated
pairs, pass/fail (or pass rate). Per frozen mini: in-sample and LOO errors,
per-judge errors, Arabic errors and ρ, variant errors, per-pressure
steadfastness errors, CI inflation, annealing/MILP gap. Wall time and seeds.
