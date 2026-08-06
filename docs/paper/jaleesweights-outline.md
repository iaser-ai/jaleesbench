# JaleesWeights — paper outline (draft, 2026-08-04)

Title (CONFIRMED by Waleed 2026-08-05): **JaleesWeights: Internalizing the
Righteous-Companion Disposition into Open Weights**. Companion paper to JaleesBench (paper 1); every section
follows the house format: orienting intro paragraph first, real subsections
(no bold run-in headings), results subsections titled by finding. Status tags:
[DONE] = result in hand (issue #21), [PLANNED] = experiment agreed as needed,
[OPEN] = awaiting Waleed's ruling.

---

## 1. Introduction

Paper 1 ended on a gap this paper closes: every frontier model has a large
guided ceiling — the jalīs ṣāliḥ disposition is *prompt-reachable* — but real
deployment rarely grants the prompt. The question here: can the disposition
live in the weights? Contributions: (i) a two-stage recipe (judge-filtered
context distillation, then on-policy preference sharpening anchored at the
distilled checkpoint) that takes an open 31B model from the pool's bottom
tier to above the best open base model, bare; (ii) a mechanism account of why
preference optimization alone cannot do this (samplability boundary); (iii)
eval-rigor methodology for single-sample-per-cell benchmarks (same-stack
controls, cell-flip floor, paired per-cell tests).

## 2. Related work

Orienting intro highlighting the three strands the recipe sits on.

### 2.1 Context distillation and constitutional pipelines
Askell et al. (context distillation); Bai et al. (Constitutional AI: SL stage
then RLAIF); descriptive, per house style — the critique-revision variant
described on its own terms (we run the direct-distillation cousin).

### 2.2 Preference optimization and its limits
DPO; iterated/on-policy DPO; rejection-sampling fine-tuning (RAFT/ReST);
literature on DPO as ranking-not-behavior and on off-policy pathologies.

### 2.3 Value and faith-conditioned fine-tuning
Whatever exists on tuning models toward normative dispositions; paper 1's
GUIDE_MIN case study as the prompt-level antecedent.

## 3. Setup

Brief instrument recap (sittings, six pressures, three framings, five bands,
two judges — cite paper 1), then what is new to this paper's protocol.

### 3.1 The internalization task
Unstated framing = deployment condition; the model's own guided run = the
teacher signal. Target metric: post-pressure Jalees score, bare.

### 3.2 Split, judge holdout, and controls
70/70 scenario split (seed 3446); Gemini selects training data, Opus judges
held-out evals and never touches selection; the same-serving-stack base
control as the comparison point for every arm (the vLLM-vs-provider shift,
−0.058, exceeded several arms' apparent effects).

### 3.3 Model and training envelope
gemma-4-31b (open weights, Apache 2.0), QLoRA r32 on one H200; full pipeline
≈ $110. [PLANNED: second model — Inkling replication or another open model.]

## 4. Why preference optimization alone does not move the disposition

Framed as the motivating ablation, not the headline (per ruling). Orienting
intro: five DPO arms across two models and three data constructions, all
statistically zero against the proper control, with training metrics healthy
throughout.

### 4.1 The samplability boundary
K=4 hot draws per training cell: 317/420 cells yield zero good-band samples
from base. Preference contrast cannot create behavior the policy barely
samples. (Histogram figure — the single plot that predicted every flat arm.)

### 4.2 Ranking is not behavior
Train pref-acc 0.83–1.0 on every arm; held-out behavior unmoved. Off-policy
chosen text teaches cross-model ranking.

### 4.3 Temperature does not rescue sampling
T=1.3 leaves the band distribution unchanged: cave-vs-hold is
scenario-determined, and per-cell bistable.

### 4.4 What looked like harm was measurement
Serving-stack shift + ~29% per-resample cell-flip floor account for all
apparent per-cell regressions; the no-training control flips more cells than
any arm. (Eval-rigor contribution; paired transcript pair as the figure.)

## 5. The JaleesModel recipe

Orienting intro: two stages, each doing what the other cannot — distillation
creates the behavior, preference contrast consolidates it under pressure.

### 5.1 Stage 1: judge-filtered context distillation
The model's own guided sittings, band ≥ +1 both scopes, guide-reference and
dangling-citation screens, re-rendered bare (the guide lives outside the
turns, so the transform is exact). 316 examples; masked NLL, both assistant
turns; lr 5e-5, 2 epochs.

### 5.2 Stage 2: on-policy preference sharpening at the distilled anchor
K=4 chains from the distilled policy per training cell; Gemini bands;
max-gap both-direction anchored pairs (relative preference, gap ≥ 2), 518
pairs / 171 cells; DPO with the SFT checkpoint as reference (two-adapter
implementation, policy ≡ ref verified at init); β 0.1, lr 1e-5, 1 epoch.

## 6. Results

Each subsection titled by its finding (house style), each opening with the
one-sentence version.

### 6.1 Distillation creates the behavior [DONE]
−0.335 → +0.188 post-pressure bare; turn-1 reaches the open-model top tier.

### 6.2 Weights and context compose: the guided ceiling rises [DONE]
Tuned + guide = +0.788 vs base + guide +0.569; the under-pressure drop with
the guide shrinks to −0.076. Guide users get a better model, not a degraded
one.

### 6.3 Distillation makes the policy's own training data minable [DONE]
Sample band mode flips from cave (59% −2) to hold (44% +2); pair-mining
yield triples. This is the empirical content of "SL before RL."

### 6.4 Preference sharpening buys steadfastness [DONE]
+0.188 → +0.408; paired per-cell +0.220 [+0.129, +0.317]; pressure drop
−0.243 → −0.110; final model exceeds base Inkling bare, ~63% of its own
raised ceiling.

### 6.5 Guards hold: no citation fabrication, register intact [DONE]
0 [n]-markers across all tuned-arm sittings; length profile flat;
previously-bistable worst cells hold warmly.

### 6.6 The result replicates on a second model [PLANNED]
Inkling (or second open model) through the identical pipeline.

### 6.7 The result survives the second judge [PLANNED]
Final checkpoint through the dual-judge protocol (~$20) to retire
"Opus idiosyncrasy."

## 7. Side effects: does the disposition over-apply? [PLANNED — required]

The most likely reviewer attack and the honest open question. Probe suite:
neutral/secular prompts, non-Muslim interlocutors, ordinary assistant tasks;
question is whether the tuned model volunteers religious counsel uninvited
or loses general capability. Design TBD; results decide whether this is a
finding ("the disposition stays context-appropriate") or a limitation.

## 8. Limitations

One model until §6.6 lands; one seed; LoRA-only (no full fine-tune);
transfer measured within the bench's scenario distribution; steadfastness
gap to the guided ceiling remains (−0.110 vs −0.076); English only (paper
1's Arabic replication not yet run on the tuned model).

## 9. Conclusion

## 10. Future work

Iteration (does round 2 keep climbing toward the ceiling?); proof-grounded
distillation with hardened citation verification [OPEN — citation ruling];
critique-revision variant vs direct distillation [OPEN]; online RL; Arabic
pipeline replication; full-140 confirmation.

---

## Open decisions for Waleed
1. ~~Title~~ — DECIDED 2026-08-05: JaleesWeights.
2. Paper-1 arXiv submission first, so this paper has its citation anchor?
3. Green-light the two [PLANNED] result sections (replication, dual-judge)
   and the §7 side-effect suite — these are the gap between "result" and
   "paper."
4. §4's depth: full ablation table of all five flat arms, or compressed to
   the samplability figure + one table row each?
