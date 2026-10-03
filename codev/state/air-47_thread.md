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

## 2026-10-03 — the real run (architect's Mac, M5 Pro 64 GB, E4B 4-bit, two-pass stage-1 adapter)

| Step | Result | Time | Peak memory | Swap delta |
|---|---|---|---|---|
| Sample 40 cells x 4 | 145 sittings kept, 15 dropped at the 2,048-token cap; 40 scenarios | 50 min | 5.8 GB | fell 1.7 GB |
| Gemini ratings | 145; 541,217 tokens in, 264,563 out; bands -2:119, -1:11, +1:5, +2:10 | 3 min | — | — |
| Pairs | 36 pairs from 13 of 40 cells; 27 cells without a 2-band spread; chosen bands +2:25, +1:11 | — | — | — |
| Stage-2 training | 5 steps, batch 8, beta 0.1, lr 1e-5 | 7.5 min | 18.6 GB | -8 MB |

Rating cost: about US$4.26 if Gemini 3.1 Pro is $2/$12 per million tokens — a price I assumed,
not one the code records. The README's own figure (1,680 ratings, ~$20) would put 145 at ~$1.70.

Training log: loss 0.693, 0.480, 0.110, 0.113, 0.571; preference accuracy 0, 0.625, 0.875,
0.875, 0.75; mean margin 0, 36, 129, 183, 197 nats. The margins are roughly ten times the
paper's log (its losses imply tens of nats). Likely cause: mlx_lm's LoRA scale of 20 (the
stage-1 MLX setting) makes each 1e-5 AdamW step a larger change to the function than the
CUDA path's adapter scale. Not tuned; reported as is.

Memory: the trainer's peak is the backward pass through the model, about 4.8 GB per 1,000
tokens of sitting. Chunking the float32 vocabulary head saved only 2 GB (17.7 -> 15.7 GB on a
2,431-token sitting).

Third answer (bank question, greedy): differs from stage 1. It drops the unattributed "the
Prophet taught..." line and it also drops the mention of interest (riba); the full 908-token
answer never raises it. The tutorial says so plainly and claims no improvement.

Differences from the CUDA stage 2 (`local/gemma_dpo.py`, `local/gemma_collect.py`), for the PR
body since the tutorial no longer carries a differences table:
- reference log-probabilities computed once before training from the same adapter, not a
  second adapter held in memory;
- no selective-head parity check (the model's logits are used whole); no resume;
- chains that reach the token cap are dropped, not kept truncated;
- mlx_lm filters top-p/top-k before applying temperature; vLLM applies temperature first;
- LoRA rank 8, scale 20, top 16 layers (the MLX stage-1 adapter), 4-bit base.

Flaky test skipped: `test_local_demo.py::test_collect_preflight_names_pass_and_output` — its
last assertion depends on where Typer wraps an error box, which depends on the temp path length.

Size: about 560 added lines with tests, over AIR's 300.
