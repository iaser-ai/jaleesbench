# air-47 — MLX stage 2 (DPO) on the model's own samples, optional tutorial section

## 2026-10-03 — implement

**Shape.** Two new commands in `jaleesweights.mlx`, same preflight / `--dry-run` shape as `sft`:
- `sample`: K chains per training cell from base + stage-1 adapter at temperature 1.3, batched
  per cell with `mlx_lm.batch_generate`; writes the collection form with a `chain` field, so
  `judge rate-samples` and `pairs` read it unchanged. `--limit N` takes N cells evenly spaced
  through the inputs (they are sorted by scenario; the first N would cover a handful of
  scenarios). Appends per cell; a re-run skips cells already written.
- `dpo`: the recipe's objective by hand (mlx_lm has no preference trainer). One model in
  memory: the reference is the stage-1 adapter, frozen, so its log-probabilities are computed
  once before the first update instead of holding a second adapter. Gradient per pair is two
  backward passes weighted by beta*sigmoid(-beta*margin), one sitting at a time. Adapter and
  log written after every optimizer step; no resume.

**Decisions and why.**
- Chains whose reply reaches `--max-tokens` (2,048) are dropped and counted, not written cut
  off: the two-pass E4B adapter sometimes does not stop (1 of 12 in the first smoke). The
  CUDA path would keep them truncated at 8,192.
- Sampling order differs from vLLM: mlx_lm filters top-p/top-k first and applies temperature
  after; vLLM applies temperature first. Goes in the differences table.
- Tests live in a new file (`tests/test_mlx_stage2.py`) so the rebase on PR #46 does not
  conflict in `test_mlx_path.py`.

**Incident (13:20 UTC).** First trainer smoke (9 hand-made pairs) pushed the Mac to ~22.7 GB
swap. Two faults: (1) MLX's buffer cache is capped by default at its memory limit, which is
larger than RAM, and every sitting has a different length, so freed multi-GB buffers piled up;
(2) my watchdog killed the `uv` wrapper, not the Python child. Fixes: `--memory-limit-gb`
(default 24) in both commands — sets MLX's limit, caps the cache at 1/8 of it, checks the peak
after every pass and stops the job past the ceiling (MLX's own limit is only a guideline: it
swaps before it raises); watchdog now kills the process tree, verifies by PID, trips at +2 GB
swap. Architect's rule since then: no model run without an estimate and an answer.

**Two numeric bugs found by the start check.**
- Log-probabilities were summed in bf16 (whole numbers). Now float32 over assistant positions.
- Reference from a plain forward pass and policy from the training pass differ by ~3 nats per
  sitting on identical weights (bf16, different evaluation path). beta*3 = 0.3 of spurious
  margin. References now go through the same pass as the policy.

**Measured so far.** Sampler: 3 cells, 11 of 12 sittings kept, 18 s per sitting, 5.8 GB peak.
Trainer: backward pass on 512 tokens 5.7 GB peak.

**Open.** Waiting for the architect's go on: re-run of the 2-pair trainer test; the 40-cell
sampling run (~50 min); then Gemini rating (cap US$5), pairs, the real stage-2 run, the third
answer. TUTORIAL.md waits for PR #46 to merge (rebase first).
