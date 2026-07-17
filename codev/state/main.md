# JaleesBench — main architect state
*Captured 2026-06-18; updated 2026-07-17 (end of Inkling/Sonnet-5 session). This session: **Inkling + Claude Sonnet 5 added as subjects 9 & 10** (full runs + dual judging, committed + pushed), **paper updated to 10 subjects** (uncommitted — Waleed to review), **leaderboard built into jaleesbrowser** (PR #6 merged; issue #5 closed; air-5 worktree awaits cleanup go).*

## FIRST ACTIONS after /clear
1. Read MEMORY.md (`~/.claude/projects/-Users-mwk-Development-fftn-taqwabench/memory/`): `jaleesbench-ten-subjects` + `tinker-inkling-api` (new), `dont-bake-my-recommendations`, `codev-protocol-checks-npm-vs-uv`, jaleesbench-paper, no-validation-machinery.
2. Repo PUBLIC: `origin` = git@github.com:iaser-ai/jaleesbench.git. Local `main` pushed through `b6ba86e` (Sonnet 5 data).
3. **Uncommitted, intentional:** `docs/paper/*` (10-subject update THIS session layered on pre-existing uncommitted arXiv-prep edits — tex, figures, references.bib, `jaleesbench-arxiv.tar.gz`; commit only on Waleed's review/go), `jaleesbench/tmp/*.py` subject-list updates, this file.

## THIS SESSION (2026-07-16/17)
- **Inkling** (Thinking Machines, 975B MoE open-weights, released 7/15): new `tinker` provider (OpenAI-compatible; TINKER_API_KEY in repo .env; account-wide in-flight cap → Ansari-style patient retries in collect.py, concurrency 40 sweet spot). 2,520 sittings ($64) + 10,080 dual judgments. See memory `tinker-inkling-api`.
- **Claude Sonnet 5**: subject 10 (~$86 collection at intro pricing $2/$10 through 2026-08-31; reasons by default — adaptive thinking when `thinking` omitted).
- **Results (Unstated, post-pressure, −1..+1):** ansari +0.48 > gpt-5.5 +0.28 ≈ sonnet-5 +0.27 ≈ inkling +0.25 ≈ sonnet-4-6 +0.23 (top-4 tie) ≫ glm −0.18 … qwen −0.48. Inkling: best Guided ceiling +0.91, near-zero steadfastness drop, 35% unstated citation. Sonnet-5: biggest false-authority gain +0.30.
- **Judging protocol per new subject** (memory `jaleesbench-ten-subjects` has the full recipe): Opus batch + Gemini-only live (`judge_all(judges={...})` — NEVER plain `judge` while an Opus batch is in flight) + sweep; then detect-citations (BOTH default and `turn1=True`), report, export-web, commit data.
- **Paper**: regenerated paper_stats/analysis_round/make_figures for 10 subjects; tables + prose updated (judge agreement 67/85 over 50,400; polarizing 691→751; love-and-contentment claim softened to "floor for six of ten"; reasoning-mode section reworded — sonnet-5 + inkling reason by default; fig_steadfastness now pins Ansari above Flash deliberately). Clean 21-page build. Cost appendix ≈$1,800 as-run.
- **Ansari MultiSage architect** (cross-workspace) asked about Inkling as a Gemini-replacement for their facilitator — sent endpoint/pricing/caveats (slow via Tinker ~35-40s/completion; pointed at Fireworks/Together servings), pointed at key PATH (didn't paste secret), flagged shared in-flight cap; suggested own key for prod benchmarking.

## LEADERBOARD (issue #5 / PR #6) — MERGED (64f5d8a), issue #5 CLOSED
- `builder-air-5` (strict AIR): leaderboard view in jaleesbrowser, computed in-app from the scores tensor (no exporter change). 3-way CMAP: gemini+claude APPROVE, codex REQUEST_CHANGES → shard-fetch gating fix applied (9c59b23). Waleed approved the pr gate 2026-07-17; merged 09:40Z; local `main` pulled; Pages will auto-deploy with the 10-subject data already in `public/data`.
- **`.builders/air-5` worktree still present** — builder says ready for cleanup; `afx cleanup -p 5` **only on Waleed's go**.
- **Issue #7** (follow-up, open): stale `test_presets_polarizing_present_and_empty_omitted` (exporter moved to turn-1 ranking in 986165e; fixture degenerate) + zero-spread `X vs X` guard question. Skip-with-annotation currently on main via PR #6.

## RESULTS BROWSER — LIVE
- https://iaser-ai.github.io/jaleesbench/ — Pages auto-deploys on push to `main`. Data now **10 subjects** (`export-web --out apps/jaleesbrowser/public/data`, committed). Single-model view default; 3 guided lists in-app; leaderboard arriving with PR #6.
- Front-end verify: headless Chrome screenshot (can't see rendered UIs). Tests: `npm test` in apps/jaleesbrowser + `uv run --directory jaleesbench pytest -q` (one skip: issue #7).

## PAPER (docs/paper/) — 10-subject update done, UNCOMMITTED
- `.tex` canonical; build `xelatex → bibtex → xelatex ×2` (or latexmk -xelatex). 100,800 judgments / 25,200 sittings. Pre-session working-tree changes (arXiv prep?) are mixed with this session's — review before committing.

## ARABIC REPLICATION — collection DONE, awaits judging "go"
- Unchanged: `collect_ar.jsonl` 22,672/22,680; on "go": `submit(lang="ar")` → Gemini live → `collect(lang="ar")`. NOTE: Arabic ran with the ORIGINAL 8+1 subjects (incl. opus subject) — no inkling/sonnet-5 there.

## OPEN / WALEED'S CALLS
- Commit the paper (mixed with prior uncommitted edits). Arabic judging "go". Issue #7 fix. Opus EN-backfill deferred. Scholar review precedes normative claims. Ansari-MultiSage may want a second Tinker key from Waleed.

## CONVENTIONS / HARD RULES
- Public repo — mind what's published. Scores −1…+1. ADDITIVE experiments (per-study files). No unprompted validation machinery. Git: explicit paths, no attribution lines.
- **NEVER auto-approve porch gates** — notifications to Waleed; he authorizes (as he did for PR #6's pr gate).
- **Don't bake recommendations as decisions; don't over-build.** UI work: screenshot to verify. `afx cleanup` only on Waleed's go.
