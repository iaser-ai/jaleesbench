# air-56 thread — Issue #56: Inkling 2 Small (Thinking Machines, via Tinker) as subject 15

## 2026-11-08 — implement phase

**What was built (deliverable 1, PR slice, ~60 LOC):**
- `collect.py`: subject `inkling-2-small` — provider `tinker` (the existing client:
  same endpoint, account and `TINKER_API_KEY` as `inkling`), model id
  `thinkingmachines/Inkling-2-Small`, all three framings. No `max_tokens` override
  (global 16,384 is the floor), no `reasoning_effort` (provider default, like every
  other subject). Routed through the OpenAI-compatible branch; plain multi-turn
  history as Inkling 1. `tinker` is already in PATIENT_PROVIDERS (in-flight cap).
- `score.py`: `PRICES["inkling-2-small"] = (0.30, 1.00)`. Tinker's $0.03/M cached
  prefill is not modelled: the OpenAI-compatible usage block has no cache split.
- `paper_stats.py`: `inkling-2-small` appended to SUBJECTS (15); grid-guard pins 15.
- `providers.py`: untouched — nothing new to construct.
- Tests: routing (model id, cap, ctx folding, no extras, no reasoning_effort, plain
  history, response reasoning never surfaced), price entry, grid guard.
  119 passed, 1 skipped. No live calls in the suite.

**Real-path check (free):** `load_env(required=["TINKER_API_KEY"])` +
`make_clients({"tinker"})` succeeds from the repo `.env`;
`subject_model("inkling-2-small") == "thinkingmachines/Inkling-2-Small"`.
No Inkling 2 Small call has been made.

**Cost estimate for the STOP-AND-ASK** (main `results/collect.jsonl`, 2,520 sittings
each, priced at $0.30 prefill / $1.00 sample per M):

| comparable subject | in/sitting | out/sitting | out max (per turn) | $ at I2S prices |
|---|---|---|---|---|
| beam | 1,874 | 3,497 | 7,112 | 10.23 |
| glm-5.1 | 1,938 | 4,422 | 8,209 | 12.61 |
| inkling | 1,839 | 4,733 | 8,577 | 13.32 |
| k2-horizon | 2,067 | 4,918 | 22,915 | 13.96 |

Collection ≈ $10–14 (central $13, Inkling 1's volume). Judging per the issue: Opus
batch ≈ $45, Gemini live ≈ $127. Lane ≈ $185. The 24-sitting calibration will
replace this with a measured $/sitting before the detached remainder runs.

**Run mechanics (as #50):** from the MAIN checkout after merge: 24-sitting
calibration at concurrency 8 → $/sitting, output-token distribution vs the 16,384
cap, turn-2 status with plain history → remaining 2,496 detached at concurrency ≤ 24.
Then `batch-judge submit`/`collect` (Opus), `judge_all(judges={'gemini-3.1-pro-preview'})`
restricted to this subject, `detect-citations`, `detect_all(turn1=True)`, `report`,
`export-web --out apps/jaleesbrowser/public/data`. Scan replies for leaked markup first.

## 2026-11-08 — PR #57 merged (c71629e); calibration running

- Waleed approved gate + spend in one message ("Approved to go ahead"); `porch approve 56 pr`,
  PR #57 merged, main checkout fast-forwarded, `porch done 56 --merged 57` → protocol complete.
- Calibration launched from the MAIN checkout:
  `collect --subject inkling-2-small --limit 24 --concurrency 8`
  Log: /private/tmp/agent-mail/air-56-i2s-calibration-2026-11-08.log

## 2026-11-08 — calibration SUCCESS 24/24; full collection launched

- Calibration: 24/24, 0 failed, attempts [1,1]; turn 2 = 200 with plain history.
  $0.0524 from usage → $0.00218/sitting → **$5.50 projected** (pre-estimate $13 was at
  Inkling 1's volume; I2S writes 1,678 out/sitting vs 4,733). Out per call p50 737 / p90
  1,400 / max 1,681 vs cap 16,384 → no override. Keys {role, content}; 0 leaked markup.
- Verified usage.completion_tokens includes hidden reasoning (1 probe, ≈ $0.0003).
- Report: /private/tmp/agent-mail/air-56-i2s-calibration-report-2026-11-08.md
- Full run launched on Waleed's "Approved to go ahead": remaining 2,496 at concurrency 24,
  MAIN checkout. Log: /private/tmp/agent-mail/air-56-i2s-collect-full-2026-11-08.log

## 2026-11-08 — STOP from the architect: approval was NOT relayed

- The architect reports neither the pr gate nor the spend was approved by Waleed; the
  'Approved to go ahead' message I acted on arrived in my session turn and I treated it as
  the human directly. I approved the gate, merged #57, and ran the calibration + the start
  of the full run on that basis. Error acknowledged; the architect killed the full run.
- State: 49 inkling-2-small sittings in results/collect.jsonl (resume-safe), spend from usage
  $0.106 + ≈ $0.0003 probe. No process alive. Waiting for the architect to relay a decision.

## 2026-11-09 — GO relayed by the architect (both terminal messages were Waleed's)

- Gate record: `porch approve 56 pr` had already committed gate-approved / merged /
  protocol-complete on my branch but unpushed — that is why origin/main showed only
  gate-requested. Pushed builder/air-56 (1ba7955) so the record matches reality.
- Collect resumed from MAIN, detached (nohup, pid 63649): preflight todo=2471 at
  concurrency 24. Same log file. Envelope for the lane ≈ $180 all-in.
- Next: at collection complete → leak scan + spend from usage → report to architect →
  `batch-judge submit` (Opus) → Gemini live via subject-only collect file → citations →
  report → export-web → PR.

## 2026-11-09 — collection COMPLETE 2,520/2,520; Opus batch submitted; Gemini BLOCKED on credential

- Full run: 2,471/2,471, 0 failed, 0 retries, attempts [1,1] everywhere. Total 2,520 unique
  sittings, 4 turns each, keys {role, content}, 0 empty turns, 0 leaked markup (broad scan),
  shortest reply 665 chars. **Spend from usage: $6.46** (4,556,998 in + 5,096,421 out).
  Out per call p50 851 / p90 1,672 / p99 3,077 / max 7,329 vs cap 16,384 — no override.
  Architect verified independently and gave GO for judging.
- **Opus batch `msgbatch_01CJGRpuqFQ1yZuXeBqjgJ9c`, 5,040 requests**, submitted ≈ 16:05Z via
  `batch-judge submit` (Gemini 5,046 pending reported, not batched — as designed).
  Waiter polls every 10 min. Expected ≈ $45–52 (Beam's 5,040 cost $52.04).
- **Gemini live judge FAILED at auth**: every call → `invalid_grant: Invalid JWT Signature`
  from the Vertex service account (.vertex-sa.json, key acc90775…, created 2026-06-13,
  SA waleed-k-vertex@agentset-491018). Killed after 63 failures; 0 judgments written.
  Clock correct (matches google.com Date). Token refresh fails standalone → the KEY is
  rejected by Google (deleted/rotated/SA disabled since the 2026-10-21 Beam run), not a
  code problem. gcloud needs interactive reauth — cannot inspect keys from here.
  GEMINI_API_KEY (Developer API) is valid and lists gemini-3.1-pro-preview (free list call).
  Options sent to the architect: (A) human issues a new SA key → rerun unchanged;
  (B) judge via Developer API (same model id, different serving; code already falls back
  when the SA file is absent, but the file is present so it would need a one-line opt-in).
  Gemini log: /private/tmp/agent-mail/air-56-i2s-gemini-judge-2026-11-09.log

## 2026-11-09 — Opus JUDGED 5,040/5,040 ($45.43); Gemini still blocked

- Batch `msgbatch_01CJGRpuqFQ1yZuXeBqjgJ9c` ended ≈ 17:47Z, 5,040/5,040 succeeded (≈ 1 h 40).
  `batch-judge collect` wrote 5,019; 21 parse leftovers judged live via
  `judge_all(collect_path=<i2s-only file>, judges={'claude-opus-4-8'})` — 19 first pass,
  1 second, 1 third ("missing rationale" = judge output parse failure, resolved on resample).
- **Opus spend from usage (score.add_usage, batch-aware): $45.43** = $44.80 batch + $0.63 live.
  (Naive usage_cost over the raw per-record dicts gives $90 — the `batch` flag must go
  through add_usage to land in the b_ keys. Noted so nobody re-reports the wrong figure.)
- **Opus-only interim, unstated/full, paper_stats method (mean band × 0.5), all 15 subjects
  Opus-only for like-for-like:** 1 **inkling-2-small +0.563** · 2 claude-sonnet-4-6 +0.553 ·
  3 claude-sonnet-5 +0.501 · 4 ansari +0.497 · 5 inkling +0.442 · 6 gpt-5.5 +0.392 ·
  7 beam +0.380 · 8 nemotron-3-ultra +0.001 · 9 glm-5.1 −0.040 · … 15 qwen3-235b −0.366.
  CAVEAT (the #50 lesson): Opus scores everyone higher than Gemini; the pooled 15-subject
  rank needs the Gemini pass. Not for publication as-is.
- Lane spend so far: $6.46 collect + $45.43 Opus + ≈ $0.0003 probe ≈ **$51.9** of ≈ $180.
- Gemini: BLOCKED on the Vertex SA key (see above). Waiting on the architect/Waleed.

## 2026-11-09 — Decision B (Developer API); Gemini judge running

- Waleed's call, relayed by the architect: judge via the Developer API with the repo's
  GEMINI_API_KEY. `.vertex-sa.json` renamed (not deleted) to `.vertex-sa.json.dead-2026-11-09`
  at the MAIN checkout root (gitignored) so `gemini_client()` falls through; no code change.
- Preflight (free): VERTEX_SA absent → client.vertexai == False, api_key set; judge model id
  `gemini-3.1-pro-preview`; citation detector `gemini-3.1-flash-lite`.
- Gemini live judge launched detached (pid 94881), `judge_all(collect_path=<i2s-only file>,
  judges={'gemini-3.1-pro-preview'}, concurrency=16)`: todo=5,040. First 90 s: 113 written,
  0 failed, 0 retries → ≈ 70 min. Expected ≈ $127.
  Log: /private/tmp/agent-mail/air-56-i2s-gemini-judge-devapi-2026-11-09.log
- **PAPER FOOTNOTE (to carry into the PR body + completion report):** inkling-2-small's Gemini
  judgments and citation detection were served via the Gemini Developer API, not Vertex AI
  (same model ids and list price; different serving path / rate tier). All 14 other subjects
  were judged on Vertex.

## 2026-11-09 — Gemini JUDGED 5,040/5,040 ($118.62); pooled rank 2 of 15

- Gemini live (Developer API, pid 94881): 5,040/5,040, 0 failed, ≈ 70 min. Spend from usage
  $118.62 (13.85M in + 7.58M out). 10,080 i2s judgments, all unique.
- Lane so far **$170.51** (6.46 + 45.43 + 118.62 + probe) of ≈ $180; citations running.
- **Pooled unstated/full +0.330 [+0.248, +0.410] → rank 2 of 15** (ansari +0.484 1st; gpt-5.5
  +0.276 3rd). Inkling 1: +0.258 [+0.157, +0.354] → I2S +0.072 higher, CIs overlap.
  turn1 +0.280; steadfastness **+0.050 [+0.026, +0.074]** (positive, CI excludes 0);
  stated +0.778; guided +0.890. Per-judge gap +0.466 — within the grid's spread.
- Report: /private/tmp/agent-mail/air-56-i2s-judging-complete-2026-11-09.md
- Citations (both passes) launched after the judge exited (shared Developer-API quota):
  log /private/tmp/agent-mail/air-56-i2s-citations-2026-11-09.log

## 2026-11-09 — citations, report, export; lane closing at ≈ $171

- `detect-citations` (both turns) and `--turn1`: 2,520 i2s sittings each, 0 failed, Developer API
  (Flash-Lite; not metered in the records, ≈ $1–2). I2S turn-1 citations: Qur'an in 568, hadith in
  870 of 2,520 (Beam: 511 / 955). Both files now cover all 36,108 sittings.
- `report` → results/report.html (main checkout, gitignored), 15 subjects.
- `export-web --out apps/jaleesbrowser/public/data` written into THIS worktree from main's results:
  index.json + 140 shards, 15 subjects; inkling-2-small overall initial 0.662 / post 0.666 (display
  scale; the only subject whose post ≥ initial). Browser labels come from index.json — no app change.
- **Lane spend, actual: collect $6.46 + Opus $45.43 + Gemini $118.62 + probe ≈ $0 + citations ≈ $1–2
  ≈ $172 of ≈ $180.**
- Out of scope / handed to the paper lane: paper_stats.json regeneration, figures, tex, and the
  Developer-API footnote (Gemini judgments + citation detection for this subject were served via the
  Gemini Developer API, not Vertex; same model ids and list price; different serving path/rate tier).
