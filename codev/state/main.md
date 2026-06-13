# taqwabench — main architect state
*Captured 2026-06-13 evening. Supersedes prior state.*

## FIRST ACTIONS after /clear
1. Read memory MEMORY.md (`~/.claude/projects/-Users-mwk-Development-fftn-taqwabench/memory/`):
   key ones — **no-validation-machinery** (don't add proof apparatus unprompted),
   **concurrent-experiment-harnesses** (default to worker pools, not serial),
   md2pdf preference, Blackbox API.
2. Two background jobs may still be live — check before acting:
   - modified-Ansari collection (was 2428/2520 at capture): `wc -l <
     /Users/mwk/Development/cluesmith/ansari4/ansari-multisage/tmp/ansari_mod_done.jsonl`
   - if done, NEXT STEP = judge it (see §Ansari experiment).

## Project: Track B — JaleesBench (Track A VirtueBench×Nemotron dormant/published)

"Is the AI a righteous companion (al-jalīs al-ṣāliḥ) to a Muslim user?" — measures
the residue counsel leaves on the user, not knowledge/professed values. Full design:
`docs/jaleesbench-design.md` (v0.3, +pdf).

## FULL RUN COMPLETE (8 subjects)
140 probes × 6 pressures × 3 framings × 8 subjects = 20,160 sittings, 80,631 dual
judgments (Opus 4.8 + Gemini 3.1 Pro), total run ~$1,316 (batch judging saved
~$934). **Scores reported on −1…+1 scale** (bands Burns −1 … Perfume +1; judge emits
−2..2, halved at report). collect.jsonl + judgments.jsonl in jaleesbench/results/.

**Jalees Score (Unstated, after pressure):** ansari +0.48 > gpt-5.5 +0.27 >
claude-sonnet-4-6 +0.22 > glm-5.1 −0.18 > nemotron-3-ultra −0.21 > gemini-3.5-flash
−0.26 > gemma-4-31b −0.34 > qwen3-235b −0.48.
- **Recognition >> instruction**: framing dominates; guided ceiling +0.56..+0.87
  for all EXCEPT qwen3-235b +0.12 (capability gap, not recognition).
- **Ansari layer worth +0.75** over its own base model gemini-3.5-flash (−0.26 on
  identical probes) — the headline.
- **Steadfastness**: ALL cave; worst on RELATIONAL pressures (insistence,
  personal_appeal); false_authority SHARPENS most (qwen the exception).
- Judge agreement 66% exact / 85% within-1 (harder bank than pilot's 73/88).
- 320 polarizing cells (one subject +1 / another −1 on same probe×pressure).

## CITATION METRIC — fully reworked (Waleed pushed hard; 3 bugs fixed)
Final metric = **turn-1 (first response only), temperature-0 LLM detector
(gemini-3.1-flash-lite on Vertex), split by probe Islamic class.** Bugs fixed
along the way: (1) regex counted clock times "1:1"/"9:00" as verses → LLM detector
(`citation.py`, benchmarked 30/30 vs hand labels); (2) Flash-Lite nondeterminism
(92% self-agree) → temperature=0; (3) "turn-1" flag scored BOTH turns →
`asst[0]` only.
**Final numbers (clean=religion-neutral probes, Unstated):** general models 0–4%
(~2% pooled), ansari 97%. Stated framing → everyone 64–98% (citation is a
RECOGNITION response). Data: results/citations_turn1.jsonl (20,160).
Probe Islamic class persisted in probes.json field "islamic": 42 intrinsic /
40 leaky / 58 clean (classification in tmp/probe_klass.json from Opus pass).

## ANSARI STEADFASTNESS EXPERIMENT (benchmark-driven fix)
Goal: fix Ansari caving under relational pressure. Added optional
`systemPromptOverride` param to `runFacilitator` in ansari-multisage
(lib/facilitator/agent.ts — UNCOMMITTED in that repo; ask Waleed before committing).
Anti-pressure addendum: `ansari-multisage/tmp/tune_addendum.txt` (change HOW not
WHAT, don't retract under insistence/appeal/secularize).
- **Held-out validation (10 fresh probes, paired, judged): steadfastness −0.42 →
  +0.02** (insistence −0.45→+0.02, personal_appeal −0.52→0.00, secularize
  −0.28→+0.03), turn-1 quality preserved. Control arm tracks full-bank baseline.
  Saved: results/ansari_prompt_mod.json (drives report §11).
- **Full-bank modified run IN PROGRESS** (subject label "ansari-steadfast",
  2,520 cells, ADDITIVE — separate files). Collection ~2428/2520 at capture
  (`tmp/collect_ansari_mod.mts`, restart-loop b/c Vertex HTTP2 crashes; has
  unhandledRejection guard). When done: merge tmp/ansari_mod_done.jsonl →
  results/collect_ansari_mod.jsonl (subject ansari-steadfast) then JUDGE into
  results/judgments_ansari_mod.jsonl (separate file!), compute full-bank
  steadfastness, update results/ansari_prompt_mod.json "full_bank" + regenerate
  report §11. Waleed said "deploying this amendment now" = HIS action (don't deploy).

## INFRA CHANGES THIS SESSION
- **Gemini → Vertex AI** (collect subject gemini-3.5-flash + both judging-Gemini
  + citation detector). `gemini_client()` in collect.py; key gitignored at
  `.vertex-sa.json` (project agentset-491018, location=global). GEMINI_API_KEY no
  longer required. Vertex has NO file-batch API → Gemini judged live, Opus batched.
- Ansari via OpenAI-compat route (spec 19, leaderboard bearer = no rate limit).
- 6 subjects added across session: gemini-3.5-flash, gemma-4-31b (Friendli),
  qwen3-235b (Friendli), glm-5.1 (Friendli), nemotron-3-ultra (Blackbox).
  Prices in score.py (verified). Friendli/Blackbox keys in cluesmith/shannon/.env.

## REPORT (docs/jaleesbench-report.{html,pdf}; HTML canonical, PDF via Playwright, NO md)
Sections: 1 scorecard (+turn-1 citation rows) · 2 framing STAIRCASE (value→value
with Δ in context) · 3 steadfastness/pressure · 4 by-probe · 5 techniques ·
6 citation (turn-1, clean/leaky/intrinsic × framing) · 7 subject findings ·
8 judge agreement · 9 cost · 10 polarizing scenarios (FULL transcripts, no clip) ·
11 Ansari prompt modification (held-out table; full-bank pending) · 12 caveats
(incl. default-config/thinking limitation). Commentary in results/commentary.json
(16 slots incl. ansari_mod). `uv run jaleesbench report` builds HTML only.

## arXiv PAPER (docs/paper/jaleesbench-paper.{md,pdf})
Authors: **Waleed Kadous, Ben Olsen, Tim Hwang.** Drafted in MARKDOWN (Waleed hates
LaTeX) → convert to LaTeX for submission (PENDING, his call on timing). Content
complete EXCEPT: §6 full-bank Ansari confirmation (pending judging), references→BibTeX.
Has: abstract, intro, related work (IslamicMMLU/LegalBench/IslamTrust/VirtueBench/
EdifyBench), method, 8-system results, §5.5 citation table (corrected), §6 Ansari
case study, limitations, Appendix A polarizing example (JLS-006 ansari +1 vs gpt −1).

## OPEN DECISIONS (Waleed's calls)
1. **De-islamization / intrinsic probes**: 42 intrinsic (21 prayer/salah), 40
   universal-leaky, 58 clean. Asked "how many intrinsic" (=42), considered removing
   — NOT DECIDED. Options presented (AskUserQuestion rejected/he was thinking):
   keep-as-tagged-subset (recommended) / drop-niche-keep-spiritual / remove-all-42.
   De-islamize the 40 leaky regardless. Turn-1 metric already mitigates much of it.
2. **Thinking**: NOT enabled/standardized anywhere (default config). Documented as
   limitation. Open: (a) test thinking-ON judges on a sample → does agreement beat
   66/85? worth doing before paper locks; (b) leave subjects "as deployed" (rec) vs
   thinking-standardized re-run.
3. LaTeX conversion of paper; BibTeX refs.
4. Scholar review (precedes any public/normative claims). taqwabench repo public?

## CONVENTIONS (respect)
Scores −1…+1. md→PDF local md2pdf only. Concurrent harnesses (worker pools), each
job try/catch skip-and-continue. Don't add validation machinery unprompted. Git
explicit paths, no attribution lines. ADDITIVE experiments — never overwrite
existing collect/judgments files (modified-Ansari uses separate files + subject label).
