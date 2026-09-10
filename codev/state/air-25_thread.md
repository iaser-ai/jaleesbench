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

## 2026-09-10 02:30Z — judging released and running; post-collection prep

- Opus: one Anthropic batch msgbatch_01FanqCx2gHJgoJSFyNREDWx (5,040 requests, 50%).
  Gemini (no Vertex batch): live judge_all(judges={'gemini-3.1-pro-preview'}) detached,
  5,045 todo (5,040 K2 + 5 pre-existing fanar gaps — those fail with 'band' parse
  errors as before; not K2). Pace ~47/min → ETA ~04:20Z. Batch collect waits until the
  Gemini judge exits (both append judgments.jsonl; avoid interleaved writes).
- Issue #28 CONFIRMED: regenerating paper_stats with the 12-subject list against main's
  data reproduces the committed JSON leaf-for-leaf (only meta.n_judgments differs, by
  the in-flight K2 judgments). Branch builder/air-25-paper-grid (b031ed2, local) has
  SUBJECTS = 13 + test; JSON regen + PR after K2 judgments land.
- V4 instrument = the #24 lane's own command:
  `uv run --directory jaleesbench python -m jaleesbench.mini score --results jaleesbench/results --subject k2-horizon`
  (E1/E3/E4 on frozen mini_v1 k=110 vs full 140, abs_err per estimand, pass at ≤0.05).

## 2026-09-10 ~04:00Z — JUDGED + SCORED

- Judgments: K2 10,079/10,080 (Opus 5,040 — 4,987 batch + 53 live; Gemini 5,039).
  One documented gap: k2-horizon|JLS-055|good_cause|unstated|gemini|full — Gemini emits
  garbage on all 6 attempts (same species as fanar's 5 chronic cells). No dupes.
- Judge cost ACTUAL $202.46 (Gemini $139.82 live — Vertex has no batch; Opus $62.63,
  4,987 batched) vs my ~$56 estimate: I wrongly assumed both judges batch, and K2's
  long replies inflate transcripts. Reported plainly to the architect.
- Full-140 Jalees Score (unstated/full): −0.448 [−0.516, −0.379] — 13th of 13, just
  below qwen3-235b (−0.48 overlaps) and fanar-sadiq (−0.43). Stated −0.068, guided
  +0.510 (instruction gap +0.58, the largest staircase in the pool). Steadfastness
  −0.088 [−0.129, −0.048].
- V4 PROSPECTIVE (mini_v1, k=110): abs_err E1 0.0107, E3 0.0085, E4_stated 0.0187,
  E4_guided 0.0110 → PASS at the 0.05 bound. Saved results/mini_v4_k2-horizon.json.
- paper_stats.json regenerated with 13 subjects; only non-K2 leaves that move are the
  pooled judge_agreement (now includes K2 pairs) and meta counts. PR on
  builder/air-25-paper-grid closes #28.
