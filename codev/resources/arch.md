# Architecture

This document evolves as the project grows. Update it during the review phase of any work
that introduces or changes architectural patterns.

## Repository shape

Three independent `uv` projects, each with its own `pyproject.toml` and `uv.lock`, and no
root project:

| Project | What | Depends on |
|---|---|---|
| `jaleesbench/` | the benchmark harness: scenario bank, collection, two-judge scoring, paper statistics, web export | — |
| `jaleesweights/` | the fine-tuning recipe (issue #36): training-set builders, judging wrappers, Tinker trainers, Modal drivers, a local GPU demonstration, data fetch, scoring | `jaleesbench` as an **editable** path dependency |
| `quranquote/` | the verbatim-quoting battery | — |

`apps/jaleesbrowser/` is the static results browser (TypeScript, deployed by Pages from
committed data). `docs/paper/` holds both papers.

## Where data lives

- The benchmark **main run** (`collect.jsonl`, `judgments.jsonl`, `judgments_v2.jsonl`,
  `citations_llm.jsonl`) is gitignored under `jaleesbench/results/`. It is distributed as
  part of the JaleesWeights data release and installed by `jaleesweights.fetch_data`.
- The benchmark's own scoring overlays `judgments_v2.jsonl` (re-judged disagreement cells)
  on `judgments.jsonl`; JaleesWeights reads the base file, as its runs did.
- JaleesWeights **reference data** (what the original runs produced) is installed under
  `jaleesweights/data/reference/` (gitignored) and is read-only for every command; a
  central guard (`jaleesweights.paths.output_path`) refuses writes there and into
  `jaleesbench/results/`. New runs write under `jaleesweights/data/runs/<name>/`.
- Checksums of the release archives are committed in `jaleesweights/release/`; the archives
  themselves are staged locally and published as a GitHub release.

## Paths and credentials

- The benchmark package resolves its data folder, the repo-root `.env` and the Vertex
  service-account file from **its own installed location**. That is why `jaleesweights`
  installs it editable: a copy in a virtual environment would point those paths at nothing.
- `jaleesweights.paths` derives every location from the clone (overridable with `JW_*`
  variables) and refuses to import outside a clone; the package is clone-only by design.
- One `.env` parser for the repository: `jaleesbench.collect.load_env(required=..., gemini=...)`.
  The benchmark's commands require the full key set; JaleesWeights commands pass the keys
  they use. Values are literal (no quote stripping).

## Paid steps

Every JaleesWeights command that spends money or rents hardware prints a preflight (inputs
and counts, model, settings, which account is billed) and stops on `--dry-run`. Collection
and judging are resume-safe by key, so a complete output file means no call is made. The
Modal drivers run their preflight as plain Python modules (`python -m
jaleesweights.modal.<driver>`) because `modal run` requires a token before it calls a local
entrypoint; a real Modal launch also requires the local source file of every uploaded input.
