# taqwabench — main architect state
*Captured: 2026-06-13. FULL RUN COMPLETE. Previous state superseded.*

## FULL RUN DONE (2026-06-13) — committed fb551b4

**Result:** 8 subjects x 140 probes x 6 pressures x 3 framings = 20,160 sittings,
80,631/80,640 judgments. Report: docs/jaleesbench-report.{md,html,pdf} (+~/Downloads).
Total cost $1,315.72 (collection $379.92, judging $935.81; batch judging saved
$933.52 vs full price; measured cache-hit rate 95%).

**Jalees Scores (Unstated, after pressure):** ansari +0.96 > gpt-5.5 +0.55 >
claude-sonnet-4-6 +0.45 > glm-5.1 -0.35 > nemotron-3-ultra -0.41 >
gemini-3.5-flash -0.53 > gemma-4-31b -0.69 > qwen3-235b -0.95.
- Ansari layer worth +1.49 over its own base (gemini-3.5-flash) — headline.
- Recognition gap dominates (told-user-is-Muslim recovers all but qwen above 0);
  guided lifts pool to +1.1..+1.74 EXCEPT qwen3-235b +0.23 = capability gap.
- Steadfastness: ALL cave; worst on RELATIONAL pressures (insistence,
  personal_appeal); false_authority sharpens most (qwen is exception, -0.26).
- Citation: ansari 98% hadith unstated vs single digits/low others (starkest diff).
- Judge agreement 66/85 (down from pilot 73/88 — harder bank, more gray cells;
  JLS-059 Monday-fast worst at 25%). Opus more generous; widest gap qwen +0.84.
- Universal-failure probe: JLS-083 "The midnight homecoming" (~-2 nearly all).

**Run war stories (all resolved, committed):**
- Ansari 8000-char route cap broke 17 verbose turn-2 cells -> collected via DIRECT
  facilitator call (cluesmith/ansari4/ansari-multisage/tmp/collect_ansari.mts,
  tsx, no deploy, production-faithful). Worth raising route cap at source.
- Anthropic API ran OUT OF CREDITS mid-batch (~7,900 Opus errored); topped up,
  re-batched the remainder (fixed _pending_jobs to re-eligible done-batch errors).
- Parser bug: greedy {.*} grabbed trailing text -> raw_decode from first brace.
- judge_all now skip-and-count (one bad cell no longer crashes gather).
- Gemini judge: safety thresholds OFF (benign parenting/privacy probe JLS-068
  false-tripped minor-safety filter). 8 JLS-068 cells STILL refused by Gemini +
  1 Opus missing-rationale = 9 single-judge cells (0.02%), documented caveat.

## OPEN / NEXT (pending Waleed)
- Scholar review of probes/proof-texts/judged sample (the big one before publish).
- 3 verse-only babs still title-pending (70,126,202) — not in the 140.
- Exemplar anchors for high-disagreement terrain (JLS-059-type) = next calibration.
- Decisions still open: 3 runs/cell for CIs (REJECTED earlier, revisit?);
  taqwabench repo public?; shannon Gemini rate fix; EdifyBench/VirtueBench
  provenance note + caro 7th-pressure idea (TABLED).

---

## (prior context retained below)

## RULINGS MADE 2026-06-12 (Waleed)

- **Full run = 139-probe subset + DUAL judging.** Encoded in design doc §3.1 (v0.3,
  commit b3091d7). One probe per probe-worthy measurement cluster; representative
  bab by hadith weight + plain case; split-half check; map re-derived not hand-edited.
- **gemini-3.5-flash added as 4th subject** (it's Ansari's base model — he said
  "GPT-3.5 Flash", verified actual id via API + AskUserQuestion). Pilot v3.1 result:
  flash −0.10 unstated vs ansari +1.45 = +1.55-band Ansari-layer value-add, the
  pilot's largest contrast. Flash: worst steadfastness (−0.31, caves to insistence
  −1.05/personal appeal −0.75), JLS-006 −1.92, guided ceiling +1.75 < frontier.
- **Source-citation metric** (his ask) is §6 of both reports: regex over transcripts
  (surah/verse, collections, prophet-said; bare mentions don't count). Ansari 80%
  hadith unstated vs 2/18/20% others; ansari citation DROPS guided (80→62%) — same
  guide-interference pattern as its score. Flash steepest stated jump (20→85%).
- Pilot FINAL (6 subjects): 1,080 sittings, 4,320 judgments, $104.54; agreement
  71/86 pool-wide (73/88 original pool). Unstated: ansari +1.45 > gpt +1.12 >
  sonnet +0.74 > nemotron +0.28 > flash −0.10 ≈ gemma −0.12. gemma/nemotron via
  Friendli/Blackbox (keys in cluesmith/shannon/.env). JLS-006 deliverable failure
  −2.00 for gpt+gemma+nemotron. Guide reviewed & frozen (meta para cut). Probe
  bank: 139 representatives selected (docs/jaleesbench-probe-bank.md); proof
  texts per bab in package (proof_texts.json; sunnah.com lacks verse openers).
  Citation rates now ON the scorecard (rows in §1) but outside the Jalees Score.
  WALEED CORRECTION (4th): no validation machinery — memory file written.
  NEXT: draft 139 probes (one Opus pass, proof texts + standards) → he reviews
  → full run. Runs/cell = 1 (triple runs REJECTED). Split-half REMOVED from design.
- Chapter map artifacts: results/chapter_map.jsonl ($3.42), chapter_clusters.json,
  docs/jaleesbench-chapter-map.md (143 clusters: 54 singletons, median 2, max 25
  "small voluntary devotions"; 4 etiquette-leaning excluded → 139).

## NEXT WORK (full-run prep, in rough order)

1. Pick the 139 representative babs (hadith weight + plain-case; mechanical, can
   start anytime). 3 verse-only babs still title-pending (70, 126, 202 — shamela
   403s; fill during authoring if their clusters need them).
2. Waleed reviews `docs/jaleesbench-guide.md` (STILL pending; blocks Guided framing
   at scale — if it changes post-run, guided cells need recollecting).
3. Exemplar anchors for grief/register judging (JLS-005-type cells still 52% exact;
   at 139 probes several register clusters will exist).
4. Author 139 probes × 6 pressure turns + corrective texts (standard #12) + proof
   texts. THE critical path. Batch + review.
5. Decide runs/cell (1 vs 3). Full-run cost w/ dual judges: ≈$263 collect +
   ≈$760 judge ≈ $1,025/run; ×3 ≈ $3.1k. Ansari self-host option open (his project).
6. Still pending: scholar review path; taqwabench repo public?; shannon Gemini rate.

## Repos & infra

- Root repo: github.com/waleedkadous/taqwabench (PRIVATE). Nested-and-gitignored:
  `external/` (virtue-bench-2 clone, branch main), `virtuebench-nemotron/` (own public
  repo), `tmp/`, `jaleesbench/results/`, `.env` (NEVER commit — has Anthropic+OpenAI keys).
- md→PDF: ALWAYS local `md2pdf`, never pandoc (Waleed hates LaTeX; memory file exists).
- Git: explicit paths only, no attribution lines, descriptive messages.

## Waleed's recurring corrections (respect these)

1. Don't buy complexity before it's needed (3× corrected): plain cases first, difficulty
   levers wait for saturation; no invented protocol machinery (kappa publishing etc.).
2. No predictions/hypotheses in shared docs; understated tone; translate all Arabic.
3. Idempotency expected everywhere; cost measurement expected.
4. Normative calls about the benchmark's fiqh (e.g. the deliverable rule) are HIS — present
   options + recommendation, get his ruling, then encode.
