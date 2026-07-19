# JaleesBench — main architect state
*Captured 2026-06-18; updated 2026-07-17 (second session). Waleed gave go on all open items: **paper committed+pushed (7649d8b)**, **air-5 cleaned up** (terminal killed; worktree preserved — only afx scaffolding uncommitted; `git worktree remove .builders/air-5` + `git branch -d builder/air-5` await explicit permission per scar rule), **bugfix-7 builder spawned** (strict; gates go to Waleed), **Arabic judging LAUNCHED** (see below), **Sonnet 4.6-vs-5 deep dive done** (tmp/sonnet_compare.py) **and in the paper** (§ "Same score, different character", bc42e00, Waleed-approved; 22pp clean build).*

## ARABIC JUDGING — COMPLETE 2026-07-19
- **judgments_ar.jsonl: 90,686 / 90,688** (99.998%). Opus batches 44,866 (5 batches, all done, logs tmp/submit_ar.log + tmp/collect_ar_batches.log); Gemini live 45,133 over ~2 days (tmp/judge_ar_gemini.log); sweep picked up 679 stragglers (tmp/judge_ar_sweep.log).
- **2 cells permanently pending**: gemini-3.1-pro-preview × glm-5.1|JLS-074|false_authority|guided (turn1+full) — judge deterministically emits malformed JSON (garbled Chinese) after repeated retries. Opus judgments for that sitting exist. Left pending per fail-fast; note in any Arabic analysis.
- results/ is gitignored — raw Arabic data local only. Arabic = original 8+1 subjects (no inkling/sonnet-5).
- **AR-vs-EN analysis DONE** (tmp/analysis_ar.py, output tmp/analysis_ar_output.txt): top-3 replicate (ansari +0.45 / gpt +0.31 / sonnet-4-6 +0.27, diffs n.s.; Spearman ρ=0.83); recognition-dominates-instruction replicates but instruction gaps SHRINK in AR (guided ceilings lower: sonnet −0.12*, glm −0.19*); steadfastness uniformly worse in AR (7/8 subjects; false-authority checking vanishes: +0.03 n.s. vs +0.08* EN); glm drops 4th→7th (−0.08*..−0.19*), nemotron/gemma relatively better (+0.14*/+0.17* unstated); judge agreement holds (68/86 vs 66/85); opus-4-8 AR-only +0.57 both-judges vs +0.44 gemini-only (self-judge bias ≈ +0.13 — caveat any use). Paper section = Waleed's call.

## SONNET 4.6 vs 5 DEEP DIVE (tmp/sonnet_compare.py, paired probe bootstrap)
- Means statistically tied (unstated diff +0.038 [−0.010,+0.086]); real differences are in SHAPE:
- **Polarization**: sonnet-5 unstated post-pressure bands: 19.5% Burns / 44.7% Perfume vs 4.6's 13.7% / 35.9% — commits harder both directions. Turn-1 stance spread std 1.10 vs 0.85; corr(turn1,post) 0.90 vs 0.84; all-6-pressures-same-sign probes 56 vs 49. Divergent probes are whole-scenario flips, not pressure-specific.
- **Significant**: false_authority +0.155*, good_cause +0.095*, steadfastness-under-false-authority diff-of-diffs +0.163*, turn-1 stated +0.060*, stated-intrinsic citation +0.194* (70% vs 51%). Borderline regression: personal_appeal −0.096 [−0.193, 0.000].

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

## MULTIBENCH AUDIT TRIAGE (2026-07-19) — verified vs current repo, AWAITING WALEED
Multibench architect flagged two ultracode audits of JaleesBench (docs/analysis/ in faithfamilytechnologynetwork/multibench; local copy in scratchpad/mb). I verified all mechanically checkable claims via an 8-agent workflow (full verdicts: scratchpad task wnrt7h1s3 output / this section).
- **Bucket A (confirmed, mechanical, builder-ready on go):** paper 143−4≠140 arithmetic (real story: 139 cluster probes + JLS-140 off-map bab 370 — audit's "three excluded" fix is WRONG); COI paragraph omits Ansari-Gemini tie (tex:688-695); judge-agreement overlay (judgments_v2, 141 pairs) undisclosed in paper; tracked results/commentary.json is stale June artifact contradicting paper (320 vs 751 polarizing, 8 vs 10 subjects); README band labels Smoke/Neutral→Sparks/Inert + missing apps/ row; CLI lacks --turn1 (public report Table 2 renders blank); dead regex detector in score.py; judge_all exits 0 on partial failure; load_env hardcodes 3 author-machine paths; opus-4-8 still in SUBJECTS vs ten-subject paper; prompts_ar.json gitignored → public Arabic path throws; bootstrap-CI code unpublished (tmp/ gitignored) vs paper's "ships with artifact" claim; probes_ar.json no version key; design-doc stale (139/pilot/−2..+2); guide.md "exact text" not byte-identical.
- **Bucket B (confirmed, editorial/data):** 4 clean-tag violations (JLS-037 Jummah, 054 tafsir, 096 janazah, 138 nikah in turn1) — retag or reword, shifts Table 2 clean class; HEARTS enum ≠ Ghazali munjiyāt (drops 3, splits 2, bare patience×14) while paper says "al-Ghazālī's stations" — relabel (cheap) vs re-tag (expensive); demographics: 20:4 MALE-asker skew (audit had direction INVERTED), 0 converts, named chars all male Arab/South-Asian — disclose in Limitations at minimum.
- **Bucket C (scholar-gated):** 5 probes cite RS numbers as Sahih numbers (JLS-069/074/105/131/132, premises confirmed) + JLS-091 ḍaʿīf anchor + JLS-100 hard-quote; fiqh-neutrality corrective cluster (JLS-103 confirmed as ONLY probe with no RS anchor; 133/106/137/109/079 content); register/wasaṭiyya axes + 13 proposed scenarios = design decisions.
- **Refuted/stale:** F030 (judge failures print loudly, not silent); F048 direction inverted; F021 stale (10-subject run fully dual-judged, 50,400×2 verified); commentary "flipped ranking" sub-claim false. NOTHING adopted/edited — all Waleed's call; scholar gate applies to Bucket C.

## CONVENTIONS / HARD RULES
- Public repo — mind what's published. Scores −1…+1. ADDITIVE experiments (per-study files). No unprompted validation machinery. Git: explicit paths, no attribution lines.
- **NEVER auto-approve porch gates** — notifications to Waleed; he authorizes (as he did for PR #6's pr gate).
- **Don't bake recommendations as decisions; don't over-build.** UI work: screenshot to verify. `afx cleanup` only on Waleed's go.
