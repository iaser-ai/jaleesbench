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
