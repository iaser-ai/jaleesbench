# air-41 thread — jaleesweights local demo, 24 GB profile (issue #41)

## 2026-10-02 implement

- Read the local demo (`jaleesweights/local/`), the archived 4-bit chain (`archive/modal_gemma_sft.py`,
  `modal_gemma_dpo2.py`) and the README. Baseline: 86 tests pass offline.
- Reused the archived chain's quantization verbatim: `BitsAndBytesConfig(load_in_4bit, nf4, bf16 compute)`
  and `prepare_model_for_kbit_training(use_gradient_checkpointing, use_reentrant=False)`. Under
  `--load-in-4bit` that call replaces the manual `gradient_checkpointing_enable` + `enable_input_require_grads`
  pair (it does both, plus the fp32 casts the archived chain ran with). bf16 path untouched.
- Serving: vLLM `quantization="bitsandbytes"` (in-flight nf4) behind the same flag; window and
  utilization defaults kept. Stated in code and README that 4-bit serving changes the sampled text
  (results), unlike the window/utilization knobs (throughput only). Records carry `@nf4` in `model`.
- Preflight: a `precision:` line with a derived estimate. Weights = nominal params x bytes/param;
  training peak scaled from the measured 31B peaks (bf16 66 GB over 62 GB; nf4 33 GB over 15.5 GB).
  12B: bf16 ~24 / ~26 GB; nf4 ~6 / ~13 GB. Unknown model id -> "no estimate", never a guess.
- `bitsandbytes>=0.45; linux` added to the `gpu` group; `uv lock` resolved it (0.50.2). Default group unchanged.
- Fail fast: the 4-bit path requires bitsandbytes before anything else, so the message names it
  even on a machine with the rest of the GPU stack missing. Verified: exit 1, "missing GPU dependency: bitsandbytes".
- Surprise: the issue cites the paper for "+0.088 (paired) bf16 over 4-bit at 31B". The .tex in
  `docs/paper/jaleesweights-paper.tex` does not contain that number (it reports the rerun's +0.220
  stage-2 gain). Used the issue's figure in the README; flagged in the PR for the architect to confirm.
- GPU path not executed here (no NVIDIA GPU). First smoke test for a 24 GB team is the stage-1
  `--limit 4 --load-in-4bit` command in the README's "Run this first".

## 2026-10-02 PR #42 and the 3-way review

- PR #42 opened. CMAP: gemini APPROVE; codex and claude REQUEST_CHANGES. Verified each point at the source:
  - vLLM in-flight bitsandbytes (locked 0.26): the loader hard-codes `quantize_4bit(..., quant_type="nf4")`
    and the 4-bit matmul runs in bf16, so "nf4, bf16 compute" is accurate; the fp4/float32 defaults codex
    cited are the config class's labels, unused on this path. Recorded in a docstring.
  - vLLM 0.28 (the lock's choice for Python 3.14) moved bitsandbytes to `vllm-bnb-plugin`. Added it to the
    gpu group for >=3.14 and a run-time check in gemma_collect that names it (tested with a fake find_spec).
  - +0.088: not in the paper text, but reproducible from the data release with `score --extra-paired`:
    stage 1 bf16 vs 4-bit +0.088 [+0.008,+0.176], stage 2 +0.090 [+0.017,+0.164] (n=420). README now cites
    the data release and the command, not the paper. Fetched the release (free) to compute it.
  - fp16 now gets the bf16 training-peak estimate (same bytes per parameter).
- Not changed: the nf4 weights estimate ignores the unquantized embeddings (labelled derived; the 31B
  calibration absorbs most of it). Parity-check risk in the PR body softened: check and tolerance are
  the archive's, which passed at 31B.
