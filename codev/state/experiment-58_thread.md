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
