# Experiment 58: Prompt fading on JaleesBench with the JaleesWeights models

**Status**: In Progress — pre-registration frozen, no data collected · **Date**: 2026-11-09

Driving issue: #58. Prior work: the MultiBench prompt-fading experiments 76 (pilot, 42
scenarios, seven traditions) and 78 (full 519-scenario corpus), August 2026. This experiment
replicates them on JaleesBench with the JaleesWeights Gemma pair, and extends the separation
ramp from 12k to at least 64k tokens.

Everything from here to "Open decisions" is the pre-registration. It is committed before any
sitting is collected. Sections marked *open* are filled in by the owner's decision and then
frozen in a second commit, still before any data.

## Goal

**Question.** A values guide delivered once, at the start of a conversation, lifts a model's
counsel when it sits next to the dilemma. Does that lift fade as value-neutral filler
separates the guide from the dilemma? And does a model whose values were trained into the
weights (JaleesWeights stage 2) hold flat across the same ramp?

**Hypotheses.**

- **H1, prompted fading.** For the prompted arm (base Gemma-4-31B, guide delivered once,
  early), the score falls as separation grows.
- **H2, weights immunity.** For the weights arm (JaleesWeights Gemma stage 2, one-sentence
  stated cue delivered once, early, in the same slot), the score is flat across the ramp.
- **H3, differential (the headline).** The prompted arm's slope is more negative than the
  weights arm's.

**Calibration from the prior work** (different judge, guide and scenario bank, so a
direction check and not a number to match): on experiment 78's Sunni Islam scenarios
(n = 140), the prompted guide went +0.380 → +0.266 over 0 → 12k tokens (slope −0.041 per
level) and stated + weights went +0.657 → +0.586 (−0.025 per level).

## Approach

Inherited from experiment 78 unless listed under "What changes".

### Conversation shape

```
SYSTEM:    framing, delivered ONCE   guide (prompted arm) or stated sentence (weights arm)
[filler user/assistant exchanges]    pre-filled history; none at L0
USER:      probe turn 1              clean
ASSISTANT: reply 1                   generated
USER:      authored pressure turn    clean
ASSISTANT: reply 2                   generated
```

The model only ever generates the two replies. Filler is pre-filled history, identical for
every arm at a given level. Stored turns hold only the clean four-turn exchange, in the
benchmark's collection schema, so the benchmark's judge code scores them unchanged and the
judge never sees the framing or the filler. Arm is stored as `subject`, level as `framing`.

This is a deliberate departure from the benchmark collector, which folds the framing into
*every* user turn. Re-delivering it on every turn puts it next to the dilemma by
construction, so fading could not be observed. One consequence: the prompted arm at L0 is
not the benchmark's "guided" condition, because the pressure turn carries no guide.

### Arms

| Arm | Model | Framing, once | Role |
|---|---|---|---|
| **P** prompted | base `google/gemma-4-31B-it` | the JaleesBench guide (`jaleesbench.prompts.GUIDE`) | expected to fade (H1) |
| **W** weights | base + adapter `gemma-sft-dpo-bf16` (stage 2) | the stated sentence (`jaleesbench.prompts.STATED`) | expected flat (H2) |

The framing is the opening **system message** for both arms (owner decision, 2026-11-09): the
channel experiment 78 ran. Gemma-4's chat template has a real system turn. The benchmark
itself delivers framing in the user turn, so these numbers are not the benchmark's
"guided" condition.

Both strings are imported from the benchmark, never retyped. Both arms run on one serving
endpoint, the same base weights, the same sampling.

**Unprompted floor: reused, not re-run** (owner decision, 2026-11-09). The L0 check uses the
existing same-stack control, `data/reference/collect_eval_basevllm.jsonl` (subject
`gemma-base-vllm`, no framing, 420 sittings = these same 70 probes × 6 pressures, collected
2026-08-04), with its Opus after-pushback judgments in
`data/reference/judgments_eval_gemma.jsonl` (mean −0.335, the paper's base figure). How its
settings compare with what this experiment serves:

| Setting | Existing control | This experiment |
|---|---|---|
| Model, precision | `google/gemma-4-31B-it`, bf16, no adapter | same |
| Sampling | model defaults: temperature 1.0, top-p 0.95, top-k 64 | same, sent explicitly |
| Reply cap | 8,192 tokens | 8,192 tokens |
| Chat template | the model's own, via the tokenizer | the model's own, via the vLLM server |
| Probes, pressures, turn texts | held-out 70 × 6 | same |
| Judge | Opus, benchmark rubric | depends on the judge decision |
| vLLM | offline batch engine, version of August 2026 (unpinned `vllm>=0.10`) | OpenAI-compatible server, current version |
| GPU, window | H200, 32,768 | B200, ~80,000 |
| Seed | 3446, one batch stream | 3446, per request |

The first five rows match. The last three do not: engine mode, vLLM version, GPU and random
stream differ. None changes the prompt or the sampling distribution, so the control is a
cross-run anchor on the same instrument, not an in-run arm, and is reported as such. If the
judge is not Opus, the control has no matching judgments and its 420 sittings would need
judging by the chosen judge.


### Separation ramp

| Level | Filler between framing and dilemma |
|---|---|
| L0 | none (adjacent) |
| L1 | ~1,000 tokens |
| L2 | ~4,000 tokens |
| L3 | ~12,000 tokens |
| L4 | ~32,000 tokens |
| L5 | ≥ 64,000 tokens |

Levels are sized in Gemma tokens, counted with the model's tokenizer when the filler is
built, and confirmed from the served token counts. (Experiments 76/78 sized by characters ÷ 4,
which overstated their 12k level by about 15%.) Each level's filler is a prefix of the next.

### Filler bank

A static, committed file of value-neutral question-and-answer exchanges, long enough to reach
L5 **without repeating** (the 78 bank was ~5k tokens and was cycled; both prior write-ups
named a non-repeating bank as the fix). The 21 exchanges of the 76/78 bank are kept verbatim
as its opening. New exchanges cover the same kind of ground: cooking, geography, arithmetic,
weather, household how-to, plain science and trivia. Rules: no moral, religious, political,
medical-advice or emotionally loaded content. Before use the bank is screened by a committed
keyword check (religion, ethics, politics, family conflict, money dilemmas, health scares),
and every exchange is read once. The bank is fixed before the smoke and not edited after.

### Scenarios, pressures, scope

- The **70 held-out probes** of `jaleesweights/split_70_70.json` (the `test` list) × the six
  authored pressures. The JaleesWeights adapters were trained on the other 70; those are
  excluded entirely, for every arm, so nothing is tested on training data (owner decision,
  2026-11-09). This is the scenario set of the paper's own results table.
- After-pushback scope only (the whole four-turn exchange): one judgment per sitting.

### Sampling

The benchmark's convention: the model's own generation defaults (temperature 1.0, top-p 0.95,
top-k 64), one sample per cell, seed 3446 sent with every request. This differs from 76/78
(temperature 0). Reply cap 8,192 tokens, as in the JaleesWeights collections (their longest reply is 1,183);
a reply that hits the cap fails the sitting loudly instead of being stored.

### Judge

Claude Opus (`claude-opus-4-8`) alone, through the batch API (owner decision, 2026-11-09):
the judge the JaleesWeights paper uses for held-out results. The JaleesBench rubric and
per-probe proof texts (`jaleesbench.prompts.judge_blocks`), bands −2…+2, reported halved on
−1…+1 as everywhere else in this repository.

### What changes from experiment 78

| | 78 | here |
|---|---|---|
| Scenarios | 519, seven traditions (Sunni Islam 140) | the 70 held-out JaleesBench probes |
| Guide | per-tradition guide | the JaleesBench guide |
| Weights model | MultiWeights adapter | JaleesWeights Gemma stage 2 |
| Ramp | 4 levels to 12k | 6 levels to ≥ 64k |
| Filler | 5k bank, cycled | non-repeating bank |
| Sampling | temperature 0 | model defaults, seeded |
| Judge | one Gemini Flash judge | Opus, batch |
| Floor for the L0 check | another run, other scenarios | the paper's same-stack control, same probes |
| Framing channel | system message | system message |

## Pre-registered analysis

**Unit.** Per-cell score = the judge's band ÷ 2 for one (probe, pressure, level, arm).
Per-scenario score = mean of that probe's six pressure cells at a level and arm.

**Slope.** For each probe and arm, the least-squares slope of per-scenario score on the
ordinal level 0…5. An arm's slope is the mean over probes. Total change over the ramp =
5 × slope.

**Inference.** Scenario-clustered bootstrap, 2,000 resamples of probes with replacement,
seed 3446, percentile 95% intervals. Claims rest on where the interval sits against 0 and
against τ.

**Materiality.** τ = 0.15 over the full ramp (L0 → L5), the floor used in 76/78.

**Decision rules.** Locked; no re-scoring and no change of threshold after data.

- **L0 check** (must pass for H1 to mean anything): P at L0 is at least 0.15 above the reused unprompted control (paired by probe).
  If not, H1 is reported as not testable.
- **H1 confirmed**: slope_P interval excludes 0, slope is negative, and −5 × slope_P ≥ 0.15.
  Interval excludes 0 but the total is under 0.15: reported as "fade present, below the
  materiality floor". Interval includes 0: no fading.
- **H2 confirmed**: |5 × slope_W| < 0.15 and its interval lies inside ±0.15 (equivalence, not
  mere non-significance).
- **H3 confirmed**: slope_P − slope_W interval excludes 0 and is negative.
- **If the weights arm fades materially** (interval excludes 0 and 5 × |slope_W| ≥ 0.15):
  H2 fails as stated, and the write-up says that the design cannot tell values fading from
  ordinary long-context degradation. A base, no-framing arm across the whole ramp would
  separate the two; it is not part of this run and would need its own approval.

**Secondary, all pre-registered and reported whatever they show.**

1. Level means per arm with intervals (the curve figure).
2. End-point contrast L5 − L0 per arm and its difference between arms, paired by probe.
3. The same slopes on L0–L3 only (total = 3 × slope), the ramp 76/78 ran, as the like-for-like
   replication check.
4. Slopes per pressure, per arm (the small-multiples figure). Descriptive.
5. Slopes against log10(1 + measured filler tokens) as a robustness check on the ordinal axis.

**Power.** With 70 probes the intervals are wider than experiment 78's Sunni Islam ones
(n = 140, half-width about ±0.018 on the prompted slope); roughly ±0.025 is to be expected.

**Cost actuals** are reconciled from usage (judge tokens × price; `modal billing report`)
and reported before any conclusion, at the smoke and again after the full run.

## Cost preflight

Figures are estimates for the decision; the smoke replaces them with measured ones.

**Grid.** 70 probes × 6 pressures × 6 levels = 2,520 sittings per arm. Two arms: 5,040.
No floor arm is run. Each sitting is two generations and one judgment.

**Judge, per judgment, after-pushback scope** (measured from this repository's existing
judgments of Gemma transcripts, at current list prices):

| Judge | Per judgment | Basis |
|---|---:|---|
| Claude Opus, batch API | $0.011 | main run: 2,352 in + 320 out + cache, at half price |
| Claude Opus, live | $0.022 | same tokens, full price |
| Gemini 3.1 Pro, live (Developer API) | $0.027 | main run: 3,266 in + 1,740 out |
| Gemini Flash via OpenRouter (the 78 judge) | $0.013 | experiment 78's reconciled rate |

**Serving.** Gemma-4-31B's native window is 262,144 tokens, so 64k is inside it. The cost is
memory: the key-value cache is about 0.94 MB per token (60 layers × 16 KV heads × 256 × 2 ×
2 bytes), so one 70k-token conversation needs about 66 GB (up to 75 GB at the 80k window) on top of 62 GB of weights. An
H200 (141 GB) at the current 92% setting leaves about 65 GB, which does not fit. A single
B200 (~180 GB) leaves about 100 GB: one shared 65k filler prefix plus roughly 16 concurrent
conversations, provided vLLM's prefix cache shares the filler across requests (the filler is
identical for every sitting at a level, and collection is ordered by arm and level to keep it
resident). These memory figures are derived, not measured; the smoke's 64k sitting is the
proof.

Estimate for 5,040 sittings: L0–L3 about 2 GPU-hours (78's measured 2,540 sittings/hour,
scaled for longer replies); L4–L5 about 3–6 GPU-hours (long-context decoding, limited
concurrency); about $7 per B200-hour all-in, plus cold starts. **≈ $60, range $40–100.** The
top of the range is the case where prefix sharing does not work and ~190M filler tokens are
prefilled in full. All levels are served by the same deployment so that hardware is not
confounded with level.

**Filler bank.** Written in the builder session and screened; no API spend.

**Smoke.** ≈ $5: one cold start, 24 sittings including one at L5, 24 live judgments.

### Totals by option

Base configuration: two arms, the 70 held-out probes, system channel, Opus batch judge.

| Configuration | Sittings | Judge | Serve | Total |
|---|---:|---:|---:|---:|
| **Base** | 5,040 | $55 | ≈ $60 | **≈ $120** (range $100–$160), smoke included |

| Judge alternative, change to the base total | |
|---|---:|
| Opus live instead of batch (results in minutes, not hours) | + $55 |
| Gemini Flash via OpenRouter (the 78 judge) instead of Opus | + $16 (includes judging the control), plus a small judge adapter |
| Opus + Gemini 3.1 Pro, after-pushback scope | + $147 (includes judging the control) |
| Opus + Gemini 3.1 Pro, both scopes | + $305 |

| Separate line | |
|---|---:|
| Inkling-Small as a second pair | + ≈ $75–$200, feasibility not yet established |

Inkling-Small: 5,040 more sittings on the Tinker API. Judge $55 (Opus batch). Generation is
the unknown: about 195M prompt tokens, whose cost depends on whether Tinker bills repeated
prefixes at its cached rate (about $20 total if so, about $75–$140 if not; the current
Inkling-Small price needs to be read off Tinker's price list). Two things must be confirmed
free of charge before it could run: that Tinker serves Inkling-Small with a window of at
least 70k tokens, and that the stage-2 adapter is still retrievable. In the paper stage 2
added nothing over stage 1 on this model.

## Decisions

1. **Delivery channel. DECIDED (owner, 2026-11-09):** system message only.
2. **Judge. DECIDED (owner, 2026-11-09):** Opus only, batch pricing.
3. **Training-half contamination. DECIDED (owner, 2026-11-09):** run only the 70 held-out
   probes; the 70 training probes are excluded entirely, for every arm.
4. **Unprompted floor. DECIDED (owner, 2026-11-09):** not re-run; the existing same-stack
   control is reused (see Arms).
5. **Inkling-Small. DECIDED (owner, 2026-11-09):** not run.
6. **Budget. DECIDED (owner, 2026-11-09):** ceiling $160 in total; pause and report if GPU
   spend passes $100.

All six decisions are made. The design above is frozen as of this commit; no data exists yet.

## Binding sequence

1. This pre-registration, committed. **Nothing paid before the decisions above.**
2. Decisions recorded here and frozen in a second commit. Filler bank built and screened;
   code ported from experiment 78.
3. Smoke: 24 sittings, both arms, all six levels, including the 64k sitting that proves
   the window. Checks: arm and level survive into the judgments; no guide, stated sentence or
   filler in any judged turn; measured filler tokens per level; throughput per level.
   Reconciled actuals. **Stop and report.**
4. Full run, detached, resume-safe by cell key, outputs under
   `jaleesweights/data/runs/fading-58/`. Cost actuals before conclusions.
5. Analysis, figures, paper paragraph and figure, pull request.

## Environment & Reproduction

To be filled in when the code lands. The Modal volume holding the adapters is read-only for
this experiment: no training, nothing overwritten, a new serving app only.

## Code

To be filled in when the code lands.

## Results

None yet.

## What Worked / What Didn't

None yet.

## Next Steps

Filler bank, code, smoke test; then stop and report.
