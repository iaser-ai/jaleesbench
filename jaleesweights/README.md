# JaleesWeights

The two-stage fine-tuning recipe behind `docs/paper/jaleesweights-paper.tex` — filtered
context distillation, then preference optimization on the tuned model's own samples —
packaged so a team can run it from a fresh clone with their own accounts.

Three paths:

1. **Gemma-4-31B on Modal** — the paper's Gemma result, exactly as run.
2. **Inkling-Small through the Tinker API** — the paper's second model, exactly as run.
3. **A local demonstration** — the same recipe on a smaller Gemma-family model on one GPU
   you own. Its numbers are not the paper's and are not expected to match them.

Everything that costs nothing — the training-set builders, the pair builder, the scoring
step — runs on a laptop against the released data and reproduces the paper's main results
table. Everything that costs money prints what it is about to do and which account it bills
before it starts, and stops there with `--dry-run`.

Contents: [What you need](#what-you-need) · [Install](#install) · [Get the data](#get-the-data) ·
[Reproduce the paper's table for free](#reproduce-the-papers-table-for-free) ·
[Run orders](#run-orders) ([Gemma on Modal](#gemma-4-31b-on-modal) · [Inkling-Small on Tinker](#inkling-small-on-tinker) ·
[Local demonstration](#local-demonstration-a-gemma-family-model-on-your-own-gpu)) · [Costs](#costs) ·
[What was and was not verified before handoff](#what-was-and-was-not-verified-before-handoff) ·
[Weights, judges, versions](#weights-judges-versions) · [The archive](#the-archive) · [Licence](#licence)

## What you need

| Account / key | Needed for | How the code finds it |
|---|---|---|
| **Anthropic** (`ANTHROPIC_API_KEY`) | Claude Opus, the held-out judge, scores every evaluation | repo-root `.env` or the environment |
| **Gemini** — `GEMINI_API_KEY`, or a Vertex service-account file at `<repo>/.vertex-sa.json` | Gemini, the selection judge, rates training candidates | same |
| **Tinker** (`TINKER_API_KEY`) | Inkling-Small training, sampling and collection | same |
| **Modal** (`modal token new`) | the Gemma path of record: one B200 for training, one H200 for serving | Modal's own config |
| **Hugging Face** | nothing: the Gemma weights are ungated. The Modal drivers reference a secret named `huggingface` that must exist; its token may be empty | Modal secret |
| **A Linux machine with one NVIDIA GPU** | the local demonstration only (see its hardware section) | — |

Each command asks only for the keys it uses and names a missing one; no key is ever printed.
Put keys in a `.env` at the repository root (`KEY=value`, one per line; JaleesWeights strips
surrounding quotes, the benchmark's own commands do not) or export them.

The runs of record used the Gemini judge through Vertex. The Vertex file is found because the
benchmark package is installed editable from this clone (see below); with a plain
`GEMINI_API_KEY` nothing else is needed.

## Install

```bash
git clone https://github.com/iaser-ai/jaleesbench.git
cd jaleesbench/jaleesweights
uv sync                      # Python >= 3.12; installs the benchmark harness editable from ../jaleesbench
uv run pytest -q             # offline tests, no keys, no data
```

Every command below is run from `jaleesweights/` as `uv run python -m jaleesweights.<step>`;
`--help` on any of them lists its options. `uv run` works from any directory with
`--directory jaleesweights`.

Dependencies: the local machine's are in `pyproject.toml` and locked in `uv.lock` (`modal`,
`typer`, the Tinker SDK and cookbook pinned to the versions the runs used, and the benchmark
package). `torch` and `transformers` are already in that default install because the Tinker
cookbook depends on them. The GPU stack for the local demonstration — `peft`, `accelerate`,
vLLM, plus the same two — is the `gpu` dependency group, installable only on Linux with an
NVIDIA GPU:

```bash
uv sync --group gpu          # on the GPU machine
```

The Modal container images pin the same versions (`jaleesweights/modal/_config.py`).

## Get the data

Two archives, released on this repository as `jaleesweights-data-v1`, checksummed in
`release/checksums.sha256` and listed member by member in `release/CONTENTS.md`:

| Archive | Holds | Lands in |
|---|---|---|
| `jaleesweights-data.tar.gz` (74 MB) | everything the original runs produced: collected answers, judgments, training sets, pairs, sampled answers, Tinker run records — for the recipe of record and for the archived arms | `jaleesweights/data/reference/` |
| `jaleesbench-main-run.tar.gz` (111 MB) | the benchmark's main run — the conversations, judgments and citation flags the training-set builders read, plus the benchmark's own `judgments_v2.jsonl` overlay | `jaleesbench/results/` |

```bash
uv run python -m jaleesweights.fetch_data                     # download, verify, extract
uv run python -m jaleesweights.fetch_data --from-dir ~/dl     # the same from archives already on disk
```

The step verifies each archive's checksum before extracting and refuses to overwrite files
already there (`--force` to replace). If the release has not been published yet, it says so;
until then `--from-dir` is the way in.

The reference data is **read-only** for every command here: outputs go to a run directory,
`data/runs/<name>/` (`--run <name>`, default `new-run`), and a command asked to write into the
reference data refuses. The data is released under CC BY 4.0 with a `NOTICE` (in both
archives and below) that the model outputs it contains remain subject to their providers'
terms.

## Reproduce the paper's table for free

With the data installed, these commands read only the released files and spend nothing:

```bash
R=data/reference
uv run python -m jaleesweights.inputs --run check
uv run python -m jaleesweights.sft_guided --run check
uv run python -m jaleesweights.pairs --run check --samples $R/collect_sftbf16_samples.jsonl \
    --judgments $R/judgments_sftbf16_samples.jsonl --out-name pairs_train70_sftbf16.jsonl
uv run python -m jaleesweights.sft_small --run check --collect $R/collect_small_train_guided.jsonl \
    --judgments $R/judgments_small_selection.jsonl
uv run python -m jaleesweights.pairs --run check --samples $R/collect_small_train_unstated_sft_k4.jsonl \
    --judgments $R/judgments_small_sft_k4.jsonl --out-name pairs_train70_small_sft2.jsonl
uv run python -m jaleesweights.comparisons --src data/runs/check/pairs_train70_small_sft2.jsonl
uv run python -m jaleesweights.score
```

The eight files these commands write are byte-identical to the released copies:

| Rebuilt file | Command | What it is |
|---|---|---|
| `train_inputs_gemma.jsonl`, `eval_inputs_gemma.jsonl` | `inputs` | the conversation openings and pressure turns, training half and held-out half (model-independent despite the name) |
| `sft_train_guided.jsonl` (316) | `sft_guided` | Gemma stage-1 training set, from the main run |
| `pairs_train70_sftbf16.jsonl` (502) | `pairs` | Gemma stage-2 pairs |
| `sft_train_small.jsonl`, `sft_train_small_messages.jsonl` (310) | `sft_small` | Inkling-Small stage-1 training set and its trainer-format copy |
| `pairs_train70_small_sft2.jsonl` (672) | `pairs` | Inkling-Small stage-2 pairs |
| `comparisons_train_small_sft2.jsonl` | `comparisons` | the same pairs in the Tinker trainer's format |

`score` prints the paper's main results table — every score, drop and interval as printed —
and the paired per-cell comparisons. Two notes:

- The two **paired** intervals the paper prints (Gemma stage 2 vs stage 1, `[+0.144, +0.304]`;
  Inkling-Small stage 1 vs base, `[+0.206, +0.392]`) came from code whose bootstrap order was
  not repeatable. This step is repeatable and gives `[+0.144, +0.306]` and `[+0.210, +0.389]`;
  the point estimates and cell counts are identical. The paper is unchanged.
- `score` reads the benchmark's base `judgments.jsonl`, as the original scoring did; the
  benchmark's own tools overlay `judgments_v2.jsonl` (282 re-judged cells), so a benchmark
  number for the two main-run rows can differ from this table by a few thousandths.
- The table prints every cell; the paper leaves some first-response and drop cells blank.

`uv run pytest -q` includes a test that checks this table against the paper once the data is
installed (it is skipped before).

## Run orders

Conventions for every paid step: it prints a **preflight** — inputs and their row counts, the
model, the settings, which account is billed — and stops there with `--dry-run`; it is
**resume-safe** (judging and collection skip work already in the output file, so a complete
output means nothing is spent); it writes to the run directory and never into the reference
data; and where a later step needs an earlier step's output (a checkpoint, an adapter), it
takes it as an option — nothing points at the original accounts.

### Gemma-4-31B on Modal

The path of record. Hardware used: one **B200** (180 GB) for training, one **H200** (141 GB) for
vLLM serving, both rented through Modal.

**Once, in your Modal account.** Create the volume and the secret the drivers expect (other
names: set `JW_MODAL_VOLUME` and `JW_MODAL_HF_SECRET` in your environment):

```bash
modal volume create gemma-dpo
modal secret create huggingface HF_TOKEN=            # the weights are ungated; the secret must exist
```

Files move to and from the volume by hand. Every driver prints the exact `modal volume put`
and `modal volume get` lines for its inputs and outputs in its preflight, which runs without
an account:

```bash
uv run python -m jaleesweights.modal.gemma_sft_bf16 --data /pairs/sft_guided.jsonl --run-name gemma-sft-guided-bf16
```

(`modal run ... --dry-run` prints the same, but `modal run` needs a token first.) A real launch
also takes the local file each volume input was uploaded from (`--local-data`,
`--local-pairs`, `--local-inputs`, `--local-context`) and checks it before renting anything.

| Local file | Volume path | Used by |
|---|---|---|
| `data/runs/<run>/sft_train_guided.jsonl` | `/pairs/sft_guided.jsonl` | stage-1 training |
| `data/runs/<run>/eval_inputs_gemma.jsonl` | `/pairs/eval_inputs.jsonl` | held-out collection |
| `data/runs/<run>/train_inputs_gemma.jsonl` | `/pairs/train_inputs.jsonl` | sampling |
| `guided_prefix.txt` | `/pairs/guided_prefix.txt` | the with-guide collection |
| `data/runs/<run>/pairs_train70_sftbf16.jsonl` | `/pairs/pairs_sftbf16.jsonl` | stage-2 training |

The steps, in order (M = `uv run modal run --detach -m jaleesweights.modal.`; costs in
[Costs](#costs)):

| # | Step | Command | Bills |
|---|---|---|---|
| 1 | Conversation inputs, both halves | `uv run python -m jaleesweights.inputs --run <run>` | free |
| 2 | Stage-1 training set (316) | `uv run python -m jaleesweights.sft_guided --run <run>` | free |
| 3 | Upload inputs and training set | `modal volume put ...` (lines from the preflights) | free |
| 4 | Stage-1 training: LoRA rank 32, lr 5e-5, 2 epochs, batch 8, bf16 | `M gemma_sft_bf16 --data /pairs/sft_guided.jsonl --run-name gemma-sft-guided-bf16 --local-data <file>` | Modal, B200 |
| 5 | Held-out collection ×3: base model control, stage 1 bare, stage 1 with guide | `M gemma_eval --run-name base --subject gemma-base-vllm --local-inputs <file>`; `M gemma_eval --run-name gemma-sft-guided-bf16 --local-inputs <file>`; `M gemma_eval --run-name gemma-sft-guided-bf16 --subject gemma-sft-guided-bf16-G --context-file /pairs/guided_prefix.txt --local-inputs <file> --local-context guided_prefix.txt` | Modal, H200 |
| 6 | Download the three collections, then Opus scores them | `modal volume get ...`; `uv run python -m jaleesweights.judge opus --run <run> --collect <each file>` | Anthropic |
| 7 | Sample 4 answers per training cell from stage 1 at temperature 1.3 | `M gemma_sample --local-inputs <file>` (defaults are the recipe) | Modal, H200 |
| 8 | Download the samples, then Gemini rates them | `uv run python -m jaleesweights.judge rate-samples --run <run> --collect <samples>` | Gemini |
| 9 | Stage-2 pairs | `uv run python -m jaleesweights.pairs --run <run> --samples <samples> --judgments <ratings> --out-name pairs_train70_sftbf16.jsonl` | free |
| 10 | Upload the pairs; stage-2 training: β 0.1, lr 1e-5, 1 epoch, stage 1 as reference | `M gemma_dpo2_bf16 --pairs /pairs/pairs_sftbf16.jsonl --sft-run gemma-sft-guided-bf16 --run-name gemma-sft-dpo-bf16 --local-pairs <file>` | Modal, B200 |
| 11 | Held-out collection from stage 2, bare | `M gemma_eval --run-name gemma-sft-dpo-bf16 --local-inputs <file>` | Modal, H200 |
| 12 | Download; Opus scores it | `judge opus` as in 6 | Anthropic |
| 13 | Scores and paired comparisons | `uv run python -m jaleesweights.score --gemma data/runs/<run>/judgments_eval.jsonl` | free |
| 14 | Capability panel (MMLU, GSM8K, IFEval) on base, stage 1, stage 2 | `M gemma_capability --chat` | Modal, H200 |

Smoke test before the real runs: step 4 with `--limit 4 --run-name smoke` (a few minutes on
the B200: loads the model, builds the adapter, runs the start-up parity check, writes an
adapter).

`--chat` is the mode the paper's capability table used (chat template applied, few-shot as
multi-turn). Without it the panel runs raw completions — the mode of the earlier panels,
whose absolutes are far lower. The raw lm-eval result files of the paper's panel are not in
the data release; they exist only on the original Modal volume.

### Inkling-Small on Tinker

The second model of record, trained and sampled through Tinker (Thinking Machines'
fine-tuning API). Export `TINKER_API_KEY` or put it in `.env`. The trainers record every
checkpoint they write in `<log dir>/checkpoints.jsonl`; the final `state_path` is the stage-1
checkpoint address stage 2 takes, and the `sampler_path` is what the collection step takes
as `--model`.

| # | Step | Command | Bills |
|---|---|---|---|
| 1 | Collect base-model answers: training half with guide; held-out half bare and with guide | `uv run python -m jaleesweights.collect_small train-guided --run <run>`; `... test-unstated --run <run>`; `... test-guided --run <run>` | Tinker |
| 2 | Gemini rates the guided training-half answers, both scopes | `uv run python -m jaleesweights.judge gemini-select --run <run> --collect data/runs/<run>/collect_small_train_guided.jsonl` | Gemini |
| 3 | Stage-1 training set (310) and its trainer-format copy | `uv run python -m jaleesweights.sft_small --run <run> --collect <that collection> --judgments data/runs/<run>/judgments_selection.jsonl` | free |
| 4 | Stage-1 training: LoRA rank 32, lr 5e-5, 2 epochs, batch 8 | `uv run python -m jaleesweights.train_sft_small --run <run> --data data/runs/<run>/sft_train_small_messages.jsonl` | Tinker |
| 5 | Held-out collection from stage 1, bare and with guide | `uv run python -m jaleesweights.collect_small test-unstated --run <run> --model tinker://<stage-1>/sampler_weights/final --subject inkling-small-sft --concurrency 3`; the same with `test-guided` | Tinker |
| 6 | Opus scores base and stage-1 held-out answers | `uv run python -m jaleesweights.judge opus --run <run> --collect <the four held-out files>` | Anthropic |
| 7 | Sample 4 answers per training cell from stage 1 | `uv run python -m jaleesweights.collect_small train-unstated --run <run> --k 4 --model tinker://<stage-1>/sampler_weights/final --subject inkling-small-sft --concurrency 3` | Tinker |
| 8 | Gemini rates the samples, after-pushback scope | `uv run python -m jaleesweights.judge rate-samples --run <run> --collect data/runs/<run>/collect_small_train_unstated_sft_k4.jsonl` | Gemini |
| 9 | Stage-2 pairs and their trainer-format export | `uv run python -m jaleesweights.pairs --run <run> --samples <samples> --judgments <ratings> --out-name pairs_train70_small_sft2.jsonl`; `uv run python -m jaleesweights.comparisons --src data/runs/<run>/pairs_train70_small_sft2.jsonl` | free |
| 10 | Stage-2 training from the stage-1 checkpoint: β 0.1, lr 1e-5, 1 epoch | `uv run python -m jaleesweights.train_dpo_small --run <run> --sft-checkpoint tinker://<stage-1>/weights/final --comparisons data/runs/<run>/comparisons_train_small_sft2.jsonl` | Tinker |
| 11 | Held-out collection from stage 2, bare; Opus scores it | `collect_small test-unstated ... --model tinker://<stage-2>/sampler_weights/final --subject inkling-small-sftdpo`; `judge opus` | Tinker, Anthropic |
| 12 | Scores and paired comparisons | `uv run python -m jaleesweights.score --small data/runs/<run>/judgments_eval.jsonl` | free |

The collection step's `--concurrency` matters: the base model's lane sustains about 22
concurrent conversations; a tuned checkpoint's lane far fewer (the runs used 3).

### Local demonstration: a Gemma-family model on your own GPU

A worked example of the same recipe on hardware a team plausibly owns, with the Hugging Face
stack the Modal functions run inside (`transformers`, `peft`, vLLM) and no Modal account.
Default model `google/gemma-4-12B-it` in bf16; `--model`, `--dtype`, `--batch`,
`--max-model-len` and `--gpu-memory-utilization` are options on every command. **Its numbers
are not the paper's and are not expected to match them.**

Because a smaller Gemma model is not a subject of the benchmark main run, the demonstration
collects its own teacher answers first and then follows the Inkling-Small order. Use a
different `--subject` for each pass (the Opus judgments of all passes share one file):

| # | Step | Command | Needs |
|---|---|---|---|
| 1 | Collect base answers: training half with guide; held-out half bare and with guide | `uv run python -m jaleesweights.local.gemma_collect --inputs data/reference/train_inputs_gemma.jsonl --guide --subject gemma12-base --run <run>`; `... --inputs data/reference/eval_inputs_gemma.jsonl --subject gemma12-base --run <run>`; the same with `--guide` | GPU (vLLM) |
| 2 | Gemini rates the guided training-half answers | `uv run python -m jaleesweights.judge gemini-select --run <run> --collect data/runs/<run>/collect_gemma12-base_train_guided.jsonl` | Gemini |
| 3 | Stage-1 training set | `uv run python -m jaleesweights.sft_small --run <run> --collect <that file> --judgments data/runs/<run>/judgments_selection.jsonl --subject gemma12-base` | free |
| 4 | Stage-1 training | `uv run python -m jaleesweights.local.gemma_sft --data data/runs/<run>/sft_train_small.jsonl --run <run>` | GPU |
| 5 | Held-out collection from stage 1, bare and with guide | `gemma_collect --inputs data/reference/eval_inputs_gemma.jsonl --adapter data/runs/<run>/gemma-sft/adapter --subject gemma12-sft --run <run>`; the same with `--guide` | GPU |
| 6 | Opus scores base and stage-1 held-out answers | `uv run python -m jaleesweights.judge opus --run <run> --collect <the four held-out files>` | Anthropic |
| 7 | Sample 4 answers per training cell from stage 1 | `gemma_collect --inputs data/reference/train_inputs_gemma.jsonl --adapter data/runs/<run>/gemma-sft/adapter --k 4 --temperature 1.3 --subject gemma12-sft --run <run>` | GPU |
| 8 | Gemini rates the samples | `uv run python -m jaleesweights.judge rate-samples --run <run> --collect data/runs/<run>/collect_gemma12-sft_train_unstated_k4.jsonl` | Gemini |
| 9 | Stage-2 pairs | `uv run python -m jaleesweights.pairs --run <run> --samples <samples> --judgments <ratings>` | free |
| 10 | Stage-2 training, stage 1 as reference | `uv run python -m jaleesweights.local.gemma_dpo --pairs data/runs/<run>/pairs.jsonl --sft-adapter data/runs/<run>/gemma-sft/adapter --run <run>` | GPU |
| 11 | Held-out collection from stage 2, bare; Opus scores it | `gemma_collect --inputs data/reference/eval_inputs_gemma.jsonl --adapter data/runs/<run>/gemma-sft-dpo/adapter --subject gemma12-sftdpo --run <run>`; `judge opus` | GPU, Anthropic |
| 12 | Scores and paired comparisons for your arms | `uv run python -m jaleesweights.score --extra-judgments data/runs/<run>/judgments_eval.jsonl --extra-subject gemma12-base --extra-subject gemma12-sft --extra-subject gemma12-sftdpo --extra-paired gemma12-sft:gemma12-base --extra-paired gemma12-sftdpo:gemma12-sft` | free |

**Run this first** on the GPU machine, before anything above:

```bash
uv run python -m jaleesweights.local.gemma_sft --data data/reference/sft_train_small.jsonl --run smoke --limit 4
uv run python -m jaleesweights.local.gemma_collect --inputs data/reference/eval_inputs_gemma.jsonl \
    --adapter data/runs/smoke/gemma-sft/adapter --subject smoke --run smoke --limit 5
```

The first loads the model, builds the adapter, runs the start-up parity check and writes an
adapter from four examples; the second serves the model with that adapter through vLLM on
five conversations. Together they exercise everything the demonstration needs, in minutes.

**Hardware.** Figures marked *measured* come from the paper's 31B runs on Modal; figures
marked *derived* follow from the model's size and the scripts' settings. Nothing below was
measured on a non-Modal machine.

- *Measured, 31B.* Stage-1 training on one B200: 79 optimizer steps, **66.0 GB peak GPU
  memory**, about 15 minutes. Stage-2 training on one B200: 63 steps (peak not in the local
  records). Held-out collection on one H200 with vLLM: 420 two-turn conversations in about
  6 minutes; sampling: 1,680 conversations in one pass.
- *Derived.* bf16 needs two bytes per parameter for the weights alone. Training adds little
  on top (66 GB measured against 62 GB of 31B weights): LoRA rank 32, one conversation per
  forward pass with a batch of 8 by gradient accumulation, conversations capped at 16,384
  tokens, gradient checkpointing on. Stage 2 holds two adapters over one copy of the weights.
  Serving as the scripts set it (bf16, LoRA, a 32,768-token window, 92% of memory) needs the
  weights plus room for the key-value cache; on a smaller card reduce `--max-model-len` or
  `--gpu-memory-utilization` — results do not change, throughput does.

| Model | bf16 weights | Training fits on | Serving as set fits on | Notes |
|---|---|---|---|---|
| gemma-4-12B-it (default) | ~24 GB | one 48 GB or 80 GB GPU with room; a 32 GB card is marginal | 80 GB comfortably; 48 GB with a smaller window | same dense layout as the paper's 31B: the code and LoRA targets carry over with only the model name changed |
| gemma-4-E4B-it | ~8 GB | one 24 GB consumer GPU | 24 GB | weakest starting point; different internal layout — check LoRA targets and vLLM support before relying on it |
| gemma-4-31B-it (the paper's) | ~62 GB | one 80 GB GPU, thin headroom (66 GB measured) | 141 GB+; on 80 GB only with a reduced window | the paper's model; the main-run teacher data could be reused via `sft_guided` |

Software the Modal runs used, untested locally: Linux, an NVIDIA driver supporting CUDA
12.8 (the B200 needs it; Hopper and Ampere cards work with the same stack), Python 3.12,
`torch` 2.7+, `transformers` 4.53+, `peft` 0.15+, `accelerate` 1.3+, vLLM 0.10+ (which
compiles Gemma-4 kernels at start-up and needs the CUDA toolkit present). Disk: the weights
in the Hugging Face cache (two bytes per parameter) plus adapters of a few hundred MB.

## Costs

Rough figures from the experiment record (GitHub issue #21, August 2026 prices), per run.
Where no figure was recorded, it says so.

| Step | Rough cost | Notes |
|---|---|---|
| Gemma stage-1 training | ~$5 | the 4-bit run: 40 min on an H200; the bf16 run of record took ~15 min on a B200, cost not recorded separately |
| Gemma stage-2 training | ~$10 | the 4-bit run: ~2 h on an H200; bf16 on a B200 not recorded separately |
| Gemma sampling pass (1,680 conversations) | ~$6 | one H200 |
| Gemma held-out collection | ~$4 per condition | one H200, ~6 min of GPU time plus start-up |
| Capability panel | not recorded | one H200, up to a few hours per checkpoint |
| Gemini rating of 1,680 samples | ~$20 | after-pushback scope only |
| Gemini rating of a 420-cell guided collection, both scopes | not recorded | 840 judgments |
| Opus scoring of one held-out condition (840 judgments) | ~$6 | |
| Whole Gemma pipeline (both stages, sampling, selection, evaluations, guards) | ~$110 on the 4-bit chain; the paper says "under $100" | the bf16 re-run of record was budgeted at $60–80 |
| Inkling-Small stage 2 (training, collection, Opus) | ~$35 | estimated $40–50 beforehand |
| Inkling-Small base collections and stage 1 | not recorded | |
| Local demonstration | electricity and your GPU time | judge costs as above |

## What was and was not verified before handoff

This folder was assembled on a Mac with no NVIDIA GPU, without re-running any paid step.

Verified here:

- A fresh clone installs with `uv sync`; the data installs from the archives; every free step
  runs; the eight rebuilt files are byte-identical to the released copies; `score` reproduces
  the paper's table and gives the same output on every run.
- Pointed at the complete released data, every judging and collection command reports
  nothing to do and builds no network client. With no keys set, each names only the key it
  needs.
- Every paid step prints its preflight and stops on `--dry-run`: the Tinker trainers, the
  five Modal drivers (as plain Python modules, without a Modal account), the three
  demonstration commands (which report `GPU: none` here).
- The demonstration's conversation renderer, with the real Gemma-4-12B tokenizer, is
  prefix-stable and masks exactly the assistant turns.
- The ported code is the as-run code: the first commit of this folder holds every script as
  it ran, so `git log` shows each change made in porting.

Not verified here, because it cannot be:

- Any Modal launch, including creating the volume and secret in a fresh account and
  building the images. The first thing to run is the stage-1 smoke test (`--limit 4`).
- Any Tinker training or collection against a live account.
- The local demonstration on a GPU: loading a model, training, serving. Run its smoke tests
  first (above).
- That the judge and base models are still served under the same ids (see below).

## Weights, judges, versions

- **No trained weights are included.** The recipe retrains them. A Gemma run leaves its
  adapter on your Modal volume at `/runs/<run-name>/adapter`, or, for the demonstration, in
  `data/runs/<run>/gemma-sft/adapter` and `.../gemma-sft-dpo/adapter`; an Inkling-Small run
  leaves `tinker://` checkpoint addresses in your Tinker account, recorded in the trainer's
  `checkpoints.jsonl`. The released run records' `load_checkpoint_path` fields hold the
  original account's addresses, which are useless to anyone else and kept only as a record.
- **Judges**: selection by `gemini-3.1-pro-preview`, held-out scoring by `claude-opus-4-8`.
  **Base models**: `google/gemma-4-31B-it`, `thinkingmachines/Inkling-Small`. These ids are
  what the runs used; whether they are still served was not re-tested. A retired judge would
  make new scores incomparable with the paper's — the released judgments still reproduce the
  paper's table regardless.
- The 70/70 scenario split of record is `split_70_70.json` (seed 3446); the guide text sent
  to the models is `guided_prefix.txt`, identical to what the benchmark package produces.

## The archive

`archive/` holds the scripts of the approaches that were tried and dropped, the earlier 4-bit
Gemma chain, and the Inkling-Small dose sweep, exactly as they ran (one exception: comments
that named a third party were reworded). They are **not maintained** and do not run from
their new location; `archive/README.md` says what each file was for and which paper claim it
supports. Their data is in the reference archive alongside the data of record.

## Licence

Code: Apache License 2.0 (`LICENSE` at the repository root). Data release: Creative Commons
Attribution 4.0, with this notice, which is also inside both archives:

> The data contains model outputs produced by third-party providers' models — the
> JaleesBench main run's answers from every subject model, the judgments written by Claude
> Opus and Gemini, and the training sets and sampled answers built from them. Those model
> outputs remain subject to the terms of the providers that produced them. The CC BY 4.0
> licence applies to what the authors contributed and grants nothing beyond the providers'
> terms.
