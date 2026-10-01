# Specification: JaleesWeights — commit the fine-tuning work as a runnable `jaleesweights/` folder for handoff

<!--
SPEC vs PLAN BOUNDARY:
This spec defines WHAT and WHY. The plan defines HOW and WHEN.
Keep implementation phases, file paths, code, and "first we will… then we will…"
out of the spec — those belong in codev/plans/XXXX-*.md.
-->

## Problem Statement

The JaleesWeights paper (`docs/paper/jaleesweights-paper.tex`) reports a two-stage
fine-tuning recipe that makes two open models behave as good Islamic companions with no
system prompt. The paper is in this repository. The work behind it is not: the scripts,
data, logs and run records exist only as uncommitted scratch files on one machine.

The project is being handed to a new team. Today that team could read the paper but could
not run, check or extend the recipe, because:

- the scripts are not in git;
- the data they read and wrote is not in git and is not downloadable anywhere;
- the scripts assume the original machine's folder layout, one hardcoded file path, and the
  original owner's cloud accounts;
- nothing says which of the 44 scripts are the recipe the paper reports and which belong to
  approaches that were tried and dropped.

The people affected are the new team (who must be able to run the recipe with their own
accounts), the project owner (who must be sure nothing private or secret is published, and
who approves anything that becomes public), and readers of the paper (who should be able to
check its numbers against released data).

## Current State

### What exists

One scratch folder holding 204 files, 338 MB:

| Kind | Count | Size | Notes |
|---|---|---|---|
| Python scripts | 44 | 0.2 MB | plain scripts, no package |
| Top-level `.jsonl` data | 58 | 325 MB (73 MB gzipped) | collected conversations, judgments, training sets, training logs |
| Per-run folders from Tinker training | 10 folders, 6 files each | 9 MB | settings, per-step metrics, checkpoint index, console log, timing records, and a `code.diff` |
| Console output captures (`.log`, `.out`) | 27 | 3.7 MB | progress output of collection, judging and training |
| Other | 7 + 9 cache files | small | the 70/70 split, the guide text, three notes, one account cleanup record, Python bytecode cache |

Separately, the benchmark's main run — which the training-set builders read — sits in the
benchmark's results folder and is ignored by git: conversations (281 MB), judgments
(236 MB) and citation flags (5 MB); 111 MB gzipped in total.

### What stops a new team from running it

Each item was confirmed by reading the scripts.

1. **Import path.** 15 scripts reach the benchmark package by inserting a path three folders
   above themselves into Python's search path. It only works from the scratch location.
2. **Working directory.** Scripts that read the main run disagree about where they are
   launched from: four expect to be run from inside the benchmark folder, one from the
   repository root, one computes the location from its own position.
3. **Hardcoded path.** One script reads the Tinker key from an absolute path to the original
   machine's `.env` file.
4. **Hardcoded checkpoints.** The Inkling-Small stage-2 training script starts from a
   checkpoint address in the original owner's Tinker account. A new team's stage-1 run
   produces a different address, so this must be an input, not a constant.
5. **Owner's cloud account.** The Gemma scripts use a Modal storage volume and a Modal secret
   that exist only in the original owner's Modal account, and nothing documents how to
   create them or what to upload.
6. **Too many keys demanded.** The benchmark's key loader refuses to start unless seven
   provider keys are set (Anthropic, OpenAI, Friendli, Blackbox, the Ansari route, Tinker,
   Fanar). JaleesWeights judging needs two (Anthropic and Gemini); collection from
   Inkling-Small needs one more (Tinker). A new team with only the keys it needs cannot
   judge anything.
7. **Undeclared dependencies.** `modal` is imported on the local machine but declared
   nowhere. `torch`, `transformers`, `peft`, `vllm` and `lm_eval` are used only inside the
   rented GPU machines; they are named inside the scripts but nowhere a reader would look.
   The Gemma training, sampling, collection and capability code lives inside Modal function
   bodies, so today it cannot be run on a GPU the team owns without first taking it out of
   those wrappers.
8. **Undocumented manual steps.** Copying input files to the Modal volume, copying results
   back and renaming them, and turning one training set into the trainer's file format were
   done by hand and are written down nowhere.
9. **No analysis script for half the paper's main table.** The Gemma rows have scoring
   scripts. The Inkling-Small rows were computed ad hoc; the only script that touches them
   belongs to the dose sweep.
10. **No index.** Nothing maps scripts or data files to the recipe of record or to the
    dropped approaches.

### What must not be published

- Two notes recording an exchange with another team, and that team's recipe files (the
  recipe files live outside the experiment folder).
- Comments in two scripts that name that team and its configuration file.
- Every per-run `code.diff`. They were thought to be lockfile diffs only; they also contain
  diffs of an architect state file (which must stay out of git) and, through it, the other
  team's name.
- A record of Tinker checkpoints deleted during an account cleanup. Most of the 172 entries
  are other parties' runs on a shared account.

### What already works (measured for this spec, at no cost)

- The six builder scripts, re-run against today's data in a scratch directory, reproduce
  the frozen files **byte for byte**: the training-half conversation inputs, both stage-1
  training sets (316 and 310 conversations), both stage-2 pair sets (502 and 672 pairs),
  and the Inkling-Small pairs in the trainer's format. Two further files were checked the
  same way: the held-out conversation inputs (the inputs builder does not write this file
  today; it only checks that it would produce the same rows) and the Inkling-Small stage-1
  set in the trainer's format (made by hand; re-serialising the training set gives the
  identical file). These eight files are the "rebuilt files" referred to below.
- Recomputing the paper's main results table from the existing judgment files matches
  **every point estimate to three decimals**, for both models, including the paired
  comparisons.
- The intervals on single scores are repeatable and match the paper exactly. The intervals
  on **paired** differences are not: that code iterates over a Python set, whose order
  changes from one run to the next, so its bootstrap gives interval ends that move by up to
  0.005 between runs. The paper prints two such intervals to three decimals. No choice of
  seed can recover the printed ends, because the run that produced them depended on an
  order that was never recorded.
- The benchmark package works out where the main run, the `.env` file and the Google
  service-account file are from **its own installed location**. That is right only when the
  package is used in place. Installed as a dependency of another project, those locations
  can point outside the clone.
- The guide text file used for the "with guide" condition is identical to the text the
  benchmark package produces, and identical to what the main run recorded.
- No key-shaped strings were found in any scratch file.

## Desired State

A new team member clones the repository, opens `jaleesweights/README.md`, and by following
only that file can:

1. install everything needed on their own machine with one documented command;
2. see which accounts and keys are needed, and set them up (including the Modal volume and
   secret, in their own account), or see what GPU machine they need for the local
   demonstration;
3. download the data with one documented step, and have it land where the code expects it;
4. run every step of the recipe of record, for Gemma on Modal and for Inkling-Small on
   Tinker, in the documented order, with a statement beside each paid step of what it costs
   roughly and which account it bills; and run the local demonstration of the same recipe
   on a GPU machine they own, with a statement of what hardware each step needs;
5. recompute the paper's main results table from the downloaded data without spending
   anything;
6. find the dropped approaches and the dose sweep in a clearly labelled archive, with an
   index saying what each file was for and which paper claim it supports.

Nothing they run depends on the original machine's paths, account names or untracked files.

Two kinds of data are kept apart. The **reference data** is what the download provides: the
files the original runs produced. It is read, never written. A **new run** writes
everything it produces — collected answers, judgments, training sets, training records —
to a separate location the user names, and each later step takes the earlier steps'
outputs from that location. Free steps can be pointed at either.

### The recipe of record

The paper is the arbiter. The recipe of record is what the paper's Method section
describes and what its main results table reports:

- **Gemma-4-31B**, the full-precision (bf16) chain: stage 1 (filtered context
  distillation, supervised fine-tuning), stage 2 (preference optimization on the stage-1
  model's own samples, with the stage-1 model as reference), the held-out evaluation of each
  stage against a base-model control served through the same stack, the "with guide"
  evaluation of stage 1, and the capability panel. The runs of record were made on Modal
  and the pipeline stays on Modal, exactly as run.
- **Inkling-Small**, through the Tinker API: the same two stages and evaluations, with
  stage 2 at the settings of record (learning rate 1e-5, one epoch).
- The 70/70 split, the Gemini-selects / Opus-scores separation, and the paired per-cell
  comparisons.

**A third path, added by the owner on 2026-09-30: a local demonstration.** Its purpose is to
show how to train locally — the same two-stage recipe running end to end on a GPU machine a
team plausibly owns, with the Hugging Face stack (`transformers`, `peft`, vLLM) that the
Modal functions already run inside, and no Modal image, volume, secret or account. It does
not have to match the Modal path: it may use a smaller model from the Gemma family, and its
precision and batch settings may differ. It keeps the recipe — two stages, the same
training-set builders, the same pairing rules, the same Gemini-selects / Opus-scores
protocol, the same split. It is a demonstration, not a paper result: the README says its
numbers are not the paper's and are not expected to match them. Which model and which
hardware it targets is open question 9, with a default.

One consequence shapes its data flow. The paper's Gemma path takes its stage-1 teacher
answers from the benchmark's main run, where Gemma-4-31B is a subject. A smaller Gemma model
is not in the main run, so the demonstration must first collect its own base-model answers
— the training half with the guide, the held-out half bare and with the guide — exactly as
the Inkling-Small path does. Its run order therefore mirrors Inkling-Small's, executed on
local hardware instead of through Tinker.

Everything else the paper mentions is supporting evidence, not the recipe: the five
preference-optimization attempts on base models, the earlier 4-bit Gemma chain (reported
as "an independent end-to-end rerun"), and the seven-arm Inkling-Small dose sweep. Those go
to the archive.

### Run order the README must document

Paid steps are marked with the account that is billed. "Free" means it runs on the local
machine using downloaded data.

**Gemma-4-31B**

| # | Step | Cost |
|---|---|---|
| 1 | Build the conversation inputs for the training half and the held-out half | free |
| 2 | Build the stage-1 training set: Gemma's own guided answers that Gemini rated good before and after pushback, screened for guide references and dangling citations (316 conversations) | free |
| 3 | Upload inputs and the training set to the Modal volume | free |
| 4 | Stage-1 training (LoRA rank 32, lr 5e-5, 2 epochs) | Modal, one B200 |
| 5 | Collect held-out answers: base model with no adapter (the control), stage 1 bare, stage 1 with guide | Modal, one H200 |
| 6 | Opus scores those answers | Anthropic |
| 7 | Sample four answers per training scenario from the stage-1 model at temperature 1.3 | Modal, one H200 |
| 8 | Gemini rates the 1,680 samples | Gemini |
| 9 | Build stage-2 pairs from the rated samples (502 pairs) | free |
| 10 | Stage-2 training (β 0.1, lr 1e-5, 1 epoch; stage 1 as reference) | Modal, one B200 |
| 11 | Collect held-out answers from the stage-2 model, bare | Modal, one H200 |
| 12 | Opus scores them | Anthropic |
| 13 | Scores with intervals, and the paired stage-2-versus-stage-1 comparison | free |
| 14 | Capability panel (MMLU, GSM8K, IFEval) on base, stage 1, stage 2 | Modal, one H200 |

**Inkling-Small**

| # | Step | Cost |
|---|---|---|
| 1 | Collect base-model answers: training half with guide; held-out half bare and with guide | Tinker |
| 2 | Gemini rates the guided training-half answers | Gemini |
| 3 | Build the stage-1 training set (310 conversations) and write it in the trainer's format | free |
| 4 | Stage-1 training | Tinker |
| 5 | Collect held-out answers from the stage-1 checkpoint, bare and with guide | Tinker |
| 6 | Opus scores base and stage-1 held-out answers | Anthropic |
| 7 | Sample four answers per training scenario from the stage-1 checkpoint | Tinker |
| 8 | Gemini rates the 1,680 samples | Gemini |
| 9 | Build stage-2 pairs (672) and write them in the trainer's format | free |
| 10 | Stage-2 training, starting from the stage-1 checkpoint | Tinker |
| 11 | Collect held-out answers from the stage-2 checkpoint, bare; Opus scores them | Tinker, Anthropic |
| 12 | Scores with intervals, and the paired comparisons (stage 1 versus base, stage 2 versus stage 1) | free |

Steps copying files to and from Modal, which were manual, become documented steps.

**Local demonstration (Gemma family, the team's own GPU machine)**

Mirrors the Inkling-Small order. Every GPU step is a plain local command; there is nothing
to upload or download. "Own GPU" means the machine in the hardware section below.

| # | Step | Cost |
|---|---|---|
| 1 | Collect base-model answers: training half with guide; held-out half bare and with guide | own GPU (vLLM) |
| 2 | Gemini rates the guided training-half answers, both scopes | Gemini |
| 3 | Build the stage-1 training set with the same filters and screens | free |
| 4 | Stage-1 training (LoRA, same objective; batch and precision per the hardware section) | own GPU |
| 5 | Collect held-out answers from the stage-1 adapter, bare and with guide | own GPU (vLLM) |
| 6 | Opus scores base and stage-1 held-out answers | Anthropic |
| 7 | Sample four answers per training scenario from the stage-1 adapter at temperature 1.3 | own GPU (vLLM) |
| 8 | Gemini rates the samples | Gemini |
| 9 | Build stage-2 pairs with the same pairing rule | free |
| 10 | Stage-2 training (β 0.1, lr 1e-5, 1 epoch; stage 1 as reference) | own GPU |
| 11 | Collect held-out answers from the stage-2 adapter, bare; Opus scores them | own GPU, Anthropic |
| 12 | Scores with intervals and paired comparisons (stage 1 versus base, stage 2 versus stage 1) | free |

The judge costs are the same as the other paths' (about 840 Opus judgments per held-out
condition; 1,680 Gemini ratings for the samples). The capability panel is not part of the
demonstration unless the owner asks for it.

### Hardware for the local demonstration

The README must carry this information, and must label each figure as **measured** (taken
from the run records of the 31B runs) or **derived** (worked out from the settings in the
scripts and the model's size). Nothing here was measured on a non-Modal machine; this
workspace has no NVIDIA GPU (see approach 5A). The figures below are the source for the
README and for open question 9.

**Measured, from the runs of record**

| Step | Hardware used | What the records say |
|---|---|---|
| Stage-1 training, bf16 | one B200 (Modal) | 79 optimizer steps; peak GPU memory 66.0 GB (training log); about 15 minutes |
| Stage-2 training, bf16 | one B200 (Modal) | 63 optimizer steps; peak memory not in the local records (the earlier 4-bit version peaked at 33 GB on an H200 with a 4-bit base, which does not transfer) |
| Held-out collection and sampling | one H200 (Modal), vLLM | 420 two-turn conversations in about 6 minutes; 1,680 sampled conversations in one pass |
| Capability panel | one H200 (Modal), vLLM through lm-eval | ran within a five-hour limit per checkpoint |

**Derived, from the scripts' settings and the model sizes**

- In bf16 a model needs two bytes per parameter of GPU memory for its weights before
  anything else. LoRA rank 32 on the attention and MLP projections; one conversation per
  forward pass, batch of 8 by gradient accumulation; conversations up to 16,384 tokens (the
  scripts refuse longer ones); gradient checkpointing on. With those settings the 31B
  training run peaked at 66 GB against 62 GB of weights, so training overhead is small and
  memory is dominated by the weights. Stage 2 holds two LoRA adapters (policy and
  reference) over one copy of the weights, so its footprint is close to stage 1's.
- Serving through vLLM as the scripts set it — bf16 weights, LoRA at rank 32, a
  32,768-token context window, 92% of GPU memory allocated — needs the weights plus room
  for the key-value cache; the smaller the leftover, the smaller the context window or the
  fewer concurrent conversations the README must tell the team to set. Results do not
  change; throughput does.
- The Gemma-4 family on Hugging Face (all ungated, checked 2026-09-30): E2B and E4B (small,
  "effective" sizes with a different internal layout), 12B (dense), 26B-A4B (mixture of
  experts, 26B total), and 31B (dense, the paper's model). Applying the derivation:

  | Candidate | bf16 weights | Training fits on | Serving as set fits on | What it gives up |
  |---|---|---|---|---|
  | 31B (the paper's) | ~62 GB | one 80 GB GPU, thin headroom (measured 66 GB) | 141 GB+; on 80 GB only with a reduced context window | nothing in the recipe; the hardware is the barrier |
  | 12B, dense | ~24 GB | one 48 GB or 80 GB GPU with room to spare; a 32 GB card is marginal | 80 GB comfortably; 48 GB with a reduced window | a smaller model's guided answers set a lower ceiling for stage 1 to distil; same architecture family as 31B, so the same LoRA targets and code apply with the model name changed |
  | E4B | ~8 GB | one 24 GB consumer GPU | 24 GB | weakest starting point; different internal layout, so LoRA targets and vLLM support must be checked before it is promised |
  | 26B-A4B | ~52 GB | one 80 GB GPU | 80 GB tight | mixture-of-experts layout: LoRA over experts is a different problem and was never tried here; not recommended for a demonstration |
- **Software.** Linux with an NVIDIA driver supporting CUDA 12.8 (required by the Blackwell
  B200; Hopper and Ampere cards work with the same stack), Python 3.12, `torch` 2.7 or later
  built for CUDA 12.8, `transformers` 4.53+, `peft` 0.15+, `accelerate` 1.3+, vLLM 0.10+
  (which needs the full CUDA toolkit present, because it compiles Gemma-4 kernels at
  start-up). These are the versions the Modal images pin; the README states them as the
  envelope the Modal runs used, untested locally.
- **Disk.** The model weights in the Hugging Face cache (two bytes per parameter), plus
  adapters (a few hundred MB each). No Hugging Face token is needed: the family was ungated
  when the runs were made and still is.

### Classification of every existing file

Three classes. **Final pipeline**: part of the recipe of record; ported so it runs from a
fresh clone. **Archive**: committed or released as it was, labelled not maintained.
**Left out**: neither committed nor put in a release archive; the originals stay untouched
on the original machine.

File names are the scratch-folder names. Where a name would itself reveal private
material, the file is described instead of named.

#### Scripts (44)

The five Modal drivers of the recipe of record stay in the final pipeline. The local
demonstration is new code, ported from their function bodies and from the Inkling-Small
collection driver; it is not an existing file and so does not appear in this
classification.

**Final pipeline (24)**

| Script | Role |
|---|---|
| `build_train_inputs.py` | conversation inputs for both halves of the split |
| `judge_train_samples.py` | Gemini rating of sampled answers (both models) |
| `export_comparisons.py` | pairs → the Tinker trainer's format |
| `score_eval.py` | scores with bootstrap intervals |
| `build_sft_guided.py` | Gemma stage-1 training set |
| `modal_gemma_sft_bf16.py` | Gemma stage-1 training |
| `modal_gemma_eval.py` | Gemma held-out collection (base control, tuned, with guide) |
| `modal_gemma_sample.py` | Gemma sampling for stage 2 |
| `judge_eval_basevllm.py`, `judge_eval_bf16.py`, `judge_eval_sftdpo_bf16.py` | Opus scoring of Gemma held-out answers |
| `build_sftbf16_pairs.py` | Gemma stage-2 pairs |
| `modal_gemma_dpo2_bf16.py` | Gemma stage-2 training |
| `paired_sftdpo_bf16.py` | Gemma paired comparison |
| `modal_gemma_capability.py` | capability panel |
| `collect_small.py` | every Inkling-Small collection and sampling pass |
| `judge_small_selection.py` | Gemini rating of Inkling-Small guided answers |
| `build_sft_small.py` | Inkling-Small stage-1 training set |
| `train_sft_small.py` | Inkling-Small stage-1 training |
| `judge_small_baselines.py`, `judge_small_sft.py`, `judge_small_sftdpo.py` | Opus scoring of Inkling-Small held-out answers |
| `build_small_sft2_pairs.py` | Inkling-Small stage-2 pairs |
| `train_dpo_small_sft2.py` | Inkling-Small stage-2 training |

**Archive (19)**

| Script | Belongs to |
|---|---|
| `build_pairs.py`, `train_dpo_run.py`, `train_dpo_run2.py`, `collect_eval.py`, `judge_eval.py` | first preference-optimization rounds on base Inkling (pairs from other models' answers; 254 and 1,200 pairs) |
| `modal_gemma_dpo.py` | preference optimization on base Gemma (used by three arms) |
| `analyze_shifts.py` | per-cell analysis of the first Gemma arms |
| `build_onpolicy_pairs.py`, `judge_eval_onpol.py` | pairs from base Gemma's own samples (also the source of the paper's "317 of 420 cells" figure) |
| `build_maxgap_pairs.py`, `judge_eval_maxgap.py` | pooled pairs from existing Gemma answers |
| `modal_gemma_sft.py`, `modal_gemma_dpo2.py`, `build_sft2_pairs.py`, `judge_eval_sft.py`, `judge_eval_sftG.py`, `judge_eval_sftdpo.py` | the earlier 4-bit Gemma chain (the paper's "independent rerun") |
| `train_dpo_small_sft2_sweep.py`, `paired_small_sweep.py` | the Inkling-Small dose sweep |

Two archive scripts have comments naming the other team and its configuration file. Those
comments are reworded; every setting stays. That is the only edit made to archive scripts.
They are not repaired: their import paths and launch instructions still describe the
scratch location, and the archive's index says so.

**Left out (1)**

| Script | Why |
|---|---|
| a sibling project's copy of the stage-1 training script | differs from our own bf16 stage-1 script only in names and docstring (9 lines); not ours to publish; the architect said to draft with it left out, owner confirms at the gate |

#### Data

**Final pipeline — reference data for the recipe of record**

| Files | What |
|---|---|
| `split_70_70.json` | the split of record (seed 3446). Small; committed to git |
| `guided_prefix.txt` | the guide text as sent to the models. Identical to what the benchmark package produces |
| `eval_inputs_gemma.jsonl`, `train_inputs_gemma.jsonl` | conversation inputs, held-out and training halves (used for both models despite the name) |
| `sft_train_guided.jsonl` | Gemma stage-1 training set (316) |
| `collect_eval_basevllm.jsonl`, `collect_eval_bf16.jsonl`, `collect_eval_bf16_guided.jsonl`, `collect_eval_sftdpo_bf16.jsonl` | Gemma held-out answers: control, stage 1 bare, stage 1 with guide, stage 2 |
| `collect_sftbf16_samples.jsonl`, `judgments_sftbf16_samples.jsonl` | Gemma stage-1 samples and their Gemini ratings |
| `pairs_train70_sftbf16.jsonl` | Gemma stage-2 pairs (502) |
| `judgments_eval_gemma.jsonl` | Opus scores for all Gemma held-out answers. One file holding ten subjects: four of record, six from archived arms. Kept whole |
| `train_log_bf16sft.jsonl` | Gemma stage-1 training log |
| `collect_small_train_guided.jsonl`, `judgments_small_selection.jsonl` | Inkling-Small guided training-half answers and their Gemini ratings |
| `sft_train_small.jsonl`, `sft_train_small_messages.jsonl` | Inkling-Small stage-1 training set (310), and the same in the trainer's format |
| `collect_small_test_unstated.jsonl`, `collect_small_test_guided.jsonl`, `collect_small_test_unstated_sft.jsonl`, `collect_small_test_guided_sft.jsonl`, `collect_small_test_unstated_sftdpo.jsonl` | Inkling-Small held-out answers: base, stage 1, stage 2 |
| `collect_small_train_unstated_sft_k4.jsonl`, `judgments_small_sft_k4.jsonl` | Inkling-Small stage-1 samples and their Gemini ratings |
| `pairs_train70_small_sft2.jsonl`, `comparisons_train_small_sft2.jsonl` | Inkling-Small stage-2 pairs (672), and the same in the trainer's format |
| `judgments_eval_small.jsonl` | Opus scores for all Inkling-Small held-out answers. One file holding nine subjects: three of record, six from the sweep. Kept whole |
| `sft_small_run/`, `dpo_small_sft2_run/` — settings and per-step metrics only | records of the two Inkling-Small training runs of record. Owner's decision at the plan gate (2026-10-01): the settings file's three path fields are rewritten to release-relative names; the checkpoint index is left out (addresses in the owner's Tinker account) |
| the benchmark main run: conversations, judgments, citation flags | read by the builders and by scoring; distributed as its own download |

**Archive**

| Files | Belongs to |
|---|---|
| `pairs_train70.jsonl`, `pairs_train70_expanded4.jsonl`, `comparisons_train.jsonl`, `comparisons_train_expanded4.jsonl`, `collect_eval.jsonl`, `judgments_eval.jsonl`, `run1/`, `run2/` | first rounds on base Inkling |
| `pairs_train70_gemma-4-31b.jsonl`, `pairs_train70_gemma-4-31b_expanded4.jsonl`, `collect_eval_gemma.jsonl` | first round on base Gemma (the expanded set was built but never trained on) |
| `collect_train_samples.jsonl`, `judgments_train_samples.jsonl`, `pairs_train70_gemma_onpol.jsonl`, `pairs_train70_gemma_onpol_all.jsonl`, `collect_eval_onpol.jsonl`, `train_log_onpol.jsonl` | pairs from base Gemma's own samples |
| `pairs_train70_gemma_maxgap.jsonl`, `collect_eval_maxgap.jsonl`, `train_log_maxgap.jsonl` | pooled pairs |
| `collect_eval_sft.jsonl`, `collect_eval_sftG.jsonl`, `collect_sft2_samples.jsonl`, `judgments_sft2_samples.jsonl`, `pairs_train70_sft2.jsonl`, `collect_eval_sftdpo.jsonl`, `train_log_sft.jsonl`, `train_log_sftdpo.jsonl` | the earlier 4-bit Gemma chain |
| six `collect_small_test_unstated_sftdpo_lr*.jsonl`, six `dpo_small_sft2_sweep_*/` folders | the dose sweep |

From every archived run folder, the same two files are kept as from the runs of record:
settings (path fields rewritten) and per-step metrics. The checkpoint index is left out.

**Left out**

| Files | Why |
|---|---|
| two notes recording the exchange with the other team | owner's decision 3 |
| a methodology note written for a sibling project | repeats the paper and the experiment issue; quotes the 4-bit numbers the paper has replaced; contains original-machine paths; architect said to draft with it left out, owner confirms at the gate |
| the Tinker cleanup record | lists other parties' runs on a shared account; no experimental content |
| ten `code.diff` files | contain diffs of an architect state file and the other team's name; no experimental content |
| ten `checkpoints.jsonl` | checkpoint addresses in the owner's Tinker account; useless to anyone else (owner, 2026-10-01) |
| ten `logs.log`, ten `timing_spans.jsonl`, 27 `.log` / `.out` console captures | console output only. They carry original-machine paths and session identifiers; nothing in the paper is computed from them; the per-step metrics that the paper does cite are kept separately |
| Python bytecode cache | generated |

## Success Criteria

- [ ] `jaleesweights/` exists at the top level of the repository with a README, the final
      pipeline, and an archive folder.
- [ ] Every one of the 44 scripts and every data file in the scratch folder is in the place
      its class above says, and nothing classed "left out" is in git or in a release archive.
- [ ] From a fresh clone in an empty directory, with none of the original machine's files
      present, following only the README: installation succeeds with one documented command.
- [ ] From that same clone, the data download step places the reference data and the
      benchmark main run where the code expects them, checks each archive against a
      checksum recorded in git, and stops with a clear message if a checksum does not match
      or the release is not yet public.
- [ ] From that same clone, every free step of both run-order tables runs, and the eight
      rebuilt files are byte-identical to the downloaded reference copies:
      `train_inputs_gemma.jsonl`, `eval_inputs_gemma.jsonl`, `sft_train_guided.jsonl`,
      `pairs_train70_sftbf16.jsonl`, `sft_train_small.jsonl`,
      `sft_train_small_messages.jsonl`, `pairs_train70_small_sft2.jsonl`,
      `comparisons_train_small_sft2.jsonl`. The README names the step that produces each.
- [ ] From that same clone, the scoring step reproduces the paper's main results table:
      every score, every paired difference and every single-score interval exactly as
      printed (three decimals, or two where the paper prints two). The two paired-difference
      intervals land within 0.01 of the printed ends.
- [ ] The scoring step gives the same output on every run. The README states its
      paired-interval values and that they differ slightly from the two printed in the
      paper, and why.
- [ ] Every paid step that runs through Modal, Tinker or a judge API can be started from
      that same clone and gets as far as it can without spending: it finds its inputs, and either reports that the reference data already
      covers all the work (collection and judging steps) or stops before launch naming what
      it is about to rent (training steps). A missing key or account produces a message that
      names it.
- [ ] The local demonstration runs the two-stage recipe end to end on one GPU machine with
      no Modal image, volume, secret or account: the same training-set builders, pairing
      rule, judge protocol and split as the paths of record; model, precision and batch
      settings as settings, defaulting to the owner's answer to open question 9.
- [ ] The local demonstration's GPU code, which cannot be executed in this workspace, is
      shown to be the Modal function bodies taken out of their wrapper: the diff is reviewed
      in the pull request and any change beyond the wrapper (model name, precision, batch,
      context window) is listed; the scripts compile and print their usage on a machine
      without a GPU; and the README names the first cheap smoke test a team with a GPU
      should run.
- [ ] The README says the demonstration's numbers are not the paper's and are not expected
      to match them.
- [ ] A JaleesWeights step asks only for the keys it uses. Judging with only an Anthropic
      key and a Gemini credential set works; nothing demands OpenAI, Friendli, Blackbox,
      Ansari-route or Fanar keys.
- [ ] No step reads a path outside the clone, and no step depends on which directory it is
      launched from beyond what the README states. Where the main run, the reference data
      and the key file are is settled by the clone's layout or by an explicit input, never
      by where a package happens to be installed.
- [ ] No checkpoint address, storage volume or secret from the original owner's accounts is
      required. Where a later step needs the output of an earlier paid step (a checkpoint, an
      adapter), it takes it as an input.
- [ ] Reference data is never written to. Every collection, judging, training-set and
      training step can write to a new-run location the user names, and every later step can
      read an earlier step's output from there.
- [ ] The README states: the accounts and keys needed; how to create the Modal volume and
      secret; the run order for both models; the rough cost and billed account of each paid
      step; which steps are free; that trained weights are not included; and how the
      capability panel's numbers relate to the paper's.
- [ ] The README's hardware section for the local demonstration gives, for each GPU step,
      the hardware the 31B run of record used and the minimum the chosen model needs, with
      every figure labelled measured or derived, and says that the demonstration was not
      executed before handoff.
- [ ] The archive has an index naming, for every archived script and data file, the approach
      it belonged to and the paper claim it supports, and states that the archive is not
      maintained and its scripts do not run from their new location.
- [ ] Dependencies are declared: what runs on the local machine in the project's dependency
      file with a committed lock file; the GPU stack (`torch`, `transformers`, `peft`,
      `accelerate`, vLLM) as a separately installable set that the local demonstration
      needs and the default install does not pull in, since it cannot be installed on a
      machine without an NVIDIA GPU; and the Modal images declare the same versions. The
      README says which is which.
- [ ] A search finds no key, no content of any `.env` file, no mention of the other team or
      its configuration file, and none of the left-out files in: every file this work adds
      or changes, **every commit this work adds to the branch**, and every release archive.
      The two comment lines already in tracked code (open question 3) are outside this
      check unless the owner asks for them to be reworded.
- [ ] A report for the owner, kept outside git, lists all 204 scratch files by name with the
      class each was given and where it ended up, together with the search result. It
      accompanies the request to publish.
- [ ] Nothing is publicly downloadable until the owner has approved it. No release, draft or
      public, is created without that approval.
- [ ] No paid Modal, Tinker or judging step is run during this work without the owner's
      approval.
- [ ] Existing benchmark tests still pass, and the new code has tests that run offline with
      no keys and no downloaded data.
- [ ] `codev/state/*` stays out of git except this builder's thread file. The spec, plan and
      review are committed.

## Constraints

### Decisions already made (by the project owner) — copied verbatim from the issue, fixed

1. **Location.** The work lives in this repo, in a new top-level `jaleesweights/` folder. No separate repo.
2. **Large data.** Large data files are distributed as a release download, not committed to git history. This covers both the experiment's own data (about 310 MB raw) and the benchmark main-run data that the training-pair builders read (about 500 MB raw), which is also not in git today.
3. **Material from a private upstream config.** Some training settings were taken from another team's private configuration. Keep the settings in the scripts, because they are needed to reproduce the runs. Leave out the exchange notes, leave out the upstream recipe files, and reword code comments so they do not name that team or its config.
4. **Scope.** The final pipeline — the recipe of record that the paper reports — must be runnable end to end, with a README and a documented run order. The abandoned arms and the dose sweep are committed as-is in an archive folder, clearly labelled as not maintained.
5. **Process.** SPIR protocol. The codev artifacts for this work (spec, plan, review) are committed with it.

### Other constraints

- The repository is public. A published release cannot be reliably withdrawn.
- Re-running any paid GPU or API step for verification needs the owner's approval first.
- The main checkout and the scratch folder are read-only for this work: copy from them,
  never move, edit or delete.
- Repository conventions: Python through `uv`; command-line entry points use Typer; no
  wrapper or runner scripts; fail fast with a clear error and no fallbacks; `git add` by
  explicit path.
- The training arithmetic, filters, pairing rules, sampling settings and hyperparameters of
  the final pipeline must not change. Porting changes only what portability requires, with
  one named exception: the paired-comparison bootstrap is made repeatable (see Current
  State). Point estimates are unaffected.
- Gemma's GPU steps of record run on Modal; Inkling-Small's run through Tinker; the local
  demonstration runs on a GPU machine the team owns. None of them runs on the machine this
  work is done on: it is a Mac with no NVIDIA GPU, so the demonstration can be reviewed here
  but not executed.

### Security and privacy

The rules that apply to anything leaving the machine, gathered in one place:

- Private wording is removed **before the first commit**. No commit on the branch, at any
  point in its history, contains the other team's name, its configuration file name, or a
  left-out file. Checking only the final tree is not enough, because the repository is
  public and history is published with it.
- Nothing is sent anywhere — no release, draft or public — before the owner has seen the
  contents list and the search result and has approved.
- No keys are committed or archived. Key files stay ignored by git. Steps read keys from
  the environment or from the clone's own `.env`, and name a missing key without printing
  any key's value.
- Identifiers from the original accounts (Tinker checkpoint addresses in the run records,
  Modal run names) are not credentials and are useless without the owning account's key.
  They remain in the released run records as part of the record.
- The release would make public the full text of judgments and the raw provider responses
  for thirteen benchmark subjects. Whether and on what terms that may be published is the
  owner's decision (open question 7).

### Scope item for review at the gate: keys

The benchmark package's key loader currently demands seven provider keys before any
judging starts. This work changes that behaviour so that a JaleesWeights step asks only for
the keys it uses. It is the one place this work touches behaviour the benchmark package
owns, and it is listed here so it is approved explicitly. The benchmark's own commands
must behave as they do today.

## Assumptions

- "Recipe only, no weights": trained adapters and checkpoints are not distributed by this
  work. (Owner's open question; see below.)
- The judge models the paper used (`claude-opus-4-8`, `gemini-3.1-pro-preview`) and the
  base models (`google/gemma-4-31B-it`, `thinkingmachines/Inkling-Small`) are still served.
  This cannot be checked without spending.
- A new team may use the public Gemini API with a Gemini key. The original runs used Google
  Vertex with a service-account file; the benchmark package already accepts either.
- The benchmark main run as it stands today is the right one to release. The builders
  reproduce the frozen training sets from it byte for byte, so nothing the recipe depends on
  has drifted.
- The benchmark's conversations are already public in another form through the results
  browser in this repository, so releasing the main run does not newly expose them. The
  judgments' full text and the raw provider responses would be newly public.
- "The team's own GPU machine" means one Linux machine with one NVIDIA GPU and a CUDA
  12.8-capable driver; its size follows from the model the owner chooses (open question 9).
  Running over several GPUs is not promised.
- Costs in the README come from the experiment record of August 2026 and are stated as
  rough. Where no figure was recorded, the README says so instead of guessing.

## Solution Approaches

Four questions were left open for the spec. Each is answered separately.

### 1. Packaging, and how it depends on the benchmark package

#### Approach 1A (recommended): its own `uv` project that declares the benchmark as a local dependency

`jaleesweights/` becomes a third `uv` project beside `jaleesbench/` and `quranquote/`,
with its own dependency file and lock file. It declares the benchmark package as a
dependency by local path, so the import works from any directory and the path hack
disappears. It declares `modal` for the local machine and the GPU stack as a separately
installable set for the local demonstration. Steps are launched as modules through `uv`.

- For: matches how the repository is already laid out; one install command; the 15 import
  hacks and the working-directory disagreements go away together; the lock file pins the
  Tinker trainer version the runs used.
- Against: two lock files that can drift; a change to the benchmark package can break
  JaleesWeights without the benchmark's own tests noticing.
- Hazard: the benchmark package locates the main run and the key files from its own
  installed position (see Current State). Depending on how the dependency is installed,
  that position may be inside the new project's environment rather than the clone.
  JaleesWeights therefore must not rely on the benchmark's idea of where things are: it is
  told, or works out from the clone's layout, where the main run and the key file live.
- Risk: low once that is handled.

#### Approach 1B: a sub-package inside the benchmark package

- For: one project, one lock file, no cross-project dependency.
- Against: the owner decided on a top-level `jaleesweights/` folder; it would also load the
  benchmark's install with `modal` and fine-tuning concerns. Ruled out by decision 1.

#### Approach 1C: keep loose scripts, correct the inserted path

- For: smallest diff from what ran.
- Against: the dependency stays undeclared, the working-directory sensitivity stays, and
  there is no single install command. Does not meet "dependencies are declared".

#### How far the port goes

Two ways to port the 24 final-pipeline scripts:

- **Minimal port (recommended).** Each script keeps its logic. Changes are limited to
  imports, paths, key handling, account names as inputs, and a Typer entry point. The seven
  near-identical judging scripts (six Opus, one Gemini) differ only in file names and may become one step
  taking the file names as inputs. The as-run originals are committed first and the port is
  made in later commits, so the history shows exactly what changed from what produced the
  paper's numbers. "As-run" here means after the private wording has been reworded: three
  scripts are affected (two archive scripts, and one docstring line in the Gemma stage-1
  script), the change is to comments only, and it is made before anything is committed.
- **Rewrite into a designed package.** Cleaner result, but the GPU stages cannot be re-run
  for free, so a rewrite of the training code could not be shown to be equivalent.

The minimal port is recommended because equivalence is the thing a handoff most needs, and
for the GPU code a small reviewable diff is the only free evidence available.

### 2. How the data download works, and how the release is staged before approval

The owner decided on a release download. Open: which host, and how to keep it private until
approved.

#### Approach 2A (recommended): a GitHub release on this repository, built locally first

Archives and a checksum list are built on the local machine in a location git ignores. The
checksum list is committed. The secret-and-private-material search runs over the archives.
The owner is shown the archive contents list and the search result, and approves. Only then
is a release created — as a draft, which the public cannot see — and the owner publishes it
or approves publishing. The download step can also install from archive files already on
disk, which is how a fresh clone is checked before anything is public.

Two archives: the JaleesWeights data (final and archive parts, about 73 MB compressed) and
the benchmark main run (about 111 MB compressed).

- For: same place as the code; no new account; a draft is invisible to the public; nothing
  leaves the machine before the owner has seen what would be sent.
- Against: until the release is public, the README's download command cannot work for an
  outsider. The step must say so plainly when that happens.
- Risk: low. Creating even a draft is an action on the owner's repository and is treated as
  needing approval.

#### Approach 2B: a Hugging Face dataset repository, private until approved

- For: fits the open request to host the benchmark there (issue #22); better for browsing.
- Against: a new account, token and tool for the new team; and it decides issue #22 by the
  back door. Better taken up under #22.

#### Approach 2C: hand the archives to the owner to upload

- For: the builder never touches a release.
- Against: the download step cannot be finished or checked until an upload happens out of
  band.

### 3. Layout of the archive folder

#### Approach 3A (recommended): one flat folder of scripts, with an index

The 19 scripts sit together as they did in the scratch folder. An index table lists each
script and each archived data file, the approach it belonged to, and the paper claim it
supports. Archived data is a separate part of the data download.

- For: closest to "as-is"; several scripts served more than one approach (one training
  script served three), so grouping by approach would force a choice or a copy.
- Against: a reader must use the index to see the groups.

#### Approach 3B: one sub-folder per approach

- For: the grouping is visible in the folder tree.
- Against: shared scripts must be duplicated or placed arbitrarily, and the scripts refer to
  each other's outputs by flat names.

### 4. Logs and per-run folders

#### Approach 4A (recommended): keep the structured records, leave out console output

From each of the ten run folders keep the settings, the per-step metrics and the checkpoint
index — the paper cites training accuracy and margins that come from the metrics. Keep the
five Modal training logs. Leave out every `code.diff`, every console log and the timing
records. The kept files go in the data download, not in git.

- For: keeps everything a number in the paper was computed from; drops files that carry
  original-machine paths, session identifiers and unrelated repository diffs.
- Against: the console logs record why four judgments are missing from two files (a judge
  call failed three times and was left). The archive index will state that in one line instead.

#### Approach 4B: keep everything except `code.diff`

- For: nothing is lost.
- Against: 8 MB of console output carrying home-directory paths, for no reproducible value.

### 5. Showing a fresh clone works without spending

#### Approach 5A (recommended): three free checks, and a priced list of optional paid ones

1. **Fresh-clone walk-through.** Clone into an empty directory, with no keys and none of the
   original machine's files reachable. Follow the README: install, install the data from the
   staged archives, run every free step. The rebuilt training files must equal the reference
   copies byte for byte, and the scoring step must reproduce the paper's table.
2. **Paid steps, up to the point of spending.** Collection and judging steps skip work that
   is already recorded, so pointed at the complete reference data they find nothing to do
   and make no billable call — which exercises their whole path to that point. Training
   steps are shown to find their inputs and state what they would rent, without launching.
3. **The diff.** For the GPU training code, the diff between the as-run original and the
   ported file is small and is reviewed in the pull request.

Paid smoke runs (for example a four-example Modal training run, which the scripts already
support) are listed with their rough cost. The owner chooses whether any are run.

- For: costs nothing; covers every step that can be covered for free; says plainly what
  remains unproven.
- Against, and stated in the README as not re-tested:
  - setting up a fresh Modal account — creating the volume and the secret, uploading the
    inputs, building the GPU images. These are the first things a new team does, and none
    can be exercised for free or from the owner's account without approval;
  - anything that fails only after launch: a GPU type no longer offered, a model or judge
    no longer served;
  - a genuine new run from start to finish. The free checks show each step starts, finds
    its inputs and writes to a new-run location; they do not show a checkpoint produced by
    one paid step being consumed by the next.

#### Approach 5B: re-run the whole recipe once

- For: the only complete proof.
- Against: about $100 for Gemma plus the Inkling-Small cost, and judge variation means the
  numbers would not match exactly anyway. Not proposed; available if the owner wants it.

### 6. The local demonstration: which model, which hardware, and how it relates to the Modal code

The owner asks for the model size and target hardware to be proposed, with the reasoning,
as a question — not picked silently. The candidates and the arithmetic are in the hardware
section above.

#### Approach 6A (recommended default): Gemma-4-12B, one 80 GB GPU, runnable on 48 GB

- For: the same dense layout as the paper's 31B, so the training code, LoRA targets and
  vLLM settings carry over with the model name changed and nothing else to re-derive; bf16
  is kept, so no quantization confound enters; 24 GB of weights leaves an 80 GB card with
  ample room for the serving settings as written, and a 48 GB card works with a smaller
  context window; a 12B instruction-tuned model is a credible companion to begin with, so
  stage 1 has something to distil.
- Against: not hardware every team owns; the numbers will sit below the paper's (a smaller
  guided ceiling).
- Risk: low.

#### Approach 6B: Gemma-4-E4B, one 24 GB consumer GPU

- For: the widest reach — a single consumer card.
- Against: the weakest starting model; its internal layout differs from the dense models,
  so LoRA targets and vLLM support must be checked before it can be promised; the guided
  ceiling may be too low for stage 1 to have much to teach, which would make the
  demonstration show little.
- Risk: medium.

#### Approach 6C: Gemma-4-31B, one 80 GB GPU

- For: the paper's own model, so the demonstration is as close to the paths of record as
  hardware allows; the main-run teacher data could be reused instead of collected.
- Against: 66 GB measured peak for training leaves thin headroom on 80 GB; serving needs a
  reduced context window; slowest and most expensive to run.
- Risk: medium (memory).

#### How the demonstration relates to the Modal code

The GPU steps are the Modal function bodies taken out of their wrappers and given local
paths, with the model name, precision, batch size and context window as settings. The
collection step gains what the Inkling-Small driver has and the Modal one lacks: a choice
of input half (training or held-out) and the guide as an option, since the demonstration
collects its own teacher answers. The plan decides whether the extracted functions are also
what the Modal drivers call (one copy) or whether the Modal drivers stay untouched (two
copies); the owner has dropped the requirement that the two never drift, so either is
acceptable, and the pull request's diff shows what differs.

**What can be checked here and what cannot.** This workspace has no NVIDIA GPU. The
demonstration is reviewed as a diff, compiled, and its usage printed; the tokenisation and
loss-mask code, which needs only the tokenizer, can be run on a CPU. Nothing else about it
is executed before handoff, and the README says so. The first thing a team with a GPU
should run is stage-1 training limited to four examples (the scripts already support the
limit): it loads the model, builds the adapter, runs the parity check and writes an adapter
in a few minutes. After that, held-out collection limited to a handful of conversations
with that adapter exercises vLLM plus LoRA. Both are named in the README as the smoke
tests.

## Open Questions

### Critical (blocks progress)

None. The work can proceed on the defaults below.

### Important (shapes design) — for the owner

1. **Weights.** Does the new team need the trained weights, or only the recipe? Default:
   recipe only. For information: the Inkling-Small checkpoints were saved with a seven-day
   expiry in August and are very likely gone; the Gemma adapters should still be on the
   owner's Modal volume.
2. **Capability results.** The paper's capability table has no raw results among the scratch
   files; they exist only on the owner's Modal volume. Should they be fetched and added to
   the data download? Default: no; the README says that table cannot be recomputed from the
   released data, and how to re-run the panel.
3. **An existing mention of the other team in tracked code.** Two comment lines in the
   benchmark's collection module name that team. They predate this work. Should they be
   reworded in this pull request? Default: not touched.
4. **The experiment issue.** The public experiment issue (#21) names the other team in
   several comments. It is the owner's to edit. Should the new README link to it as the
   experiment history? Default: the README does not link it until the owner says so.
5. **The two sibling-project files** (a methodology note and a copy of the stage-1 script).
   Default, as the architect directed: both left out, and the one docstring line in our own
   stage-1 script that says where it came from is reworded to name no other project. Owner
   confirms.
6. **Console logs.** Left out under approach 4A. Confirm, or say to keep them in the archive
   download.
7. **Terms for the released data.** The repository has no licence file. The release contains
   model outputs from several providers (Anthropic, OpenAI, Google, Fanar and others), the
   judges' full text, and training sets built from them, offered so others can re-run a
   fine-tuning recipe. Whether that may be redistributed, and under what stated terms, is
   for the owner to decide before publication. This work does not resolve it; the request
   to publish will ask for it. Default: nothing is published until the owner has answered.
8. **The paper's two paired intervals.** Once the scoring step is repeatable, its
   paired-difference intervals will differ from the two printed in the paper by up to
   0.005 (one run made for this spec gave an end of +0.211 where the paper prints
   +0.206). Should the paper be corrected to the repeatable values, or left as printed
   with a note in the README? Default: the paper is not touched by this work; the README
   carries the note.
9. **Model and hardware for the local demonstration** (new). Which Gemma-family model, and
   what machine does it target? Default: **Gemma-4-12B in bf16 on one 80 GB GPU, also
   runnable on a 48 GB card with a smaller serving context window** (approach 6A). Reasoning:
   it is the same dense layout as the paper's 31B, so the code and LoRA targets carry over
   unchanged; 24 GB of weights fits comfortably; bf16 avoids a quantization confound; and a
   12B instruction-tuned model gives stage 1 a real guided ceiling to distil. What it gives
   up: the numbers will be lower than the paper's and are not meant to match. The
   alternatives are E4B on a 24 GB consumer card (widest reach, weakest model, support to be
   checked) and the paper's 31B on 80 GB (thin memory headroom). Running over several GPUs
   is not promised for any choice.

Questions 1–8 stand at their defaults by the owner's decision of 2026-09-30; question 9 is
new.

### Nice-to-know

10. The capability script has a raw-completion mode and a chat mode. The paper's figures
   (MMLU 0.828) look like the chat-mode run; the experiment issue's earlier figures
   (MMLU 0.467) are the raw mode. The README will document chat mode as the paper's. Correct
   this if wrong.
11. Whether `gemini-3.1-pro-preview` is reachable with a plain Gemini key, as opposed to
   Vertex, has not been tested. It costs a call to find out.

## Test Scenarios

### Functional

1. **Fresh clone, free path.** Empty directory, no keys, no access to the original machine's
   files. Install; install data from local archives; run all free steps for both models.
   Expected: the eight rebuilt files byte-identical to the reference copies; counts 316, 310,
   502, 672; scoring output equals the paper's main table within the stated tolerance.
2. **Scoring is repeatable.** Run the scoring step twice. Expected: identical output.
3. **Checksum failure.** Corrupt one archive. Expected: the download step stops and names
   the archive.
4. **Release not yet public.** Run the download step before publication with no local
   archives. Expected: it stops with a message saying the data release is not published.
5. **Missing key.** Run a judging step with no Anthropic key. Expected: it stops and names
   that key, and names no key the step does not use.
6. **Only the needed keys.** Set only an Anthropic key and a Gemini key (placeholder values)
   and run the Opus and Gemini judging steps against the complete reference data. Expected:
   each reports nothing left to do and makes no billable call.
7. **Any working directory.** Run one builder and the scoring step from the repository root
   and from inside `jaleesweights/`. Expected: same result.
8. **Reference data is not overwritten.** Run a builder. Expected: reference files unchanged
   (same checksums); new output is somewhere else.
8a. **A new run chains.** In an empty new-run location holding only small made-up inputs,
   run a training-set builder and then the step that consumes its output. Expected: the
   second step reads the first step's output from the new-run location, not from the
   reference data.
8b. **Installed elsewhere.** With the benchmark package installed into the JaleesWeights
   environment, run a builder and the scoring step. Expected: they read the main run from
   the clone, not from inside the environment.
9. **Stage-2 needs a stage-1 checkpoint.** Start Inkling-Small stage-2 training without
   giving a checkpoint. Expected: it stops and asks for one; it does not fall back to the
   original account's address.
10. **Benchmark unchanged.** The benchmark's existing test suite passes, and its own commands
    still require the keys they required before.

### Non-functional

11. **Nothing private.** Search every file this work adds or changes, every commit this work
    adds to the branch, and both archives for: key-shaped strings; the other team's name and
    configuration file name; the names of the left-out files; architect state content.
    Expected: no hits. (The two existing comment lines of open question 3 are not part of
    this work and are excluded unless the owner asks otherwise.)
12. **Nothing large in git.** No file added to git by this work is larger than 1 MB.
13. **Archive is labelled.** The archive index exists, covers all 19 scripts and every
    archived data file, and says the archive is not maintained.
14. **Offline tests.** The new tests pass with no network, no keys and no downloaded data.

### Local demonstration (no GPU here)

15. **Compiles and explains itself.** On this Mac, every demonstration step compiles and
    prints its usage; a missing GPU dependency is reported by name.
16. **Same recipe.** The diff between each as-run Modal function body and the demonstration
    code is reviewed in the pull request; every difference beyond the wrapper (model name,
    precision, batch, context window, the input-half and guide options) is listed, and the
    filters, pairing rule and judge protocol are the shared ones.
17. **Loss mask on a CPU.** With only the tokenizer, the conversation rendering and
    assistant-token mask code produces a prefix-stable rendering and masks exactly the
    assistant turns on a made-up conversation. (Needs network access to fetch the tokenizer;
    skipped offline.)
18. **First smoke test for a team with a GPU** (documented, not run here): stage-1 training
    limited to four examples, then held-out collection limited to a handful of
    conversations with the resulting adapter.

### Paid, optional, only with the owner's approval

19. A four-example Modal smoke run of Gemma stage-1 training (the script supports it).
20. One Opus judgment and one Gemini judgment through a plain key, to confirm the judge
    models are still served.

## Risks and Mitigation

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Private material or a key is published in a public, non-withdrawable release | Low | High | Search the changed files, the branch's commits and the built archives before anything is sent; owner sees the contents list and search result; release is created only after approval and as a draft first |
| Private wording reaches git history through an early commit even though the final tree is clean | Medium | High | Reword before the first commit; the search covers every commit on the branch, and runs before the branch is pushed |
| Released data is published without redistribution terms being settled | Medium | Medium | Raised as open question 7; publication waits for the owner's answer |
| The repeatable scoring step's paired intervals differ from the paper's printed ones and a reader takes it for an error | High | Low | README states the values and the reason; owner decides whether the paper is corrected (open question 8) |
| The port changes training behaviour without anyone noticing, since GPU stages are not re-run | Medium | High | Minimal port; as-run originals committed first so the diff is reviewable; builders proven byte-identical; optional paid smoke run offered to the owner |
| The local demonstration is handed over never having been executed on a GPU | High | Medium | Code is the Modal function bodies with paths and settings changed; compile, usage and CPU-only mask checks; README states plainly that it was not run and names the four-example smoke test to run first |
| The chosen demonstration model does not fit the target card, or a smaller model's guided ceiling is too low for stage 1 to show anything | Medium | Medium | Hardware figures labelled measured or derived, with the 31B measurements as the anchor; the owner chooses the model with the trade-offs stated (open question 9); README says which serving settings to reduce |
| A reader takes the demonstration's numbers for the paper's | Medium | Low | README states they are not and are not expected to match |
| A paid step fails only after launch (GPU image no longer builds, GPU type unavailable, model or judge no longer served) | Medium | Medium | README states the versions and GPU types the runs used and that this was not re-tested; optional paid checks listed with costs |
| Judge models are retired, so a new team's scores are not comparable with the paper's | Medium | Medium | README states the exact judge models; the released judgments let the paper's table be recomputed regardless |
| The key-loader change alters the benchmark's own behaviour | Low | Medium | Listed as an explicit scope item; benchmark commands must behave as before; existing tests must pass |
| Releasing the main run exposes something beyond what the results browser already shows (full judge text, raw provider responses) | Low | Medium | Stated in Assumptions for the owner to weigh; covered by the same search; owner approves the contents |
| Two `uv` projects drift apart | Low | Low | Lock file committed; an offline test imports the benchmark functions the pipeline uses |
| The README's download command fails for outsiders between merge and publication | Medium | Low | The step says plainly that the release is not yet published; publication is requested with the pull request |
| Dropping console logs loses the reason a few judgments are missing | Low | Low | The archive index states it |

## References

- Issue #36 — this work. Issue #21 — the experiment record. Issue #22 — request to host the
  benchmark on Hugging Face.
- `docs/paper/jaleesweights-paper.tex` — the arbiter of the recipe of record.
  `docs/paper/jaleesweights-outline.md` — earlier outline; its Gemma figures are the 4-bit
  chain's and have been superseded by the paper.
- `jaleesbench/README.md` — the benchmark harness, its keys and its commands.
- Askell et al. (context distillation), Rafailov et al. (DPO), Hu et al. (LoRA) — as cited
  in the paper.
