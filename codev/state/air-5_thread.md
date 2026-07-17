# air-5 — issue #5: jaleesbrowser built-in leaderboard view

## 2026-07-17 — Implement phase start

Explored the app + data. Key findings that shaped the design:

- `public/data/index.json` already ships a full `scores` tensor
  (subject × item × pressure × framing × scope, display scale). Verified
  numerically: mean-of-cell-means from the tensor reproduces the exporter's
  `subjects[].overall` **exactly** (all 9 subjects, both scopes, 4dp). The
  exporter rescales native −2..+2 bands by `SCORE_SCALE = 0.5`, so everything
  is already on the paper's −1..+1 scale. → **No exporter change, no contract
  bump needed**; per-framing aggregates are derivable client-side.
- `guided.ts` establishes the "computed IN-APP from the score blob (no
  re-export)" precedent; leaderboard follows it.
- `urlstate.ts` already has a `view` field ("detail" | "compare" — compare is
  currently unrendered). Adding "leaderboard" is the natural wiring.
- Genericity constraint: the viewer must contain no JaleesBench-specific
  strings. Resolution: breakdown axis = the condition axis with the fewest
  values (framing, 3), canonical rank = its first declared value at the
  default (post) scope → Unstated post-pressure, the paper's ordering —
  all derived from the data's declared order.

Plan: `src/leaderboard.ts` (pure compute + canonical ordering),
`src/components/Leaderboard.tsx` (sortable table, row → detail view),
view nav in `App.tsx` (hidden when the index has no scores), tests for all.

## Implementation done

- `src/leaderboard.ts`: pure compute (means from the score tensor, canonical
  ordering by first breakdown-axis value at the post scope) + `breakdownAxis`
  (fewest-values rule → framing).
- `src/components/Leaderboard.tsx`: sortable table; Rank column pinned to the
  canonical order; model click → that subject's detail view.
- `App.tsx`: Browse/Leaderboard nav (hidden when the index has no score blob),
  pickers/presets hidden on the leaderboard.
- `urlstate.ts`: "leaderboard" view; encoded canonically as `?view=leaderboard`.
- 81/81 tests pass (15 new across 4 files), `tsc` clean, vite build clean.
- Real-data sanity: computed Unstated post-pressure ranking puts ansari first
  (+0.480), qwen3-235b last (−0.476) — matches the paper's ordering.
