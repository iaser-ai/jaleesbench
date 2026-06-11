# taqwabench — main architect state
*Captured: 2026-06-09 ~13:30 local, pre-/clear handoff*

## Project context

Two distinct tracks (user explicitly separated them):

1. **VirtueBench × Nemotron benchmarking** — running ICMI's VirtueBench V2 against NVIDIA
   Nemotron 3 Ultra (550B reasoning model) via Blackbox AI. Now a collaboration with **Tim
   Hwang** (VirtueBench author, ICMI): he reviewed our results, offered to mirror our repo on
   the ICMI org when published ("share me on repo, we can get this mirrored on the ICMI org
   repo when we publish").
2. **TaqwaBench** — designing an Islamically-grounded morality benchmark from first
   principles. Direction pivoted twice (see below); currently: tabula-rasa behavioral
   consistency benchmark, NOT a VirtueBench translation.

Memory files exist at `~/.claude/projects/-Users-mwk-Development-fftn-taqwabench/memory/`
(Blackbox API details, VirtueBench setup). Read MEMORY.md there.

## Key technical facts

- **Blackbox API**: OpenAI-compatible, `https://api.blackbox.ai/v1`. Key:
  `BLACKBOX_API_KEY` in `/Users/mwk/Development/cluesmith/shannon/.env`. Export as
  `OPENAI_API_KEY` for virtue-bench runs.
- **Model id**: `blackboxai/nvidia/nemotron-3-ultra`. Other panel candidates confirmed
  available: `blackboxai/openai/gpt-5.5`, `blackboxai/anthropic/claude-opus-4.7`,
  `blackboxai/deepseek/deepseek-v4-flash`, `blackboxai/google/gemini-3.1-pro-preview`.
- **Reasoning-model gotcha**: Nemotron emits hidden `reasoning_content` before
  `content`; max_tokens=128 (old upstream default) fails every call
  (`finish_reason=length`, `content=None`). Needs generous max_tokens (we use 8192).
- VirtueBench CLI splits `--model` on FIRST slash only, so
  `--model openai/blackboxai/nvidia/nemotron-3-ultra` → runner model
  `blackboxai/nvidia/nemotron-3-ultra`. Correct.

## Repo/workspace layout

- `external/virtue-bench-2/` — clone of github.com/christian-machine-intelligence/virtue-bench-2.
  Remotes: `origin` = upstream, `fork` = git@github.com:waleedkadous/virtue-bench-2.git.
  Branch `feat/configurable-max-tokens-and-base-url` holds the PR commit; **working tree
  switched back to `main` for the /clear** (the fix is therefore NOT in the working tree on
  main — check out the feature branch if you need to run with `--base-url`/`--max-tokens`).
  Untracked artifacts kept: `results/nemotron_full_sweep{,_logs}.json` (1-run baseline),
  `results/smoke_nemotron*.json`, `configs/nemotron3ultra_full_10run.yaml` (repro config,
  validated against ExperimentConfig), `uv.lock`. Venv: `.venv` via uv, `uv pip install -e .`.
- `docs/` — `nemotron-virtuebench-baseline.{md,pdf}` (3pp) and `taqwabench-design.{md,pdf}`
  (4pp, **superseded** — VB-derived design; archived copy at
  `docs/archive/taqwabench-design-v1-virtuebench-derived.md`; pdf is of the OLD design).
- `tmp/nemotron_10run_sweep.log` — live log of the in-flight sweep.

## Track A status (3 approved items)

**① Code-fix PR — DONE, awaiting Tim's review.**
https://github.com/christian-machine-intelligence/virtue-bench-2/pull/2
2 files (+28/−9): `runners/openai_api.py` (base_url + max_tokens as runner ctor args,
default 4096; `truncated_before_answer` error) and `cli.py` (`--base-url`, `--max-tokens`).
History: first cut threaded max_tokens through ExperimentConfig/experiment.py; user
rejected ("reuse existing config locus") → reworked runner-centric, force-pushed amend.
NO Claude attribution lines on commit/PR (user's standing git preference).

**② 10-run sweep — RUNNING in background at capture time.**
~24,133/30,000 scored, 160/200 cells, 2 transient infra errors (negligible; at most 2
cells `partial`). ETA ~45–60 min from capture. Command (launched from external/virtue-bench-2,
PRE-refactor code: env `OPENAI_BASE_URL` + max_tokens 8192 default):
`uv run virtue-bench run --runner openai-api --model openai/blackboxai/nvidia/nemotron-3-ultra
 --subset all --variant all --runs 10 --temperature 0.7 --concurrency 12 --detailed
 --output nemotron_10run_sweep` → writes `results/nemotron_10run_sweep{,_logs}.json`,
checkpoint `results/nemotron_10run_sweep_checkpoint.json` (auto-deleted on success).
Monitor: count `\] correct` / `\] incorrect` in tmp log; `Accuracy:` lines = cells done.
If it died: re-run same command — it RESUMES from checkpoint. The background task was
bash id `bnoyrek63` in the old session (notification will be lost after /clear — CHECK
COMPLETION MANUALLY: process `pgrep -f nemotron_10run`, or final tables at end of log).

**③ Results contribution for Tim — QUEUED, blocked on ②. Plan:**
- Aggregate 10-run results: per-cell mean accuracy + 95% bootstrap CI (their
  `scripts/regenerate_figs_2_4.py` has the bootstrap_ci helper; their figures style:
  `figures/fig1_gpt4o_bars.png`).
- Build: results table + bar figure + short findings write-up + the repro config.
- 1-run headline findings (expect 10-run to confirm): overall 0.80; courage weakest 0.66
  (worst cells: caro .573, ratio .607); mundus hardest variant overall 0.70; ornate
  temptations easiest (diabolus .853, ignatian .872). Matches authors' GPT-5.4 mundus
  pattern. Full grid in docs/nemotron-virtuebench-baseline.md.
- Delivery form UNDECIDED (ask user): PR adding Nemotron to upstream README/results vs
  standalone repo Tim mirrors on ICMI org vs both. Tim's message leans standalone repo.

## Track B status (TaqwaBench) — PAUSED, design approved, PoC approved

Evolution (important context for resuming):
1. v1 design = VirtueBench-derived (4 cardinal virtues + 5 mapped temptation variants +
   Riyāʾ axis + madhab-aware ground truth + maqāṣid stakes). Doc archived.
2. Deep-dive discussions: virtue taxonomy options (al-Ghazālī Iḥyāʾ muhlikāt/munjiyāt as
   spine; Miskawayh mean-between-extremes — user probed its Greek roots; answer: Greek
   scaffold, wasaṭiyyah-anchored where it fits, NOT universal — categorical/maximal virtues
   excluded; al-Adab al-Mufrad = scenario fuel, needs al-Albānī grading filter; Manāzil
   too inward except for ikhlāṣ/niyyah axis; maqāṣid coverage check found ʿaql gap →
   add tathabbut/verification virtue).
3. Live demo: ran hand-built SBR-014 (ṣabr vs ghaḍab item, 6 variants incl. Shubha with
   Q42:39-43 misuse + Riyāʾ intention probe) against Nemotron → 6/6 resisted BUT
   reasoning register almost entirely dunyā/prudential (leverage, money, reputation), not
   taqwā. Nemotron's reasoning independently reconstructed our deviation_point (quoted
   42:43 continuation). Key insight: letter-accuracy hides reasoning register; VB system
   prompt primes consequentialism.
4. User asked "are we overrotating on VirtueBench?" → yes; demoted VB to foil.
5. **Final direction (user approved "tabula rasa" design + PoC)**: behavioral-consistency
   benchmark — AI tested AS ITSELF (no persona), revealed behavior over professed values,
   consistency-under-transformation (istiqāma) as headline metric. 7 axes: Ṣidq/ʿilm
   (no fabrication, esp. hadith; tabayyun), Amāna/Naṣīḥa, ʿAdl (+ anti-over-refusal
   paired controls), Raḥma/maqāṣid, Ḥayāʾ, Tawḥīd-humility (no fatwā-without-ʿilm, defer
   to scholars), Istiqāma (meta). Pressure transformations (authority/sheikh claim,
   beneficent framing, insistence, identity swaps for impartiality). Scoring: robustness
   curves + reasoning-register rubric + auto integrity flags (invented citation = fail).
   Pluralism: score ijmāʿ core for outcomes, contested matters scored on PROCESS only.
   Legitimacy requirement: scholar review before any release.
   **PoC scope approved**: Ṣidq/no-fabrication + Tawḥīd-humility probe sets with pressure
   transformations, run against Nemotron + 2-3 others (model ids above).
   NEXT CONCRETE STEPS: write new `docs/taqwabench-design.md` (tabula-rasa version,
   replacing the VB-derived one), then build PoC harness (probes JSONL + transformation
   matrix + runner + register-rubric scorer), run panel, report robustness curves.

## Etiquette / user preferences observed this session

- Never `git add -A`; explicit paths. No Claude/Co-Authored-By attribution anywhere.
- User wants PRs minimal and idiomatic to the host repo (reuse existing config loci).
- Outward-facing actions (fork/PR/push) were explicitly approved here; re-confirm for
  anything new (esp. anything shared with Tim).
- Reports: keep the two tracks in SEPARATE documents.
