# Plan: JaleesWeights — commit the fine-tuning work as a runnable `jaleesweights/` folder for handoff

**Specification**: [codev/specs/36-jaleesweights-commit-the-fine-.md](../specs/36-jaleesweights-commit-the-fine-.md)

## Executive Summary

The spec's recommended approaches are taken as decided: `jaleesweights/` becomes a third
`uv` project beside `jaleesbench/` and `quranquote/`, depending on the benchmark package by
local path (1A); the 24 final-pipeline scripts are ported with minimal changes, with the
as-run text committed first so every port is a reviewable diff (the "minimal port"); the
data goes out as two archives on a GitHub release, built and scanned locally and created
only after the owner approves (2A); the archive is one flat folder with an index (3A);
structured run records are kept and console output left out (4A); a fresh clone is shown to
work by free checks only (5A); and the local demonstration defaults to Gemma-4-12B on one
80 GB GPU (6A), with the owner's questions 1–9 at their defaults.

Eight phases, each one commit. The first commit places every kept script, verbatim except
for three reworded comments, at its final path — so private wording never enters history
and each later phase's diff against the as-run text is small. Then: the installable
project and the key-loader change; the data archives and the download step; the free steps
(builders, exports, scoring), proven byte-identical against the reference data; the judging
and Tinker steps; the Modal drivers; the local demonstration; and finally the README, the
archive index, the fresh-clone walk-through and the owner's report.

Layout the phases build toward:

```
jaleesweights/
  README.md                       accounts, keys, costs, hardware, run orders, smoke tests
  pyproject.toml  uv.lock         the project; benchmark as an editable path dependency
  jaleesweights/                  the package (one module per step, Typer entry points)
    paths.py  env.py  common.py   clone layout, key loading, shared filters and constants
    inputs.py sft_guided.py sft_small.py pairs.py comparisons.py score.py    free steps
    judge.py collect_small.py train_sft_small.py train_dpo_small.py          API / Tinker steps
    fetch_data.py                 the download step
    modal/                        the five Modal drivers (run with `modal run`)
    local/                        the demonstration: collect, sft, dpo on the team's own GPU
  archive/                        19 as-run scripts + README.md index (not maintained)
  release/checksums.sha256        checksums of the two data archives (committed)
  tests/                          offline tests, no keys, no data
  data/                           gitignored: reference/ (downloaded), runs/<name>/ (new runs)
```

Two conventions run through the phases. **Preflight:** every command that would spend
money or rent hardware (the Tinker trainers, the Modal drivers, the collection and judging
commands, the local demonstration) first checks its inputs — files exist, row counts,
model id, the keys it needs, the account names or hardware it will use — prints that
summary, and only then launches; `--dry-run` stops after the summary. That is how the spec's
"finds its inputs and states what it would rent, without launching" is met, and it is one
shape reused everywhere. **Size:** no file added to git exceeds 1 MB, with `uv.lock` as the
one named exception (the benchmark's is already 826 KB; this one adds `modal` and the GPU
group).

Reference data is installed under `jaleesweights/data/reference/` (flat, original file
names, Tinker run folders under `tinker-runs/`); the benchmark main run under
`jaleesbench/results/`, where the benchmark already expects it and git already ignores it.
Every step takes explicit input and output paths as options, with defaults that read the
reference directory and write under a named run directory; nothing writes into the
reference directory.

## Phases (Machine Readable)

```json
{
  "phases": [
    {"id": "phase_1", "title": "As-run scripts in their final places, private wording removed"},
    {"id": "phase_2", "title": "Installable project, clone-relative paths, keys scoped to what a step uses"},
    {"id": "phase_3", "title": "Data archives, checksums and the download step"},
    {"id": "phase_4", "title": "Free steps ported: builders, exports and repeatable scoring"},
    {"id": "phase_5", "title": "Judging and Inkling-Small Tinker steps ported"},
    {"id": "phase_6", "title": "Gemma on Modal: drivers with configurable account names"},
    {"id": "phase_7", "title": "Local demonstration on the team's own GPU"},
    {"id": "phase_8", "title": "README, archive index, fresh-clone walk-through and owner report"}
  ]
}
```

## Phase Breakdown

### Phase 1: As-run scripts in their final places, private wording removed

**Dependencies**: None

#### Objective

Put every kept script into git exactly as it ran — at the path where its ported version
will live — with the three private-wording comments reworded before anything is committed.
After this phase, every later change to a final-pipeline script is a diff against the text
that produced the paper's numbers, and no commit on the branch carries the other team's
name.

#### Files to Create / Modify

- `jaleesweights/archive/<19 scripts>` — verbatim copies of the archive scripts;
  `train_dpo_run.py` and `train_dpo_run2.py` with their comments reworded: the
  docstring's provenance sentence and the inline remarks that attribute the batch size and
  replica count become "the preference-optimization settings of record".
- `jaleesweights/jaleesweights/<module>.py` — verbatim copies of the 24 final scripts at
  their final module paths (mapping below); `modal/gemma_sft_bf16.py` with its docstring's
  first sentence reworded to name no other project.
- `jaleesweights/jaleesweights/__init__.py`, `modal/__init__.py`, `local/__init__.py`
  (empty).
- `jaleesweights/split_70_70.json` — the split of record, verbatim.
- `jaleesweights/guided_prefix.txt` — verbatim.

Mapping of final scripts to module paths (several as-run scripts land in one module when
the port will merge them; until phase 4/5 the module simply holds them concatenated with a
separator comment, so the diff stays readable):

| Module | As-run script(s) |
|---|---|
| `inputs.py` | `build_train_inputs.py` |
| `sft_guided.py` | `build_sft_guided.py` |
| `sft_small.py` | `build_sft_small.py` |
| `pairs.py` | `build_sftbf16_pairs.py`, `build_small_sft2_pairs.py` |
| `comparisons.py` | `export_comparisons.py` |
| `score.py` | `score_eval.py`, `paired_sftdpo_bf16.py`, and a copy of `paired_small_sweep.py` (which also stays in the archive as-is): it is the only as-run code for the Inkling-Small rows and paired comparisons, so the port starts from it |
| `judge.py` | `judge_train_samples.py`, `judge_eval_basevllm.py`, `judge_eval_bf16.py`, `judge_eval_sftdpo_bf16.py`, `judge_small_selection.py`, `judge_small_baselines.py`, `judge_small_sft.py`, `judge_small_sftdpo.py` |
| `collect_small.py` | `collect_small.py` |
| `train_sft_small.py` | `train_sft_small.py` |
| `train_dpo_small.py` | `train_dpo_small_sft2.py` |
| `modal/gemma_sft_bf16.py`, `modal/gemma_dpo2_bf16.py`, `modal/gemma_eval.py`, `modal/gemma_sample.py`, `modal/gemma_capability.py` | the five Modal drivers |

#### Deliverables

- [ ] 43 kept scripts present: 19 under `archive/`, 24 under the package (in 16 files, one
      archive script additionally copied into `score.py` as a port source). The 44th is left
      out.
- [ ] `diff` of each copied file against its scratch original is empty, except the three
      reworded comments.
- [ ] A search of the phase's commit (`git show`) for the other team's name and its
      configuration file name finds nothing.
- [ ] Tests for this phase: none new (no code runs yet); the benchmark suite still passes.

#### Acceptance Criteria

- [ ] The diff-against-original check and the private-wording search both pass.
- [ ] Nothing under `archive/` is imported or executed by anything.
- [ ] Benchmark tests pass (`uv run --directory jaleesbench pytest -q`).

#### Test Plan

Manual: run the per-file diff and the search over `git show <commit>`; record both in the
thread. Automated: none.

### Phase 2: Installable project, clone-relative paths, keys scoped to what a step uses

**Dependencies**: Phase 1

#### Objective

Make `jaleesweights/` install with one command and give every later module the three
things the scratch scripts lacked: a clone-relative idea of where the main run, the
reference data, the run directory and the `.env` file are; key loading that asks only for
what a step uses; and the shared constants and filters in one place.

#### Files to Create / Modify

- `jaleesweights/pyproject.toml` — project `jaleesweights`, Python ≥ 3.12; dependencies:
  `jaleesbench` (via `[tool.uv.sources]` as an **editable** path dependency on
  `../jaleesbench`), `modal`, `typer`, `openai`, `tinker`, `tinker-cookbook[inkling]`
  (the last three are already what the benchmark pins; declared here because the Tinker
  steps import them directly); dependency group `gpu`, every entry marked
  `sys_platform == 'linux'`: `torch>=2.7` (from the CUDA 12.8 index, declared as a
  `[tool.uv.sources]` index entry), `transformers>=4.53`, `peft>=0.15`, `accelerate>=1.3`,
  `vllm>=0.10` — the same versions the Modal images pin; `lm-eval` is not in the group
  because the capability panel is not part of the local demonstration. `[tool.uv]
  environments` limited to Linux and macOS so the lock resolves on this Mac without
  building GPU wheels. Group `dev`: `pytest`, `pytest-asyncio`. `uv.lock` committed (the
  named exception to the 1 MB rule).
- `jaleesweights/jaleesweights/paths.py` — `REPO_ROOT` from this file's position;
  `BENCH_RESULTS = REPO_ROOT / "jaleesbench" / "results"`, `REFERENCE`, `RUNS`, all
  overridable by environment variables (`JW_BENCH_RESULTS`, `JW_REFERENCE`, `JW_RUNS`);
  `run_dir(name)`; `main_run_files()` that fails fast, naming the missing file, when the
  main run is not installed.
- `jaleesweights/jaleesweights/env.py` — `load_keys(required: list[str], gemini: bool)`:
  reads `REPO_ROOT/.env` (environment wins), then fails naming exactly the missing keys;
  the Gemini credential check (Vertex file at the repo root or `GEMINI_API_KEY`) only when
  asked. Never prints a value.
- `jaleesweights/jaleesweights/common.py` — `GEMINI`, `OPUS`, `MIN_GAP`, `MARKER`,
  `RESOLVES`, `GUIDE_REF`, `dangling_markers`, `load_split`, `judgment_key` re-export.
  Nothing else moves here yet.
- `jaleesbench/jaleesbench/collect.py` — `load_env(required=REQUIRED_KEYS,
  gemini=True)`: default behaviour unchanged; callers may narrow.
- `jaleesbench/jaleesbench/judge.py` — `judge_all(..., required_keys=None)` passes the
  narrowing through and builds clients only for the providers of the judges it will call
  (today it always builds both Anthropic and Gemini). `rejudge_disagreements` keeps calling
  `load_env()` with defaults; it is the benchmark's own command and is not narrowed.
- `jaleesbench/tests/test_units.py` — tests for the two changes.
- `jaleesweights/tests/conftest.py`, `tests/test_paths_env.py`.
- `.gitignore` — `jaleesweights/data/`, `jaleesweights/.venv/`.

#### Deliverables

- [ ] `cd jaleesweights && uv sync` succeeds on this Mac (without the `gpu` group).
- [ ] `uv run python -c "import jaleesbench, jaleesweights"` works from the project
      directory and `jaleesbench.__file__` is inside the clone's `jaleesbench/` (editable).
      This matters beyond tidiness: the benchmark derives the Vertex service-account path
      and its `.env` path from its own package location, and `judge_all` → `make_clients`
      → `gemini_client()` reads the Vertex path. JaleesWeights loads keys itself before
      calling in, so `.env` is covered either way; the Vertex file is found only because the
      install is editable, and the README says so (spec scenario 8b).
- [ ] Key-loader narrowing in the benchmark with its default unchanged.
- [ ] Tests for this phase.

#### Acceptance Criteria

- [ ] `load_keys(["ANTHROPIC_API_KEY"], gemini=False)` with only that key set succeeds;
      with nothing set fails naming only that key.
- [ ] Benchmark `load_env()` with no arguments still demands the seven keys (existing
      behaviour, now under test).
- [ ] `judge_all(judges={"claude-opus-4-8"}, required_keys=[...])` does not touch Gemini
      credentials (unit test with the network call stubbed).
- [ ] `paths.REPO_ROOT` is the clone root when run from the repo root and from inside
      `jaleesweights/`.
- [ ] Both test suites pass.

#### Test Plan

Unit: paths under both working directories; `load_keys` missing/present/partial; benchmark
`load_env` default and narrowed; `judge_all` client construction with a stub. Manual:
`uv sync`, the import check.

### Phase 3: Data archives, checksums and the download step

**Dependencies**: Phase 2

#### Objective

Build the two release archives on this machine, commit their checksums, and give the
README a single download step that works from the published release or from archive files
already on disk, verifies checksums, and says plainly when the release is not yet public.
Nothing is uploaded in this phase.

#### Files to Create / Modify

- Staging (gitignored, under `jaleesweights/data/staging/`): `jaleesweights-data.tar.gz`
  — all 58 top-level `.jsonl` files (every one is final or archive) plus
  `tinker-runs/<10 folders>/{config.json,metrics.jsonl}` = 78 members —
  and `jaleesbench-main-run.tar.gz` (`collect.jsonl`, `judgments.jsonl`,
  `citations_llm.jsonl`). Built by a documented one-off command sequence recorded in the
  thread, not by a committed script (the source is the read-only scratch folder on this
  machine and will not exist for anyone else). The release tag is fixed now:
  `jaleesweights-data-v1`; `checksums.sha256`, the fetch module and the README all use it.
- Run records, per the owner's decision at the plan gate (2026-10-01): from each of the
  ten Tinker run folders keep `metrics.jsonl` as-is and `config.json` with its `log_path`,
  `train_path` and `file_path` fields rewritten to the release-relative file name (for
  example `tinker-runs/dpo_small_sft2_run` and `comparisons_train_small_sft2.jsonl`; no
  original-machine prefix); drop `checkpoints.jsonl` (addresses in the owner's Tinker
  account, useless to anyone else). The rewrite is the only edit to any released file and
  `CONTENTS.md` says so.
- `jaleesweights/release/checksums.sha256` — committed; also `release/CONTENTS.md` listing
  every file in each archive with its size (no left-out names appear, by construction).
- `jaleesweights/jaleesweights/fetch_data.py` — Typer command: `--from-dir PATH` installs
  from local archives; otherwise downloads the two assets from
  `https://github.com/iaser-ai/jaleesbench/releases/download/<tag>/<asset>` (tag fixed in
  the module, overridable); verifies against `checksums.sha256` before extracting; a 404
  produces "the data release <tag> has not been published yet"; a mismatch names the
  archive and stops. Extracts to `data/reference/` and `jaleesbench/results/`; refuses to
  overwrite an existing reference directory, or an existing main-run file, unless
  `--force`.
- `jaleesweights/tests/test_fetch.py`.

#### Deliverables

- [ ] Two archives staged; checksums and contents list committed.
- [ ] `fetch_data --from-dir` installs both and leaves the tree ready for phase 4.
- [ ] Tests for this phase.

#### Acceptance Criteria

- [ ] Every file in `CONTENTS.md` is one the spec classes final or archive; none is left
      out; the experiment archive has exactly 78 members (58 + 20) and the main-run archive
      3; no `checkpoints.jsonl` is present. `guided_prefix.txt` and `split_70_70.json` are
      in git instead.
- [ ] No released `config.json` contains an absolute path; its three path fields name
      release-relative files that exist in the archive.
- [ ] Exhaustive, not spot-checked: a `sha256` list of every member of both archives, made
      from the scratch originals, equals the list made from the files `fetch_data
      --from-dir` installs (81 lines, all matching; the ten `config.json` entries are
      compared after the same path rewrite). Recorded in the thread.
- [ ] Both destinations refuse to overwrite existing files without `--force`.
- [ ] Checksum mismatch → named failure; missing release → the "not published" message
      (tested with a stub HTTP response); `--from-dir` path → extraction succeeds.
- [ ] Both test suites pass.

#### Test Plan

Unit: checksum verify on temp files; the not-published and mismatch paths with a stubbed
downloader; extraction layout and overwrite refusal on a tiny fake archive. Manual: build
the archives, run `fetch_data --from-dir data/staging`, run the exhaustive 81-file checksum
comparison against the scratch originals (config files compared after the rewrite).

### Phase 4: Free steps ported: builders, exports and repeatable scoring

**Dependencies**: Phase 3

#### Objective

Port the steps that spend nothing, and prove them: the eight rebuilt files are
byte-identical to the reference copies and the scoring step reproduces the paper's main
table.

#### Files to Create / Modify

- `inputs.py` — one command writing both halves (`train_inputs.jsonl`,
  `eval_inputs.jsonl`) from the main run; the existing self-check becomes a comparison
  against the reference copy when present.
- `sft_guided.py` — reads the main run via `paths`; `--out`.
- `sft_small.py` — `--collect` (the guided training-half answers), `--judgments` (their
  Gemini ratings), `--subject`, `--out`; writes both the training set and the `_messages`
  form (the manual conversion becomes a documented output of this step). The local
  demonstration feeds this same command with its own collections.
- `pairs.py` — one max-gap builder with two documented invocations (`--samples`,
  `--judgments`, `--chain-suffix` for the Inkling-Small `-c{chain}` naming); both as-run
  variants are the same function with different inputs — the diff against phase 1 shows
  the merge.
- `comparisons.py` — `--src`, `--out`.
- `score.py` — the main table for both models (base control, stage 1, stage 2, guided
  rows, the Inkling reference row) and the four paired comparisons; iteration over
  `sorted(a.keys() & b.keys())` so the bootstrap is repeatable; `--reference` /
  `--judgments` options so a new run can be scored the same way. Honest accounting: the
  Gemma rows and the Gemma paired comparison are ported from `score_eval.py` and
  `paired_sftdpo_bf16.py`; the Inkling-Small rows and its two paired comparisons are
  **written new**, using `paired_small_sweep.py`'s `bands()`/`paired()` as the reference
  implementation (subjects `inkling-small`, `inkling-small-sft`, `inkling-small-sftdpo`).
  The spec's table comparison is what proves them.
- `tests/test_builders.py`, `tests/test_score.py` with small made-up fixtures.

#### Deliverables

- [ ] Six Typer commands; the manual `_messages` conversion is gone.
- [ ] Eight files rebuilt into a run directory and compared.
- [ ] Tests for this phase.

#### Acceptance Criteria

- [ ] `sha256` of the eight rebuilt files equals the reference copies'
      (`train_inputs_gemma.jsonl`, `eval_inputs_gemma.jsonl`, `sft_train_guided.jsonl`,
      `pairs_train70_sftbf16.jsonl`, `sft_train_small.jsonl`,
      `sft_train_small_messages.jsonl`, `pairs_train70_small_sft2.jsonl`,
      `comparisons_train_small_sft2.jsonl`).
- [ ] `score.py` output: every score and paired difference matches the paper to three
      decimals; single-score intervals match as printed; the two paired intervals within
      0.01; two consecutive runs give identical output.
- [ ] Builders run from the repo root and from inside `jaleesweights/` with the same result.
- [ ] Reference directory checksums unchanged after all builders ran.
- [ ] A new run chains (spec scenario 8a): in an empty run directory holding made-up
      collection and judgment files, `sft_small` writes a training set there and
      `comparisons` / `pairs` consume outputs from there, never from the reference
      directory (unit test with tiny fixtures).
- [ ] Both test suites pass.

#### Test Plan

Unit: filters and screens on made-up conversations; the new-run chain on fixtures; max-gap pairing on a hand-built band
table (known pair count, both directions, dedup, gap floor); comparison export label
determinism; scoring on a made-up judgment file (means, repeatability, paired sign counts).
Manual: the eight-file comparison, the table comparison against the paper, the two-cwd
check, the reference-checksum check.

### Phase 5: Judging and Inkling-Small Tinker steps ported

**Dependencies**: Phase 4

#### Objective

Port the API-billed and Tinker-billed steps so they run from the clone with only the keys
they use, write to a run directory, take checkpoints as inputs, and — pointed at the
complete reference data — find nothing to do.

#### Files to Create / Modify

- `judge.py` — three commands: `opus` (held-out scoring: `--collect` files, `--out`;
  Anthropic key only), `gemini-select` (both scopes, Gemini credential only), `rate-samples`
  (after-pushback scope only, chain-aware, from `judge_train_samples.py`). The first two
  call the benchmark's `judge_all` with explicit paths and narrowed keys.
- `collect_small.py` — Typer options replace the environment knobs (`--pass`, `--model`,
  `--subject`, `--k`, `--out`, `--concurrency`); the hardcoded `.env` path becomes
  `env.load_keys(["TINKER_API_KEY"])`; inputs default to the reference inputs files.
- `train_sft_small.py` — `--data`, `--log-dir` (under the run directory).
- `train_dpo_small.py` — `--sft-checkpoint` **required** (the as-run constant is gone),
  `--comparisons`, `--log-dir`; learning rate and epochs as options defaulting to the
  settings of record (1e-5, 1).
- Preflight in all five: check inputs (file present, row count), the keys the step uses,
  and for the trainers the model id, the number of examples or pairs and the settings;
  print the summary ("will train `thinkingmachines/Inkling-Small` on 672 pairs through
  Tinker, billed to your Tinker account"); `--dry-run` exits there. `judge` and
  `collect_small` print the same kind of summary including how many calls remain.
- `tests/test_steps_offline.py`.

#### Deliverables

- [ ] Five commands; no environment-variable knobs; no absolute paths.
- [ ] Tests for this phase.

#### Acceptance Criteria

- [ ] With placeholder `ANTHROPIC_API_KEY` and `GEMINI_API_KEY` set and nothing else,
      `judge opus` on each reference held-out file and `judge gemini-select` /
      `rate-samples` on the reference sample files each print "todo=0" and exit without a
      network call.
- [ ] With no keys set, each command fails naming only the key(s) it uses.
- [ ] `train_dpo_small` without `--sft-checkpoint` exits with a usage error.
- [ ] `train_sft_small --dry-run` and `train_dpo_small --dry-run --sft-checkpoint x` with a
      placeholder Tinker key print the preflight summary naming the model, the data size and
      the account, and exit without contacting Tinker (stubbed client asserts no call).
- [ ] `collect_small` pointed at a complete reference collection reports 0 to do.
- [ ] Both test suites pass.

#### Test Plan

Unit: option parsing and key requirements per command (stubbed network); done-set logic on
a tiny collect/judgment pair. Manual: the todo=0 runs against reference data (free by
construction: nothing left to judge or collect).

### Phase 6: Gemma on Modal: drivers with configurable account names

**Dependencies**: Phase 2

#### Objective

Make the five Modal drivers runnable from a new team's own Modal account: the volume name,
secret name and volume paths become settings with the as-run defaults; the input upload
and output download that were manual become documented commands; the capability panel's
checkpoint table is the bf16 chain. Function bodies are otherwise untouched.

#### Files to Create / Modify

- `modal/_config.py` — `VOLUME = os.environ.get("JW_MODAL_VOLUME", "gemma-dpo")`,
  `HF_SECRET = os.environ.get("JW_MODAL_HF_SECRET", "huggingface")`, and the **three**
  image definitions exactly as the drivers have them today: training (CUDA 12.8 base,
  torch cu128, transformers/peft/accelerate), serving (vLLM), capability (vLLM +
  `lm_eval[vllm,ifeval]`). Nothing is unified across them; the capability image stays its
  own.
- The five drivers import from `_config`; `gemma_eval.py` and `gemma_sample.py` take the
  inputs file path on the volume as an option (today hardcoded); `gemma_capability.py`
  checkpoint table = base, sft-bf16, sft-dpo-bf16, and `--chat` documented as the paper's
  mode.
- Preflight, same shape as phase 5, in each local entrypoint: check that the local inputs
  the README says to upload exist and have the expected row counts, print the volume and
  secret names, the volume paths it will read and write, the GPU type and the run name;
  `--dry-run` exits before any `.remote()`/`.spawn()`. The volume itself cannot be checked
  without an account and the summary says which checks were local.
- README fragments (finished in phase 8): `modal volume create`, `modal secret create`,
  `modal volume put` for inputs and training sets, `modal volume get` for outputs, with
  the exact volume paths each driver expects.

#### Deliverables

- [ ] Five drivers whose only diff against phase 1 is configuration and option plumbing.
- [ ] Tests for this phase: `modal run <driver> --help` for each driver under a fake HOME
      (no Modal credentials) prints usage — verified in this phase and recorded; a pytest
      that imports each driver module and checks the settings resolve.

#### Acceptance Criteria

- [ ] `git diff phase-1..HEAD -- jaleesweights/jaleesweights/modal/` touches no line inside
      a training loop, a sampling call or an lm-eval invocation; reviewed and stated in the
      thread.
- [ ] Each driver prints its usage without an account, and `--dry-run` prints the
      preflight summary (GPU type, volume, secret, paths, run name) and exits without an
      account (fake HOME, no credentials).
- [ ] No paid Modal run is launched (a four-example smoke run is offered to the owner in the
      review, not run).
- [ ] Both test suites pass.

#### Test Plan

Manual: the `--help` runs; the diff review. Unit: import-and-settings test.

### Phase 7: Local demonstration on the team's own GPU

**Dependencies**: Phase 5, Phase 6

#### Objective

Provide the demonstration: the two-stage recipe on a Gemma-family model on one local GPU,
with no Modal, following the Inkling-Small data flow (collect own base answers first).
Default model Gemma-4-12B in bf16; model, precision, batch and context window are options.
It cannot be executed here; it is checked by diff, compilation, usage output and a
CPU-only tokenizer test, and the README names the first smoke test.

#### Files to Create / Modify

- `local/gemma_collect.py` — from `gemma_eval.py` + `gemma_sample.py` function bodies:
  vLLM collection with `--inputs` (train or eval half), `--guide/--no-guide`, `--k`
  (1 for evaluation, 4 for sampling), `--temperature` (default: model config; 1.3 for
  sampling), `--adapter`, `--model` (default `google/gemma-4-12B-it`), `--dtype` (default
  bf16), `--max-model-len`, `--gpu-memory-utilization`, `--limit` (first N inputs, for the
  smoke test), `--subject`, `--out`. Writes the harness record schema so `judge` and
  `pairs` consume it unchanged.
- `local/gemma_sft.py` — from `gemma_sft_bf16.py`'s body: `--model`, `--dtype` (bf16
  default), `--data`, `--out`, `--batch`, `--lr`, `--epochs`, `--seed`, `--limit`,
  `--resume-from`; the 16,384-token cap and the parity check kept as they are.
- `local/gemma_dpo.py` — from `gemma_dpo2_bf16.py`'s body: `--model`, `--dtype`,
  `--sft-adapter` required, `--pairs`, `--out`, `--beta`, `--lr`, `--batch`, `--seed`,
  `--limit`, `--resume-from`.
- Preflight in all three, same shape: inputs, model id, dtype, settings, and the GPU it
  sees (`torch.cuda` device name and memory, "none" on this Mac) printed before anything
  loads; `--dry-run` exits there.
- `local/_render.py` — the `render`/mask function shared by the three, imported lazily
  from `transformers` so `--help` works without the `gpu` group.
- `tests/test_local_demo.py` — compile + `--help` for the three commands on a machine
  without the GPU group; a tokenizer-only mask test (`pytest.mark.skipif` no network).

#### Deliverables

- [ ] Three commands; GPU imports lazy; settings as options with the demonstration
      defaults.
- [ ] A written diff summary (thread) listing every difference from the Modal function
      bodies beyond paths and options.
- [ ] Tests for this phase.

#### Acceptance Criteria

- [ ] On this Mac, each command compiles and prints usage; `--dry-run` prints the preflight
      summary with "GPU: none" and exits; a missing GPU dependency is reported by name when
      a command is actually run.
- [ ] The mask test passes when the tokenizer can be fetched: rendering is prefix-stable and
      exactly the assistant turns are masked in a made-up conversation.
- [ ] The diff summary is in the pull request description.
- [ ] Both test suites pass.

#### Test Plan

Unit: compile, `--help`, lazy-import failure message; tokenizer mask test (skipped
offline). Manual: none possible here; the README's smoke order (`gemma_sft --limit 4`, then
`gemma_collect --limit 5 --adapter <smoke>`) is what a GPU team runs first.

### Phase 8: README, archive index, fresh-clone walk-through and owner report

**Dependencies**: Phase 7

#### Objective

Finish the handoff: the README a new team follows, the archive index, the top-level pointer,
the fresh-clone walk-through executed from an empty directory, the private-material search
over the whole branch, and the owner-facing report that accompanies the request to publish.
Open the pull request.

#### Files to Create / Modify

- `jaleesweights/README.md` — sections: what this is; accounts and keys (Anthropic, Gemini
  key or Vertex file, Tinker, Modal, Hugging Face not needed); install; data download
  (published release or `--from-dir`; the "not published yet" behaviour); the three run
  orders with cost/hardware column (figures from the experiment record, dated, "not
  recorded" where none); the hardware section (measured vs derived, from the spec); what
  was and was not verified before handoff and the smoke tests; scoring and the two paired
  intervals note, with the table of the eight rebuilt files and the command that produces
  each; weights not included; capability panel: chat mode is the paper's, raw
  results not in the release; the demonstration's numbers are not the paper's; the
  archive.
- `jaleesweights/archive/README.md` — the index: every archived script and data file, the
  approach it belonged to, the paper claim it supports, "not maintained, does not run from
  here", the one-line note on the four missing judgments.
- `README.md` (top level) — one paragraph and link.
- `codev/reviews/36-jaleesweights-commit-the-fine-.md` — started here, finished in the
  review phase.
- Outside git: `/private/tmp/agent-mail/spir-36-release-report.md` — all 204 scratch
  files by name with class and destination; archive contents; search result; the request
  to publish with the open questions that gate it (7: terms).

#### Deliverables

- [ ] README complete against the spec's README criterion, item by item.
- [ ] Fresh-clone walk-through: clone into an empty directory, no keys, `uv sync`,
      `fetch_data --from-dir`, all free steps, the eight-file and table comparisons — run
      and recorded in the thread with the commands used.
- [ ] Private-material search over `git log -p <base>..HEAD`, the working tree and both
      archives, with the patterns taken from the architect's local notes (never committed);
      result recorded in the report.
- [ ] Pull request opened; `porch done 36 --pr <N> --branch builder/spir-36`.

#### Acceptance Criteria

- [ ] Walk-through succeeds end to end on the free steps from the empty directory.
- [ ] Search finds nothing.
- [ ] No file added to git by this work exceeds 1 MB, except `jaleesweights/uv.lock`.
- [ ] Both test suites pass.

#### Test Plan

Manual: the walk-through; the search; a size check over `git diff --stat <base>..HEAD`.
Automated: the existing suites.

## Risks and Mitigation

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Phase 1 copies carry private wording into history | Low | High | Reword first; search `git show` of the commit before pushing; phase 8 repeats the search over the whole branch |
| The editable path dependency does not behave as expected under `uv` (non-editable copy in the environment) | Low | Medium | Phase 2 asserts `jaleesbench.__file__` is inside the clone; `paths.py` never relies on it; the Vertex-file dependence on it is documented |
| `uv lock` cannot resolve the GPU group on macOS (no vLLM or CUDA torch wheels) | Medium | Medium | Linux-only markers on the group and `[tool.uv] environments`; if resolution still fails, the group is split into its own `requirements-gpu.txt` referenced from the README — declared either way |
| `judge_all` change breaks the benchmark's own judging | Low | Medium | Default arguments preserve behaviour; tests for the default and the narrowed paths |
| The merged `pairs.py` or `score.py` silently changes a number | Low | High | Byte-identical rebuilds and the table comparison are the acceptance criteria of phase 4 |
| A Modal driver diff touches more than configuration | Low | High | Phase 6 acceptance is a reviewed diff confined to settings and options |
| The demonstration has a defect only a GPU would reveal | High | Medium | Diff summary in the PR; lazy imports so it at least starts; README names the four-example smoke test first |
| Owner's answer to question 7 (terms) delays publication | Medium | Low | `--from-dir` keeps the clone testable; the fetch step's "not published" message is honest in the meantime |
| Judge-model or Tinker-model retirement breaks a paid step after handoff | Medium | Medium | README states exact ids and that they were not re-tested |

## Documentation Updates

- New: `jaleesweights/README.md`, `jaleesweights/archive/README.md`,
  `jaleesweights/release/CONTENTS.md`.
- Changed: top-level `README.md` (pointer); `jaleesbench/README.md` gains one sentence on
  `load_env`'s optional narrowing.
- `codev/resources/arch.md` / `lessons-learned.md`: the review phase records that the
  repository now has three `uv` projects and where reference data lives; lesson: reword
  before the first commit, search the branch's history, not just the tree.
