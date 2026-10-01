# Archive — not maintained

The scripts in this folder are the approaches that were tried and dropped on the way to the
recipe of record, the earlier 4-bit (QLoRA) Gemma chain, and the Inkling-Small dose sweep.
They are committed **exactly as they ran** in August 2026 (one exception: comments in two
scripts that named a third party were reworded; no setting changed). They are **not
maintained** and **do not run from here**: their imports reach the benchmark package by a
relative path that only existed in the original scratch folder, their "Run:" lines name that
folder, and several read the main run from a working-directory-relative `results/`. Read them
for what was done; use `../jaleesweights/` to run anything.

Their data files are in the reference data download (`jaleesweights/data/reference/`),
alongside the data of record; the index below names them. The paper (`docs/paper/
jaleesweights-paper.tex`) reports these arms as supporting evidence, not as the recipe.

## First preference-optimization rounds on base Inkling

Pairs built from the benchmark main run: the chosen side is another model's answer, the
rejected side Inkling's own where it qualified. Both arms flat. Paper: "Why not preference
optimization alone" — two of the five flat arms.

| File | What |
|---|---|
| `build_pairs.py` | pair builder over the main run (one pair per cell, or expanded with `EXPANDED_PER_CELL`; `TARGET_SUBJECT` picks the on-policy side) |
| `train_dpo_run.py`, `train_dpo_run2.py` | Tinker DPO on 254 and 1,200 pairs (`comparisons_train.jsonl`, `comparisons_train_expanded4.jsonl`) |
| `collect_eval.py` | held-out collection from the two tuned checkpoints through the benchmark harness |
| `judge_eval.py` | Opus scoring of those collections |
| data | `pairs_train70.jsonl`, `pairs_train70_expanded4.jsonl`, `comparisons_train.jsonl`, `comparisons_train_expanded4.jsonl`, `collect_eval.jsonl`, `judgments_eval.jsonl`, `tinker-runs/run1/`, `tinker-runs/run2/` |

## First preference-optimization round on base Gemma

The same construction aimed at Gemma, trained on Modal with a 4-bit base. Flat. Paper: the
third flat arm. The expanded Gemma pair set (1,570 pairs) was built but never trained on.

| File | What |
|---|---|
| `modal_gemma_dpo.py` | Modal DPO trainer (4-bit base, LoRA rank 32); also used by the two arms below |
| `analyze_shifts.py` | per-cell comparison of the first Gemma arms against base |
| data | `pairs_train70_gemma-4-31b.jsonl`, `pairs_train70_gemma-4-31b_expanded4.jsonl`, `collect_eval_gemma.jsonl`, and the `gemma-dpo-r1` rows of `judgments_eval_gemma.jsonl` |

## Pairs from base Gemma's own samples

Four answers per training cell sampled from the base model at temperature 1.3, rated by
Gemini, paired within the cell. Flat. Paper: the fourth flat arm, and the source of the
"317 of 420 cells produced no good draw" figure (the script prints it as `no-chosen`).

| File | What |
|---|---|
| `build_onpolicy_pairs.py` | within-cell pairs from the sampled answers (`EXPANDED=1` for all combinations) |
| `judge_eval_onpol.py` | Opus scoring of the arm's held-out collection |
| data | `collect_train_samples.jsonl`, `judgments_train_samples.jsonl`, `pairs_train70_gemma_onpol.jsonl`, `pairs_train70_gemma_onpol_all.jsonl`, `collect_eval_onpol.jsonl`, `train_log_onpol.jsonl`, the `gemma-dpo-onpol` rows of `judgments_eval_gemma.jsonl` |

The base-model sampling itself used the Modal sampler that is now
`jaleesweights/modal/gemma_sample.py` with `--adapter-run ""`.

## Pooled "max-gap" pairs

Every existing Gemma answer for a training cell — the main-run answer plus the four samples
— anchored to its most-differently-rated counterpart in both directions. Flat. Paper: the
fifth flat arm.

| File | What |
|---|---|
| `build_maxgap_pairs.py` | the pooled pair builder |
| `judge_eval_maxgap.py` | Opus scoring of the arm's held-out collection |
| data | `pairs_train70_gemma_maxgap.jsonl`, `collect_eval_maxgap.jsonl`, `train_log_maxgap.jsonl`, the `gemma-dpo-maxgap` rows of `judgments_eval_gemma.jsonl` |

## The earlier 4-bit Gemma chain

The two-stage recipe as first run: a 4-bit (nf4) base with LoRA on an H200. Superseded by
the bf16 chain of record; the paper reports it as "an independent end-to-end rerun of the
Gemma pipeline" that reproduced the stage-2 gain (+0.220).

| File | What |
|---|---|
| `modal_gemma_sft.py` | stage-1 trainer, 4-bit base |
| `modal_gemma_dpo2.py` | stage-2 trainer, two adapters over a 4-bit base |
| `build_sft2_pairs.py` | stage-2 pairs from this chain's stage-1 samples (518 pairs) |
| `judge_eval_sft.py`, `judge_eval_sftG.py`, `judge_eval_sftdpo.py` | Opus scoring of stage 1 bare, stage 1 with guide, stage 2 |
| data | `collect_eval_sft.jsonl`, `collect_eval_sftG.jsonl`, `collect_sft2_samples.jsonl`, `judgments_sft2_samples.jsonl`, `pairs_train70_sft2.jsonl`, `collect_eval_sftdpo.jsonl`, `train_log_sft.jsonl`, `train_log_sftdpo.jsonl`, the `gemma-sft-guided`, `gemma-sft-guided-G` and `gemma-sft-dpo` rows of `judgments_eval_gemma.jsonl` |

## The Inkling-Small dose sweep

Stage 2 re-run at six more learning-rate / epoch settings (the run of record is lr 1e-5,
one epoch). Every arm lands within ±0.025 of stage 1. Paper: "we re-ran stage 2 as a
seven-arm dose sweep".

| File | What |
|---|---|
| `train_dpo_small_sft2_sweep.py` | the stage-2 trainer with `--lr` and `--epochs` (Typer) |
| `paired_small_sweep.py` | scores and paired comparisons of all seven arms against stage 1, plus training fit from each run's `metrics.jsonl` |
| data | six `collect_small_test_unstated_sftdpo_lr*.jsonl`, six `tinker-runs/dpo_small_sft2_sweep_*/`, and the `inkling-small-sftdpo-lr*` rows of `judgments_eval_small.jsonl` |

## Notes on the data

- Two judgment files are shared with the data of record and were left whole:
  `judgments_eval_gemma.jsonl` (ten subjects) and `judgments_eval_small.jsonl` (nine).
- A few judgments are missing because a judge call failed three times and was left:
  `gemma-sft-guided` has 839 of 840 rows, and three sweep arms (`inkling-small-sftdpo-lr3e-5`,
  `-lr3e-4`, `-lr3e-5-ep3`) have 839 each. The scoring handles the gaps.
- Each Tinker run folder holds `config.json` (the three path fields rewritten to
  release-relative names; everything else as written) and `metrics.jsonl`. The checkpoint
  index was left out: it held addresses in the original Tinker account.
- The Modal training logs of this archive's arms (`train_log_*.jsonl`) are per-step records
  copied from the volume at the time.
