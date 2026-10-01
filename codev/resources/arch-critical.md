# arch-critical.md — Always-On System-Shape Facts (HOT tier)

<!-- HOT tier: capped facts + a bounded map of arch.md. Always injected into every porch
phase prompt and into CLAUDE.md/AGENTS.md. CAP: <=10 facts, <=12 map topics, <=35 lines.
To add a fact, DEMOTE a weaker one into arch.md (displacement). MAINTAIN polices the cap
and keeps the map in sync with arch.md's top-level sections.
STARTER: replace the examples below with YOUR project's facts and arch.md sections. -->

## Critical facts (consult before deciding)
- Three independent `uv` projects (`jaleesbench/`, `jaleesweights/`, `quranquote/`), no root project; `jaleesweights` depends on `jaleesbench` **editable** — the benchmark resolves its data and credential paths from its own installed location.
- The main run (`jaleesbench/results/`) and JaleesWeights reference data (`jaleesweights/data/reference/`) are gitignored, installed by `jaleesweights.fetch_data`, and read-only: new outputs go to `jaleesweights/data/runs/<name>/`.
- One `.env` parser: `jaleesbench.collect.load_env(required=..., gemini=...)`; values are literal. JaleesWeights commands ask only for the keys they use.
- Every paid step prints a preflight and stops on `--dry-run`; collection and judging are resume-safe by key.

## Map of arch.md (consult when…)
- Repository shape — consult when adding a project, a dependency between projects, or a top-level folder.
- Where data lives — consult when a step reads or writes benchmark results or reference data.
- Paths and credentials — consult when a path or key lookup behaves differently installed vs in the clone.
- Paid steps — consult when adding a command that spends money or rents hardware.
