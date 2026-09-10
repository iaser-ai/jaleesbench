# task-ViBt — Refresh jaleesbrowser export to the 13-subject grid

## Scope
Data refresh only: re-run `jaleesbench export-web` against the main checkout's raw
results (`/Users/mwk/Development/fftn/taqwabench/jaleesbench/results/`, gitignored,
read by absolute path) and commit the regenerated `apps/jaleesbrowser/public/data/`.
No product-logic changes. If the exporter or the app breaks on 13 subjects or on
fanar-sadiq's missing stated/guided framings: stop and report, do not patch around it.

## Orientation (2026-09-10)
- No porch project for this task id; plain task, thread + PR only.
- Task text says `results/` at the main checkout root — it actually lives at
  `jaleesbench/results/` (only paper_stats.json + mini_* are tracked).
- Current committed export: 12 subjects (missing k2-horizon). paper_stats.json
  jalees_by_framing has 13 subjects; fanar-sadiq has `unstated` only.
- Exporter derives subjects/framings from the data present, fills `null` for absent
  cells in the score matrix — so missing framings should be tolerated by design.

## Export + verification (2026-09-10)
Ran `uv run jaleesbench export-web --results-path <main>/jaleesbench/results --out ../apps/jaleesbrowser/public/data`
from the worktree's `jaleesbench/`. Exit 0; 140 shards + index.json rewritten (all 141
files change because k2-horizon cells are added to every probe). 90.7 MB on disk.

Verified (script over index.json's `scores` blob AND the app's own `computeLeaderboard`
run via vite-node on the real index — both agree):
- 13 subjects: ansari, claude-sonnet-4-6, claude-sonnet-5, fanar, fanar-sadiq,
  gemini-3.5-flash, gemma-4-31b, glm-5.1, gpt-5.5, inkling, k2-horizon,
  nemotron-3-ultra, qwen3-235b.
- Leaderboard order (Unstated post-pressure) == paper_stats.json jalees_by_framing
  unstated order for all 13: ansari +0.484 #1 … fanar-sadiq −0.426 #11,
  k2-horizon −0.448 #12, qwen3-235b −0.476 #13. Point values match to 3 dp.
- fanar-sadiq: unstated 840 cells; stated/guided are `null` in the blob, the
  leaderboard row shows `null` for those two columns, nothing throws.
- Incidental: fanar has 835 unstated / 833 stated cells (not 840) — pre-existing
  gaps in the raw results (see results/collect_fanar_refusals.json), not introduced here.

Checks: `npm test` 15 files / 82 tests pass; `npm run build` (tsc + vite) clean.
No source files touched — data + this thread only.
