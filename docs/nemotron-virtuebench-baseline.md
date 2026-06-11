# Nemotron 3 Ultra on VirtueBench V2 — Baseline Report

*Model-evaluation report — June 2026*

## Summary

We evaluated **NVIDIA Nemotron 3 Ultra** (a 550B-parameter reasoning model, served via Blackbox's
OpenAI-compatible API) on **VirtueBench V2**, a benchmark that tests whether a model *chooses* the
virtuous option when the non-virtuous one is actively rationalized for it. Across the full instrument
— 4 cardinal virtues × 5 temptation types × 150 scenarios = **3,000 forced-choice items** at
temperature 0.7 — Nemotron scored an overall **0.80** (fraction choosing virtue under temptation),
with every cell completing cleanly (**0 infrastructure errors**).

Headline findings:

- **Courage is the weak virtue (0.66)**, well below prudence/justice/temperance (~0.84–0.86). It
  collapses under utilitarian (*ratio* 0.61) and bodily-comfort (*caro* 0.57) framings.
- **Social pressure (*mundus*) is the hardest temptation overall (0.70)** — the large-model profile
  the benchmark authors also report for GPT-5.4.
- **Ornate temptations are the easiest to resist** — *diabolus* (0.85) and *ignatian* (0.87, vice
  couched in scripture). The more elaborately vice is dressed, the more transparent it is to a
  reasoning model.

## What VirtueBench measures

VirtueBench V2 (Tim Hwang / Institute for a Christian Machine Intelligence) places the model, in the
first person, in a concrete dilemma with two options — one virtuous (carrying a real cost: career,
safety, comfort, relationships) and one tempting. The model answers `A`/`B`; the A/B position is
randomized per item, and scoring is exact (did it select the virtuous option?).

- **Virtues (4):** prudence, justice, courage, temperance — the classical cardinal virtues.
- **Temptation variants (5)** — the virtuous option is held fixed across all five; only the
  *mechanism* of the temptation changes, which isolates what each mechanism does to the model:
  - *ratio* — utilitarian rationalization ("the outcome justifies the cost").
  - *caro* — bodily appetite, comfort, fatigue.
  - *mundus* — social pressure, peer consensus, career/reputational risk.
  - *diabolus* — vice reframed as a *secular* virtue ("prudent leadership," "institutional wisdom").
  - *ignatian* — vice reframed as a *Christian* virtue, citing chapter and verse.

**Interpretation caveat:** VirtueBench is an explicitly *Christian-grounded* instrument (cardinal
virtues, patristic sourcing, a Christological temptation taxonomy). "Accuracy" here means agreement
with *its* notion of the virtuous choice — not a tradition-neutral measure of morality.

## Setup & methodology

| | |
|---|---|
| Model | `blackboxai/nvidia/nemotron-3-ultra` (Nemotron-3-Ultra-550B-A55B, FP4) |
| Endpoint | Blackbox AI, OpenAI-compatible (`https://api.blackbox.ai/v1`) |
| Runner | VirtueBench `openai-api` backend (OpenAI Python SDK) |
| Coverage | all 4 virtues × all 5 variants × 150 scenarios = 3,000 items |
| Runs | 1 (single pass) |
| Temperature | 0.7 · **Concurrency** 8 |
| Outcome | 3,000 / 3,000 scored · 0 infra errors |

**Reproducibility note — evaluating a reasoning model.** Nemotron 3 Ultra emits a hidden reasoning
pass (`message.reasoning_content`) *before* its final answer (`message.content`). VirtueBench's
OpenAI runner defaults to `max_tokens=128`, which the reasoning pass exhausts before any answer is
produced — the API returns `finish_reason: "length"` and `content: null`, which would silently fail
**every** call. We raised the runner default to 8,192 tokens (billed per token actually used, not per
cap); answers then arrive cleanly as `A — <one-line rationale>` and parse correctly. This is a
general gotcha when running answer-parsing benchmarks against reasoning models.

## Results

Accuracy = fraction of scenarios where the model chose the virtuous option despite the temptation
(150 scenarios per cell):

| Virtue \ Variant | ratio | caro | mundus | diabolus | ignatian | **mean** |
|---|---|---|---|---|---|---|
| Prudence | 0.900 | 0.920 | 0.700 | 0.873 | 0.867 | **0.852** |
| Justice | 0.827 | 0.847 | 0.693 | 0.893 | 0.920 | **0.836** |
| **Courage** | **0.607** | **0.573** | 0.640 | 0.733 | 0.727 | **0.656** |
| Temperance | 0.840 | 0.813 | 0.767 | 0.913 | 0.973 | **0.861** |
| **mean** | 0.793 | 0.788 | **0.700** | 0.853 | 0.872 | **0.801** |

## Interpretation

1. **The courage gap.** Courage (0.66) is ~0.19 below the other three virtues and is the only one
   that falls below chance-adjacent levels on any cell. It is softest under *ratio* and *caro* — the
   model talks itself out of standing firm via "this serves no purpose" and comfort/self-preservation
   reasoning. (The authors report GPT-4o weakest on courage/*ratio* at ~0.39; Nemotron's 0.61 is
   markedly stronger but still its own worst virtue.)
2. **Fear of the crowd beats appetite.** *mundus* is the hardest temptation in 3 of 4 virtues. A
   model with no body is hardest to move by *caro* in most virtues, but readily moved by social
   pressure and consensus — the published large-model signature.
3. **Sophistication is self-defeating — for the tempter.** The two most elaborate temptations
   (*diabolus*, *ignatian*) are the *easiest* to resist. A reasoning model sees through ornate
   manipulation, including vice dressed in scripture; blunt pressure lands better. Temptation
   strength is **not** monotonic in elaborateness.

## Caveats

- **Single run, no confidence intervals.** At temperature 0.7 run-to-run variance is real; these are
  point estimates. VirtueBench supports multi-run aggregation with bootstrap CIs / McNemar — the
  natural next step before drawing firm conclusions about the courage and *mundus* effects.
- **One model.** No comparative panel yet.
- **Instrument is tradition-specific and forced-choice.** It measures selection between two
  pre-written options, not open-ended moral reasoning or intention.

## Next steps (benchmarking track)

- **Multi-run** (e.g. 10×) to put CIs on the courage weakness and the *mundus* effect.
- **Model panel** (frontier + open weights) for comparative moral profiles.
- **Error analysis** on the courage/*ratio* and */mundus* cells — read the rationales to see *how*
  Nemotron rationalizes when it caves.

---

*Reference implementation: `external/virtue-bench-2` (ICMI VirtueBench V2), wired to Blackbox
Nemotron. Raw outputs: `external/virtue-bench-2/results/nemotron_full_sweep.json` (+ `_logs.json`
for per-scenario responses).*
