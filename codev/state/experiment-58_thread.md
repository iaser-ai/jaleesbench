# experiment-58 thread — prompt fading on JaleesBench

## 2026-11-09 — orientation and pre-registration

- The spec file named in the spawn prompt does not exist; the issue body (#58) is the spec.
  The EXPERIMENT protocol text was not inlined either; read from the installed skeleton.
- Read MultiBench experiments 76 and 78 notes end to end, plus 78's collector, analyzer,
  serve script, judge config and filler bank.
- Pre-registration written: `jaleesweights/experiments/58_prompt_fading/notes.md`. Nothing
  paid, nothing deployed, no filler generated.
- Facts established for free:
  - Gemma-4-31B native window is 262,144 tokens; its chat template has a real system turn.
  - 64k does not fit one H200 at the current settings (derived: ~0.94 MB of KV cache per
    token); a single B200 should. To be proven by the smoke.
  - The stage-2 adapter `gemma-sft-dpo-bf16` is present on the Modal volume.
  - The JaleesWeights adapters were trained on 70 of the 140 probes — raised as a decision.
  - Gemini 3.1 Pro selected the training data, so it is not an independent judge of the
    weights arm; the paper scores held-out with Opus alone — raised under the judge decision.
- Waiting on six owner decisions (channel, judge, training-half handling, floor arm,
  Inkling-Small, budget).

## 2026-11-09 — decision 3

- Owner decision: run only the 70 held-out probes; training probes excluded for every arm.
  Pre-registration and cost table updated (base ≈ $130). Decisions 1, 2, 4, 5, 6 pending.

## 2026-11-09 — decisions 1 and 4

- Owner decisions: system message only; unprompted floor not re-run, the existing same-stack
  control is reused. Grid is 70 × 6 × 6 × 2 = 5,040 sittings; base ≈ $120.
- Checked the control: 420 sittings, exactly the held-out 70 × 6, bf16, model-default
  sampling, 8,192 cap, the model's own chat template. Its Opus judgments are in
  `judgments_eval_gemma.jsonl` (not `judgments_eval.jsonl`); mean −0.335. Differences from
  this experiment: offline engine vs server, vLLM version, H200 vs B200, random stream.
  Reply cap raised from my 4,096 to 8,192 to match. Told the architect.
- Decisions 2, 5, 6 pending.

## 2026-11-09 — GO, filler, code, smoke

- Final decisions: Opus batch; no Inkling-Small; ceiling $160, pause at $100 GPU. Frozen.
- Filler bank built by eight parallel writers by topic, keyword-screened, then read in full by
  an independent reader; seven exchanges removed on that read. 239 exchanges, 64,192 tokens.
- Deployed `jaleesweights-fading-serve` (B200, vLLM 0.26.0, 80k window, volume read-only).
- Smoke passed: 24 sittings incl. 64k, 24 judgments, clean records. Prefix cache hit ~95%.
  Surprise: my memory estimate was ~4x too high; the H200 would likely have fit.
- Smoke cost $2.81. Full-run projection about $87. STOPPED; waiting for the word.

## 2026-11-09 15:19 PST — full run launched

- GO received. Collection running detached from this worktree, outputs and log in the main
  checkout's `jaleesweights/data/runs/fading-58/` (`collect.log`). Resumable: re-run the same
  command. A watcher stops it if today's GPU bill for the app passes $95.
- 15:36 PST: budget raised after launch to $250 total, GPU pause $150. Watcher restarted with
  the new stop (the watcher is a separate process; the collection was not touched). First
  group ran at 2,924 sittings/hour.

## 2026-11-09 18:20 PST — collection finished, judge batch submitted

Full collection done: 5,040 of 5,040 conversations, 0 failures, 2 h 52 min on one B200.
Throughput fell with filler length as expected (about 3,000/h with no filler, about 900/h at
64k). GPU bill for the app so far 21.37 USD including the 2.55 USD smoke. Server stopped.
Opus judge batch submitted (5,040 requests, one batch). Reported to the architect; nothing
scored yet, so no conclusions.

## 2026-11-10 — results, paper, PR

Judging closed at 5,039 of 5,040: 25 malformed judge replies, 24 recovered by re-asking, one
(weights arm, JLS-077, flattery, L3) malformed four times and left out, not hand-entered.
Measured cost about 72 USD (GPU 21.46 incl. smoke, judging 50.5), reported to the architect
before the analysis was run.

Result, by the locked rules: the prompted guide fades (-0.24 over 64k tokens, H1 confirmed);
it fades faster than the weights arm (difference of slopes -0.020 per level, interval excludes
zero, H3 confirmed); the weights arm is NOT flat (-0.14, interval reaches -0.22, H2 not
confirmed). On the first 12k tokens alone the difference between arms is not distinguishable
from zero. The guide still keeps two-thirds of its lift at 64k. The design cannot say why the
weights arm declines (its stated sentence fading, or long-context degradation); two further
arms would, and are listed as a suggestion only.

Paper: motivation paragraph in the introduction, new results subsection with the pooled
figure, one limitation. Written to say what was measured, including the failed hypothesis.
Open wording question for the owner at the PR gate: how to refer to the earlier unpublished
MultiBench experiments (currently "earlier unpublished experiments on MultiBench").

## 2026-11-10 — owner's decisions on PR #61; follow-up arms registered

Decisions relayed by the architect: (1) run two more arms over the same ramp, fine-tuned model
with no stated sentence and base model with no framing; (2) remove every MultiBench reference
from the paper; (3) do not say or imply the trained model solves fading; split the figure in
two: figure one the prompted arm alone, WITHOUT the no-guide floor line (floor may be stated in
text), figure two the comparison with the fine-tuned model, stated as measured; (4) per-pressure
figure stays out of the paper; the thread file stays in the commit. Paper text held until the
new arms are judged.

My 36 USD estimate for the two arms was an arithmetic error: 5,040 conversations is the size of
the first run, 69 USD measured. Told the architect and am holding all paid steps until the
corrected figure is confirmed. Follow-up registered in notes.md before its data (d528170).

## 2026-11-10 — follow-up arms done; paper rewritten

Owner narrowed the follow-up to stage 2 with no system message, then added stage 1 with no
system message; base no-framing stays on hold. Ran the two in parallel on two B200 servers.
Results: stage 2 no framing is flat over 64k (-0.03, inside the margin); stage 1 no framing
declines (-0.14); the stated sentence fades (+0.26 at no filler, +0.16 from 4k on), which
explains the first run's weights-arm decline. Level-0 checks reproduce the paper (+0.444 vs
+0.499; +0.302 vs +0.276). Experiment total about 139 USD.

Paper per the owner's decisions: no reference to any earlier experiment; two figures (prompted
arm alone with no floor line; prompted arm against the two tuned arms with no system message);
per-pressure figure kept in the experiment directory only; text says plainly that training is
not a general protection (stage 1 declines) and that everything delivered by prompt faded.
Flagged to the architect that the owner's sketch of figure two ("starts higher, declines less,
also declines") described the stated-sentence arm and does not match the no-system-message data.

## 2026-11-10 — owner's narrative direction: the combination of the two stages

Supersedes "do not say training solves it". Paper now framed around: DPO alone does not give
good answers (verified from the released reference judgments: -0.349, -0.340, -0.311 against
base -0.335), SFT alone gives answers that erode over length (stage 1), both together match the
prompted guide at the start and hold through 64k. Added the DPO-alone row to the results table
and the numbers to the existing "why not preference optimization alone" subsection (the paper
already had that subsection, without the absolute scores). Limits kept: one model, one run per
stage, one filler, DPO-alone and base-no-guide not run over the ramp, mechanism unexplained,
Inkling-Small untested. No reference to earlier experiments.
