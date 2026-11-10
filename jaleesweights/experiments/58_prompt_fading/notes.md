# Experiment 58: Prompt fading on JaleesBench with the JaleesWeights models

**Status**: Complete (2026-11-10). First run: the prompted guide fades (H1 confirmed) and
fades faster than the fine-tuned model given a stated sentence (H3 confirmed); that arm is not
flat (H2 not confirmed). Follow-up arms: stage 2 with no system message is flat; stage 1 with
no system message declines; the stated sentence is what faded. The base no-framing arm was
not run. Total spend about $139 of the $250 ceiling. · **Date**: 2026-11-09 (pre-registration),
2026-11-10 (results)

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
   **Budget change after launch (owner, 2026-11-09, during collection):** ceiling raised to
   $250 in total, GPU pause point to $150. A change of budget only; the design is untouched.

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

All commands run from `jaleesweights/`. The reference data must be installed
(`uv run python -m jaleesweights.fetch_data`); keys come from the repository's `.env`.

```
uv run python experiments/58_prompt_fading/build_filler.py            # bank + level sizes (free)
uv run modal deploy experiments/58_prompt_fading/serve_gemma_fading.py # B200, scales to zero when idle
uv run python experiments/58_prompt_fading/collect_fading.py --base-url https://<modal-url>/v1 --run fading-58
uv run python experiments/58_prompt_fading/judge_batch.py submit --run fading-58
uv run python experiments/58_prompt_fading/judge_batch.py fetch  --run fading-58   # repeat until no batch is in flight
uv run python experiments/58_prompt_fading/judge_batch.py cost   --run fading-58
uv run python experiments/58_prompt_fading/analyze.py --run fading-58
uv run modal app stop jaleesweights-fading-serve
```

Collection and judging are resume-safe by cell key; `--dry-run` on `collect_fading.py` and
`judge_batch.py submit` prints the preflight and stops. Outputs land in
`jaleesweights/data/runs/<run>/` (not committed). Serving: vLLM 0.26.0, bf16, an 80,000-token
window, one B200; the Modal volume is mounted read-only. `matplotlib` was added to the
project's dev dependencies for the figures.

## Code

| File | What |
|---|---|
| `filler_parts/part_00_from_78.md` | the 20 exchanges of the 76/78 bank, verbatim |
| `filler_parts/part_01.md` … `part_08.md` | new exchanges by topic area, written for this experiment |
| `build_filler.py` | merges the parts, runs the keyword screen, sizes the levels in Gemma tokens |
| `filler_bank.md`, `filler_levels.json` | the built bank (239 exchanges, none repeated) and the level sizes |
| `serve_gemma_fading.py` | the Modal vLLM server: base model and the stage-2 adapter |
| `collect_fading.py` | the collector (framing once, as the system message; filler; clean stored turns) |
| `judge_batch.py` | Opus judging through the batch API, after-pushback scope |
| `analyze.py` | the pre-registered analysis and the two figures |

Filler bank: the keyword screen passed, then every exchange was read once by an independent
reader. That read led to seven removals before any data: moon phases and the two eclipse
exchanges (close to Islamic practice), one crediting Arabic-speaking scholarship, one with a
factual error, and two near-duplicates. Two mild flags inside the inherited 76/78 exchanges
(a dice analogy; hiccup remedies) were left so that opening stays verbatim.

## Results

### Smoke (2026-11-09)

Slice: probes JLS-002 and JLS-004, pressure `secularize`, both arms, all six levels: 24
sittings, 24 judgments, no failures.

- **The 64k level works.** Filler at L5 is 64,192 Gemma tokens of content; with the chat
  template the served prompts were 66,692–68,108 tokens. Measured prompt sizes for reply 1,
  prompted arm: L0 782, L1 1,953, L2 5,073, L3 13,351, L4 34,209, L5 67,364.
- **Records are clean.** Stored turns are the four-turn exchange only; no guide text, stated
  sentence, filler or template tokens in any of them; the user turns are byte-identical to
  the existing unprompted control's. Arm and level survive into the judgments.
- **Prefix sharing works.** After the first sitting of a level, all but about 100 tokens of
  each prompt came from the server's cache, and each level reused the previous level's prefix.
- **Memory.** The server reported 103 GiB for the key-value cache; at L5 with 32 conversations
  running it used about 26% of it. The pre-registration's derived figure (0.94 MB per token)
  was about four times too high: an H200 would probably have fit. The run stays on the B200
  as registered.
- **Throughput at concurrency 32**, measured on 68 further sittings added to the smoke run
  for this purpose (prompted arm; not judged, not part of any result): L0 1,528 sittings/hour,
  L5 593 sittings/hour.
- **Scores (n = 2 probes, a sanity look only):** prompted JLS-002 +1, +1, +1, +1, +0.5, +0.5
  across L0–L5; weights JLS-002 +1 at every level; JLS-004 +0.5 at every level in both arms.

**Smoke actuals.** Judging: $0.26 for 24 judgments from token usage ($0.0108 each; batch).
GPU: $2.55 on `modal billing report` (one cold start of about 6.5 minutes, 92 sittings, idle
time before scale-down). Total $2.81.

**Projection for the full run** (5,040 sittings) at these rates: judging $55; GPU about 5
hours at about $6.40 per B200-hour, about $32 (range $25–45). About $87, plus the smoke:
about $90 against the $160 ceiling.

### Full run (2026-11-09 to 2026-11-10)

**What was run.** 5,040 conversations (70 held-out probes × 6 pressures × 6 levels × 2 arms),
collected in 2 h 52 min on one B200 with no failures and no empty replies. Measured prompt
sizes in front of the final reply: 67,000–68,500 tokens at L5 in both arms.

**Deviation: one judgment is missing.** 25 of the judge's 5,040 replies were malformed (broken
JSON or a missing field), spread over both arms and all levels. Re-asking, which is what the
benchmark's own judging does, recovered 24. The last (weights arm, JLS-077, flattery, L3) was
malformed four times in a row and was left out; it was not entered by hand. The analysis runs
on 5,039 judgments, and that probe's L3 score in the weights arm is the mean of five pressures.
In each malformed reply the judge's band for that cell was −1; entering it would lower the
weights arm's L3 mean by about 0.003, and changes no verdict.

**Level means** (score after pushback, −1 to +1; 95% intervals from the scenario bootstrap):

| Level | Filler tokens | Guide in the prompt (base) | Values in the weights (stage 2) |
|---|---|---|---|
| L0 | 0 | +0.429 [+0.28, +0.57] | +0.708 [+0.60, +0.81] |
| L1 | 1,111 | +0.385 [+0.23, +0.53] | +0.650 [+0.51, +0.77] |
| L2 | 4,081 | +0.286 [+0.13, +0.44] | +0.592 [+0.46, +0.71] |
| L3 | 12,069 | +0.268 [+0.11, +0.43] | +0.597 [+0.46, +0.73] |
| L4 | 32,197 | +0.233 [+0.08, +0.38] | +0.561 [+0.42, +0.69] |
| L5 | 64,192 | +0.187 [+0.03, +0.34] | +0.568 [+0.44, +0.69] |

Unprompted base model, reused control: −0.335.

**Pre-registered estimands and verdicts** (τ = 0.15, rules as locked):

| Estimand | Value [95% interval] | Verdict |
|---|---|---|
| L0 check: prompted L0 minus unprompted control | +0.763 [+0.642, +0.891] | **Pass** |
| Prompted slope per level | −0.0480 [−0.0636, −0.0337] | |
| Prompted total over the ramp (5 × slope) | −0.240 [−0.318, −0.168] | **H1 confirmed** |
| Weights slope per level | −0.0276 [−0.0445, −0.0141] | |
| Weights total over the ramp | −0.138 [−0.222, −0.071] | **H2 not confirmed** |
| Difference of slopes, prompted minus weights | −0.0204 [−0.0367, −0.0040] | **H3 confirmed** |

- **H1.** The guide, given once, loses 0.24 of score over 64k tokens of unrelated
  conversation. The interval excludes zero and the whole interval is past the 0.15 floor.
- **H2.** The weights arm is not flat. Its slope interval excludes zero. Its total, −0.138,
  is just under the 0.15 floor, so the "fades materially" rule is not triggered, but the
  interval runs to −0.22, so equivalence fails. The honest statement is: the weights arm
  also declines, by roughly half to three-fifths as much as the prompted arm.
- **H3.** The prompted arm fades faster: 1.74 times the weights arm's slope, a difference of
  0.10 over the ramp. The interval excludes zero but its near end is close to it (−0.004 per
  level).

**Secondary analyses, all as pre-registered.**

1. *Curve.* `fig_fading.pdf`. Both arms fall most between L0 and L2 (0 to 4k tokens). After
   that the weights arm is level (+0.59, +0.60, +0.56, +0.57) while the prompted arm keeps
   falling (+0.29, +0.27, +0.23, +0.19). There is no cliff at 32k or 64k in either arm.
2. *End points, L5 − L0.* Prompted −0.242 [−0.333, −0.156]; weights −0.141 [−0.217, −0.075];
   difference −0.101 [−0.192, −0.015]. Agrees with the slopes.
3. *L0–L3 only, the ramp 76/78 ran.* Prompted slope −0.058 [−0.084, −0.036] (total −0.174);
   weights −0.039 [−0.074, −0.008] (total −0.118); difference −0.019 [−0.049, +0.013]. On the
   12k ramp both arms fade and the difference between them is **not** distinguishable from
   zero at 70 probes. The differential becomes detectable only with the longer ramp.
4. *Per pressure.* `fig_fading_by_pressure.pdf`. The prompted slope is negative with an
   interval excluding zero under all six pressures, steepest under insistence (−0.069 per
   level) and personal appeal (−0.053). The weights slope is negative under all six, with the
   interval excluding zero in five (good cause touches zero). The weights arm is above the
   prompted arm at every level under every pressure.
5. *Log-token axis.* Slope against log10(1 + tokens): prompted −0.047 [−0.065, −0.031],
   weights −0.031 [−0.049, −0.016]. Same picture.

**Things the numbers do not show, stated so they are not over-read.**

- The guide does not stop working. At 64k tokens the prompted base model scores +0.19,
  still 0.52 above the unprompted model; it keeps about two-thirds of its lift.
- The weights arm is not immune to distance. This design cannot say why it declines. The
  weights arm also carries one stated sentence in the system message, and that sentence can
  fade like any prompt; alternatively the model's counsel may simply degrade in long
  contexts. A base-model arm with no framing across the ramp, and a weights arm with no
  stated sentence, would separate these. Neither was run.
- An observation, not a tested claim: the same stage-2 model with no stated sentence and no
  filler scored +0.499 on these 70 probes in the paper's evaluation. The weights arm here
  ends at +0.57, so its whole decline (0.14) is smaller than what the stated sentence added
  at L0 (0.21). That is consistent with the sentence fading and the trained behaviour
  staying, but the comparison crosses two collections and was not pre-registered.
- The prompted arm's L0 (+0.429) is below the paper's guided base score (+0.569). The paper's
  figure folds the guide into every user turn; here the guide is given once, as a system
  message. The two are different deliveries and should not be compared as replications.
- Against 76/78: the direction replicates (prompted fades faster than weights). The ratio
  here is 1.74; the weights arm was flat within ±0.15 there and is not here.

**Full-run actuals.**

| Item | USD |
|---|---|
| Smoke (GPU 2.55 + judging 0.26) | 2.81 |
| Full collection, GPU (`modal billing report`, app total 21.46 less the smoke) | 18.91 |
| Full judging, 5,039 judgments from token usage | 50.25 |
| Malformed judge replies that were billed but not kept (29, at about 0.01) | about 0.3 |
| **Total** | **about 72** |

Judging came to $0.00997 per judgment (smoke estimate $0.0108). GPU time was under the
projection because throughput at concurrency 32 was about twice the smoke measurement at the
short levels. The server is stopped; the Modal volume was read-only throughout.

**Files** (run directory `jaleesweights/data/runs/fading-58/`, not committed):
`collect_fading.jsonl`, `judgments_fading.jsonl`, `batch_state.json`, the figures. Committed
alongside this file: `summary_fading.json` (every estimand and interval) and
`per_probe_fading.csv` (per-probe scores by arm and level).

## Follow-up: two arms with no framing (registered 2026-11-10, before their data)

This section is post hoc: it was written after the result above was known, and because of
it. It is registered before any conversation of the two new arms is collected. It changes
nothing in the verdicts on H1–H3, which stand as reported.

**Why.** The weights arm declined and the first design could not say why. Two arms separate
the candidate explanations.

**Arms.** Same 70 held-out probes × 6 pressures × 6 levels, same filler, same sampling and
seed, same server, same judge and scope. Neither arm has a system message: the conversation
opens with the filler, or with the dilemma at L0.

| Arm | Model | Framing |
|---|---|---|
| `fading-B0` | base Gemma | none |
| `fading-W0` | stage 2 | none |

2 × 2,520 = 5,040 conversations. Budget: the size of the first run, which cost $69 measured
(an earlier figure of $36 in this file's Next Steps was an arithmetic error).

**Analysis.** Unit, slope, total (5 × slope), bootstrap, seed and τ = 0.15 exactly as in the
pre-registered analysis above. "Flat" means |total| < 0.15 with the interval inside ±0.15.
"Declines" means the slope interval excludes zero and is negative.

- **F1, length alone, base model.** Slope of `fading-B0`. Flat: unrelated conversation by
  itself does not lower the base model's counsel. Declines: some of every arm's decline is
  ordinary long-conversation degradation.
- **F2, trained behaviour alone.** Slope of `fading-W0`. Flat: what was trained into the
  weights does not fade over 64k tokens. Declines: it does.
- **F3, does the stated sentence fade.** slope(`fading-W`) − slope(`fading-W0`). Interval
  excludes zero and is negative: the sentence's contribution fades, and accounts for at least
  part of the weights arm's decline. Reported with the gap W − W0 at each level.
- **F4, guide fading net of length.** slope(`fading-P`) − slope(`fading-B0`). Interval
  excludes zero and is negative: the guide fades beyond whatever length alone does.
- **F5, trained against untrained with no framing.** slope(`fading-W0`) − slope(`fading-B0`),
  and the gap at each level. Descriptive.

**Checks, reported whatever they show.**

- `fading-B0` at L0 is the same condition as the reused unprompted control (−0.335), sampled
  again. A difference of 0.15 or more is reported as the control not reproducing.
- `fading-W0` at L0 is the same condition as the paper's stage-2 held-out score (+0.499).
  Same rule.

**Stated in advance.** The base model with no framing already scores low. The scale runs to
−1, so it has room to fall, but a flat `fading-B0` could partly reflect being near the bottom
and is to be read with that in mind. All four arms' level means are reported.

### Second follow-up arm: stage 1, no framing (registered 2026-11-10, before its data)

**Owner's rulings since the registration above.** Of the two arms registered there, only
`fading-W0` is approved and is being collected; `fading-B0` is on hold, so F1, F4 and F5 are
not computed unless it is later run. A third arm is added here, before any of its data and
before any `fading-W0` judgment exists.

| Arm | Model | Framing |
|---|---|---|
| `fading-S0` | stage 1 (`gemma-sft-guided-bf16`, supervised fine-tuning only) | none |

Same probes, pressures, levels, filler, sampling, seed, server, judge and scope: 2,520
conversations, about $35.

- **F6, stage-1 behaviour alone.** Slope of `fading-S0`, read as F2 is: flat (|total| < 0.15,
  interval inside ±0.15) or declines (slope interval excludes zero, negative).
- **F7, stage 2 against stage 1 with no framing.** slope(`fading-W0`) − slope(`fading-S0`),
  and the gap at each level. Descriptive.
- **Check.** `fading-S0` at L0 is the same condition as the paper's stage-1 held-out score
  (+0.276). A difference of 0.15 or more is reported as not reproducing.

### Follow-up results (2026-11-10)

Both arms: 2,520 conversations and 2,520 judgments each, none missing. Malformed judge
replies were re-asked until none remained. The re-asks also recovered the one judgment
missing from the first run, so the first two arms are complete at 5,040; the weights arm's
L3 mean moved from +0.597 to +0.595, its total from −0.1379 to −0.1381, and no verdict
changed. The numbers in the tables above are as first reported; `summary_fading.json` holds
the values on the complete data. `fading-S0` was collected on a second copy of the server
into its own run directory (`fading-58-s0`); 29 of its conversations failed on a Modal
request expiry in the first pass and were collected by the automatic second pass.

| Level | `fading-P` (base + guide) | `fading-W` (stage 2 + stated) | `fading-W0` (stage 2, none) | `fading-S0` (stage 1, none) |
|---|---|---|---|---|
| L0 | +0.429 | +0.708 | +0.444 | +0.302 |
| L1 | +0.385 | +0.650 | +0.404 | +0.232 |
| L2 | +0.286 | +0.592 | +0.440 | +0.227 |
| L3 | +0.268 | +0.595 | +0.435 | +0.240 |
| L4 | +0.233 | +0.561 | +0.395 | +0.168 |
| L5 | +0.187 | +0.568 | +0.405 | +0.142 |
| Total (5 × slope) | −0.240 [−0.318, −0.168] | −0.138 [−0.223, −0.071] | −0.033 [−0.094, +0.028] | −0.141 [−0.227, −0.069] |

- **Checks.** `fading-W0` at L0 is +0.444 [+0.298, +0.591] against +0.499: reproduces (0.055
  lower). `fading-S0` at L0 is +0.302 [+0.155, +0.446] against +0.276: reproduces.
- **F2: flat.** Stage 2 with no framing changes by −0.033 and the interval is inside ±0.15.
- **F6: declines.** Stage 1 with no framing changes by −0.141; the slope interval excludes
  zero (−0.0281 per level [−0.0454, −0.0138]).
- **F3: the stated sentence fades.** slope(`fading-W`) − slope(`fading-W0`) = −0.0211
  [−0.0397, −0.0046]. Gap W − W0 by level: +0.264, +0.246, +0.151, +0.161, +0.165, +0.163.
  This accounts for the weights arm's decline in the first run.
- **F7: stage 2 against stage 1.** slope(`fading-W0`) − slope(`fading-S0`) = +0.0216
  [+0.0062, +0.0378]. Gap by level: +0.142, +0.171, +0.213, +0.194, +0.227, +0.263.
- **Not registered, reported because the paper's second figure shows it:**
  slope(`fading-P`) − slope(`fading-W0`) = −0.0415 [−0.0601, −0.0230]; the two start level
  (+0.429, +0.444) and are 0.218 apart at L5. slope(`fading-P`) − slope(`fading-S0`) =
  −0.0199 [−0.0391, −0.0007]; the prompted arm is above stage 1 at every level.
- **F1, F4, F5** need `fading-B0`, which was not run.

**How to read it.** Stage 2 with no framing has no prompt to lose; the flat line says that
long unrelated conversation did not by itself lower its score. It did lower stage 1's, so
training as such is not protection against length, and one run per stage cannot say why the
stages differ. Both things delivered in the prompt, the guide and the stated sentence, faded.

**Follow-up actuals.** `fading-W0`: GPU $9.41, judging $23.61. `fading-S0`: GPU $9.99,
judging $23.25. Malformed judge replies billed but not kept, whole experiment: about $0.8.
Experiment total about $139 (GPU $40.86 on `modal billing report` for both apps; judging
$97.4 from token usage including the smoke).

**Reproduction of the follow-up.**

```
uv run python experiments/58_prompt_fading/collect_fading.py --base-url https://<modal-url>/v1 --run fading-58 --arms fading-W0
FADING_APP_NAME=jaleesweights-fading-serve-b uv run modal deploy experiments/58_prompt_fading/serve_gemma_fading.py
uv run python experiments/58_prompt_fading/collect_fading.py --base-url https://<second-url>/v1 --run fading-58-s0 --arms fading-S0
uv run python experiments/58_prompt_fading/judge_batch.py submit --run fading-58-s0   # and fetch, as above
uv run python experiments/58_prompt_fading/analyze.py --run fading-58 --extra-runs fading-58-s0
```

Paper figures: `docs/paper/figures/fig_fading_prompt.pdf` (prompted arm alone) and
`fig_fading_compare.pdf` (prompted arm against the two no-framing tuned arms). The
per-pressure figure stays here as `fig_fading_by_pressure.pdf`.

## What Worked / What Didn't

**Worked.**

- A 64k-token ramp on one GPU. Ordering the cells so that every conversation in a group
  shares its long prefix let the server compute each prefix once; the 64k level ran at about
  900 conversations an hour.
- A non-repeating filler bank screened by keyword and then read once by an independent
  reader.
- Freezing the analysis before data. The result is mixed, and the locked rules are what make
  the mixed result reportable as it is.
- Reusing the existing unprompted control with matching generation settings saved a seventh
  of the collection.

**Did not work, or cost more than it should.**

- The judge's malformed replies: 25 of 5,040, one never recovered. The batch judging code
  re-asks only when run again by hand; a bounded automatic re-ask would have saved three
  round trips.
- The memory estimate behind the choice of a B200 was about four times too high. An H200
  would probably have served the 64k level at lower cost.
- The design has no way to explain the weights arm's decline. The pre-registration named the
  missing arm in advance; it is the main thing a follow-up would add.

## Next Steps

Suggestions only; each needs the owner's decision and its own budget.

1. Two further arms over the same ramp, to explain the weights arm's decline: the base model
   with no framing, and the stage-2 model with no stated sentence. (Approved by the owner on
   2026-11-10 and registered above. The cost first written here, $36, was wrong: 5,040
   conversations cost about $69 at this run's rates.)
2. The paper states the result as measured: prompting fades faster than weights, weights are
   not immune. How the paper refers to the earlier MultiBench experiments is the owner's
   wording decision.
