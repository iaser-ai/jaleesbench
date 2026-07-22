# JaleesBench — main architect state
*Consolidated 2026-07-22 (stale superseded sections pruned; git history has the full trail).*

## FIRST ACTIONS after /clear
1. Read MEMORY.md (`~/.claude/projects/-Users-mwk-Development-fftn-taqwabench/memory/`): `jaleesbench-ten-subjects`, `tinker-inkling-api`, `dont-bake-my-recommendations`, `codev-protocol-checks-npm-vs-uv`, `jaleesbench-paper`, `no-validation-machinery`.
2. Repo PUBLIC: `origin` = git@github.com:iaser-ai/jaleesbench.git. Everything below is committed and pushed unless marked otherwise. Untracked-by-design: `docs/paper/jaleesbench-arxiv.tar.gz` (STALE Jun-27 8-subject bundle — regenerate before arXiv).
3. Check `afx status` for live builders; **builder-air-11 may be running** (issue #11, bank v4) — see V4 below.

## CURRENT STATE (2026-07-22)
- **Paper**: 23pp clean build (`xelatex → bibtex → xelatex ×2`), through `26a8db6`. Contains: 10-subject main results; §5.12 Sonnet 4.6-vs-5 ("Same score, different character", five-point + diagnostic-instrument coda); §7 **Arabic replication** (+abstract sentence); audit fixes (cluster arithmetic 139+JLS-140, re-judge-overlay disclosure w/ pre-overlay 67.5/85.1, COI includes Ansari, hearts "adapted from" relabel, demographic-skew limitation); Table 2 regenerated for v3 retag (all nine general models 0% clean-class citation; Ansari 98/95/96).
- **EN main run**: 10 subjects, 25,200 sittings / 100,800 judgments, fully dual-judged. Unstated: ansari +0.48 > gpt-5.5 +0.28 ≈ sonnet-5 +0.27 ≈ inkling +0.25 ≈ sonnet-4-6 +0.23 ≫ glm −0.18 … qwen −0.48.
- **Arabic**: COMPLETE — 22,672 sittings, 90,686/90,688 judgments (2 cells unjudgeable by Gemini: glm|JLS-074|false_authority|guided, Opus-only), citations detected (results/citations_ar_turn1.jsonl 22,671, tmp/detect_ar.py). Analyses: tmp/analysis_ar.py + analysis_ar2.py (+ saved outputs). Headlines: ranking replicates ρ=0.83, top-3 n.s.; **Arabic = implicit faith signal** (clean-class citation 0% EN vs 1–12% AR — F055 confirmed); steadfastness worse pool-wide, false-authority checking vanishes; citation cultures diverge (open/mid cite more in AR, GPT/Sonnet less); AR polarizing 792 vs EN 691 (8-common); judge gaps narrow in AR, opus self-judge gap +0.27 = ordinary family-tie size. All in paper §7.
- **Results browser**: https://iaser-ai.github.io/jaleesbench/ — 10-subject v3 data + leaderboard live (export committed `75a635e`).
- **Multibench audit**: Buckets A+B fully executed (PR #8 issue #7; PR #10 issue #9 — merged, regenerated, issues closed, worktrees removed). Corrections sent to multibench architect (F048 inverted, F016 wrong fix, F030 refuted). Bucket C: all decided by Waleed 07-20/22 — see V4.

## V4 IN FLIGHT (issue #11, builder-air-11, strict AIR, spawned 2026-07-22)
- Package (Waleed-approved wording; full text in issue #11): register+wasaṭiyya tags on all 140 probes (126/9/3/2; 107/28/5 — from 3-agent pass, converges with audit ≈101/30/8); C1a five RS-relabels; C3 JLS-100 anchored rewrite; C4 six correctives realigned to RS-text-only policy (JLS-103 gets Nawawī bab-261 prose anchor — bab has n_hadith:0; Umm Kulthūm = Muslim 2605, Nawawī himself records the tawriya dispute, verified via Ansari); ḍaʿīf disclosure for bab 211 (n_hadith:1 — keep RS 1159 per Waleed's "RS text = judging criteria" policy); README neutrality contract; GUIDE_V4_ADDENDUM + REGISTER_OVERLAY shipped DORMANT (activate next run — avoids invalidating Guided comparisons). 13 audit-proposed scenarios NOT adopted.
- **Post-merge (architect)**: RE-JUDGE the six C4 probes (Waleed approved): EN 10 subjects + AR 8+1, those probes' cells only (Opus batch + gemini-only live + sweep; NEVER plain judge while a batch is in flight); then regenerate paper_stats/Table-2-adjacent numbers/web export; add wasaṭiyya-tilt disclosure to paper (note the inversion: excess probes outscore laxity probes in both languages — AR +0.21/−0.11, EN +0.15/−0.14; grief = worst register both languages). Builder's pr gate goes to Waleed.

## FINDINGS PARKED FOR FUTURE PAPER USE (computed, not yet in paper)
- Wasaṭiyya/register axis numbers (above) — publishable once v4 tags land.
- Sonnet compare details in tmp/sonnet_compare.py output; AR movers: worse on social-speech (backbiting/toast/eulogy), better on ritual (graves/mourning).
- Opus-4-8 AR-only: +0.57 both-judges / +0.44 gemini-only, best steadfastness (−0.01); self-judge caveat mandatory.

## OPEN / WALEED'S CALLS
- Scholar review still precedes normative claims (unchanged; C4 rewrites deliberately defer disputed scope). Opus EN-backfill deferred. arXiv bundle regeneration when he's ready to submit.

## CONVENTIONS / HARD RULES
- Public repo — mind what's published. Scores −1…+1. ADDITIVE experiments (per-study files in results/, drivers in tmp/). Git: explicit paths, no attribution lines. Paper commits = architect direct with Waleed's go; ALL other repo changes via builder PRs.
- **NEVER auto-approve porch gates** — notifications to Waleed; he authorizes. `afx cleanup` / worktree removal only on Waleed's go.
- **Don't bake recommendations as decisions; don't over-build.** UI work: screenshot to verify.
- Judging: NEVER plain `judge`/judge_all-both-judges while an Opus batch is in flight (double-judges). Arabic judge/collect need explicit collect_path/out_path (or post-#10, `--lang ar`).
- Keys: repo-root `.env` is the single source (consolidated 07-20 after PR #10; GEMINI/FRIENDLI/BLACKBOX/LEADERBOARD copied in; `.vertex-sa.json` at repo root).
