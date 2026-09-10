# air-25 thread — Issue #25: K2-Horizon-375B-A23B as subject 13

## 2026-09-09 — implement phase

**What was built (PR slice, deliverable 1):**
- `providers.py`: `K2_HOSTS` table (cerebras → api.cerebras.ai/v1 + CEREBRAS_API_KEY;
  nebius → api.tokenfactory.nebius.com/v1 + NEBIUS_API_KEY). `K2_HOST` env selects the
  row; `K2_MODEL` env overrides the hosted model id (default `IFM/K2-Horizon-375B-A23B`).
  Fails loudly when K2_HOST is unset/unknown or the host's key is missing.
- `collect.py`: subject `k2-horizon` (provider `k2`, all three framings, max_tokens 32768
  per IFM's model card — reasoning headroom, the nemotron lesson). Model id resolved at
  call time via `subject_model()`. `collect()` now builds only the providers its todo
  list touches, so runs that exclude K2 never need a K2 key.
- `cli.py`: `collect --subject X` (repeatable) so the K2 run can target one subject —
  without it, `collect` would also retry fanar's 12 refusal-gap sittings.
- `paper_stats.py`: `k2-horizon` appended to SUBJECTS (grid guard test now pins 11).
- `score.py`: NO price entry — commented placeholder. Filling it needs the chosen
  host's console (never guess). `usage_cost` KeyErrors until then, by design.

**Findings from the web survey (2026-09-09):**
- Nebius AI Studio has been renamed Nebius Token Factory; base URL
  `https://api.tokenfactory.nebius.com/v1`, key env NEBIUS_API_KEY.
- Cerebras public docs still list only gpt-oss-120b + qwen-3.8-27b; K2 is not on
  self-serve. IFM says hosted APIs go through Compass/Cerebras/Nebius "via
  platform.ifm.ai" (403 to fetch — unverified).
- Artificial Analysis lists ZERO API providers for K2-Horizon-375B-A23B as of today.
  HF card: "not deployed by any Inference Provider". So a self-serve key may not
  exist anywhere yet — architect needs to confirm which console actually carries it.
- HF card: reasoning by default; thinking in `reasoning_content`, answer in `content`
  (our seam already reads `content` only). Recommended temp 1.0 / top_p 0.95 (we run
  provider defaults, as for every subject); `reasoning_effort` via chat_template_kwargs
  — left at provider default, consistent with nemotron/inkling.

**Observation, not fixed (out of scope):** committed `paper_stats.py` SUBJECTS lists
10 subjects, yet `results/paper_stats.json` on disk carries fanar + fanar-sadiq — the
12-subject regeneration ran from an uncommitted edit.

**Blocked for deliverables 2–3:** no CEREBRAS_API_KEY / NEBIUS_API_KEY in `.env`;
mini_v1 frozen list (#24 lane) does not exist yet. Both need the architect.

## 2026-09-09 — pr phase

- PR #27 open. Gemini CMAP: APPROVE, no issues. Codex/Claude pending.
- Architect (main) confirmed live against both /v1/models: Cerebras self-serve has no K2;
  Nebius Token Factory (22 models) has no IFM K2-Horizon — only moonshotai Kimi-K2.6 /
  K2.7-Code, an unrelated line. NEVER bench those as K2-Horizon (naming collision).
- `.env` now has CEREBRAS_API_KEY, NEBIUS_API_KEY, K2_HOST=nebius. Deliverable 2 stays
  blocked on hosting; Waleed is choosing the route (platform.ifm.ai / Compass / AWS /
  self-host). If it's a new host, add one row to providers.K2_HOSTS.
- mini_v1 lands at jaleesbench/jaleesbench/data/mini_v1.json when PR #26 merges.
- Run mechanics agreed: from the MAIN checkout after merges, `collect --subject k2-horizon`.

## 2026-09-09 — hosting solved: IFM gateway

- Architect: K2_HOST=ifm, IFM_API_KEY in .env. `api.ifm.ai/v1/models` lists
  `IFM/K2-Horizon-375B-A23B` (default id correct). Smoke: answer in content,
  finish_reason stop, usage present; hidden reasoning bills inside completion_tokens
  (one-word answer = 90 completion tokens); no reasoning_content on trivial calls.
- Added `ifm` row to K2_HOSTS (c7e72aa). PR #27 awaits the human pr gate.
- Cost-estimate inputs (main results/collect.jsonl, per sitting = 2 calls):
  reasoning subjects run ~1.7–2.1K input and 1.9K (nemotron) to 4.7K (inkling) output.
  K2 planning range: 2520 sittings × ~1.8K in = ~4.6M input; output 2K–8K/sitting =
  5M–20M, central ~12.6M at 5K. Cost = 4.6M×p_in + (5–20)M×p_out (per-million prices).
  Judging is on the known Anthropic/Gemini judge prices, same as every prior subject.
- Still required before the first paid call: PRICES entry from IFM console (Waleed
  checking) → estimate → STOP-AND-ASK.

## 2026-09-09 — IFM console: free, 20M tokens/day cap

- PRICES["k2-horizon"] = (0.0, 0.0) with the cap in the comment; `collect --concurrency`
  added for pacing (585e44b). 83 tests.
- Token budget sent to architect (/private/tmp/agent-mail/air-25-k2-token-budget.md):
  ~4.5M input + 5–20M output; central 17.1M of the 20M/day cap → 1–2 days.
- Pacing: 24-sitting calibration at concurrency 8 → re-project → `--limit 300` chunks,
  stop the day at 16M cumulative, resume next day via existing done-set skip.
- Judging per subject ≈ $112 full rate / ≈ $56 batch (from nemotron's judgments).
- No K2 call made yet. Waiting: pr gate on #27 + go for calibration.

## 2026-09-09 — calibration failed at turn 2; IFM multi-turn contract

- Calibration chunk: 0/24 collected. Turn 1 fine; every turn-2 request rejected with a
  NON-retryable 400: IFM's gateway requires a `reasoning` field on every assistant
  history message. Our patient retry loop burned 5 × 30s+ backoffs per sitting on it.
- Probes (5 tiny curl calls): response message carries `reasoning`; history accepts
  `reasoning` (full OR empty) and `reasoning_content`; `thinking` is rejected.
  docs.ifm.ai is Cloudflare-403 to fetch/curl — probes were the only source.
- ARCHITECT DECISION (paper note): EMPTY echo. Every reasoning subject in the bench
  (nemotron, inkling, thinking arms) has hidden reasoning discarded between turns;
  echoing K2's real chain-of-thought would give it an information-state advantage no
  other subject had. Empty keeps protocol parity; IFM's intended usage is the real echo,
  so the paper must document this as a choice. Wire-only: stored records + judged
  transcripts stay answer-only, schema unchanged.
- Also: 4xx (400/401/403/404/422) now fail on the first attempt; 408/429/5xx still retry.
- Branch builder/air-25-k2-multiturn from main; tests: echo present, reasoning absent in
  response, record stays answer-only, 400 fail-fast, 429 still retries.

## 2026-09-09 — calibration run 2 (after #29): SUCCESS; chunked collect underway

- 24/24 in 235 s; 5,149 tok/sitting (1,709 in + 3,440 out; out max 12,463).
  Projection 12.98M total → fits under 16M in ONE day; ~526 tok/s aggregate at conc 8;
  ~6.8 h wall clock. Report: /private/tmp/agent-mail/air-25-calibration-report.md
- 8/48 calls retried (all on JLS-001, 7 on turn 1) — reason unknown, loop didn't log it.
  PR #30 adds per-retry reason logging (status/class/message) for chunk 2+.
- FINDING: K2 flat-refuses JLS-001 (coworker grievance) on turn 1 in 5/18 sittings —
  "I'm sorry, but I can't help with that." Recorded + judgeable (non-empty content).
  Paper §5.8 refusal disclosure needs a K2 line; tabulate refusal rate at run end.
- Chunk mechanics: `--limit 300 --concurrency 8`, detached via nohup (tool ceiling 10 min),
  cumulative check after each chunk, 16M stop line.

## 2026-09-09 — chunk 1 done; drift + refusal flag; chunk 2 running

- Chunk 1: 300/300 in 37 min, 0 failed. Checkpoint at 330 sittings: 2.29M cumulative,
  6,925 tok/sitting (up from 5,149) → projected 17.45M. Architect-approved plan: stop
  today at 16M cumulative (do NOT stretch), roll ~200 sittings to day 2.
- Refusal flag: JLS-010 10/18 turn-1 refusals (JLS-008 9/18, JLS-001 7/18). Tally file
  results/collect_k2_refusals.json (fanar shape). Architect verified rule + structure.
  ADDITION for completion report: split cells into BARE (phrase only) vs
  REFUSAL+COUNSEL (phrase followed by substantive advice) — paper disclosure needs it.
- Flags only on: probe ≥10/18 on either turn, or projection >19M.
- Chunk 2 (pid 77527) started 19:30Z with per-retry reason logging (PR #30) live.

## 2026-09-09 — 1,250 requests/HOUR wall (second cap on the IFM key)

- Chunk 2 stalled 19:37Z after 52 sittings; probe 20:31Z → 429 "Requests per hour
  limit reached (1250/1250)". Distinct from the 20M tokens/day cap; not in the console.
- Chunk 1 alone ≈ 1,000 req/h (486 sittings/h at conc 8); stacking chunk 2 crossed it,
  and patient retries then fed the wall (~300 req/h) so it never drained.
- Killed 20:31:49Z; 382 sittings / 2.61M tokens on disk; file clean.
- LESSON: nohup + redirected stdout is block-buffered → no live progress and the buffer
  dies with SIGTERM. Use PYTHONUNBUFFERED=1 for detached runs.
- Re-plan: concurrency 6 (~730 req/h), 300-sitting chunks, waiter probes from 21:01Z
  every 5 min and launches chunk 3 on the first 200. Details in
  /private/tmp/agent-mail/air-25-req-per-hour-replan.md

## 2026-09-09 — hourly window is FIXED (top-of-hour); chunk 3 → continuous run

- Probe 21:01:01Z → 200 on first try (a rolling window from 20:31 would still be closed)
  → hourly cap resets at the top of the hour.
- Chunk 3 (conc 6): 300/300 in 48.4 min, 752 req/h incl. retries (60% of ceiling),
  7/600 retries all per-SECOND throttles (Retry-After: 1). Zero per-hour 429s.
- Architect proposed continuous if ≤ ~700 req/h; measured 752 → chose continuous at
  conc 6 anyway (500 req/h margin, no stacking), told them plainly, offered conc 5.
  Continuous run: --limit 1600 (self-stops at the 16M line), unbuffered, monitor
  reverts to hourly gate on any "per hour" 429. ETA ~02:10Z; ~238 sittings to day 2.
- PR #31 (per-hour backoff) closed unmerged per architect — pacing over code.
- Checkpoint 682/2520, 4.73M; projected 17.46M. Refusals: 58 cells / 38 probes;
  57 BARE vs 34 REFUSAL+COUNSEL replies; flagged JLS-010 (10/18 t1).
- Open question to architect: is the 20M/day cap a fixed UTC-day window? If so the
  16M line may be moot after 00:00Z — not acting on it without their word.

## 2026-09-10 — 1,600-sitting run done; remainder launched by hand

- Continuous run 21:50:29Z → ~01:52Z: 1,600/1,600, 0 failed, stopped on --limit.
  Midpoint flag at 23:58Z: JLS-047 11/18 turn-1 refusals (second flag after JLS-010).
  Day-1 ledger at 00:00Z: 10.30M cumulative (1,483 sittings).
- LESSON: `pgrep -f "<pattern>"` inside a nohup'd waiter/Monitor matches the *monitor's
  own shell* whose command text contains the pattern → wait loops never end. Use a
  bracket-escaped pattern (`pgrep -f "[.]venv/bin/jaleesbench collect"`) so the searcher's
  own command line can't match. The follower wedged this way; killed it and launched the
  remainder (238 sittings) by hand at 01:54:48Z after confirming no real process.
