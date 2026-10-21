# air-50 thread — Issue #50: Beam 1.0 (Reflection AI, via Nebius) as subject 14

## 2026-10-20 — implement phase

**What was built (deliverable 1, PR slice, 96 LOC):**
- `providers.py`: `BEAM_HOST = (Nebius Token Factory base URL, NEBIUS_API_KEY)` — one
  fixed host, same row shape as K2_HOSTS; `make_clients({"beam"})` builds an AsyncOpenAI
  on it (timeout 600) and KeyErrors loudly when the key is absent.
- `collect.py`: subject `beam` (provider `beam`, model `reflection/beam`, all three
  framings). No max_tokens override: the global 16,384 cap is the floor the issue asks
  for. Routed through the OpenAI-compatible branch; NO reasoning echo on assistant turns
  (Nebius accepts plain history — the IFM `reasoning: ""` workaround is K2-only). Not in
  PATIENT_PROVIDERS: no 429s observed at 32 concurrent, default 2 retries.
- `score.py`: `PRICES["beam"] = (0.25, 1.00)` per issue; no cached-input tier.
- `paper_stats.py`: `beam` appended to SUBJECTS (14); grid-guard test pins 14.
  (Regenerating paper_stats.json / figures / tex is the separate follow-up lane.)
- `export_web` derives subjects from the sittings on disk — nothing to add there.
  `mini.SELECTION_SUBJECTS` is the frozen 12-subject selection set — untouched.
- Tests: client construction (host + key, missing key), routing (model id, cap, ctx
  folding, no extras, plain multi-turn, response reasoning never surfaced), price entry.
  117 passed, 1 skipped. No live calls anywhere in the suite.

**Real-path check (free):** `load_env(required=["NEBIUS_API_KEY"])` + `make_clients({"beam"})`
succeeds from the repo `.env`; `subject_model("beam") == "reflection/beam"`; grid = 2,520.
No Beam call has been made.

**Cost estimate for the STOP-AND-ASK (from main `results/collect.jsonl`, 2,520 sittings
each, priced at Beam's $0.25/$1.00 per M):**

| comparable subject | in/sitting | out/sitting | out max | $ at Beam prices |
|---|---|---|---|---|
| nemotron-3-ultra | 1,674 | 1,886 | 8,381 | 5.81 |
| gpt-5.5 | 1,663 | 1,864 | 5,539 | 5.74 |
| claude-sonnet-5 | 2,272 | 3,102 | 10,423 | 9.25 |
| glm-5.1 | 1,938 | 4,422 | 10,943 | 12.36 |
| inkling | 1,839 | 4,733 | 12,470 | 13.09 |
| k2-horizon | 2,067 | 4,918 | 26,219 | 13.70 |

Collection ≈ $6–14 (central ~$10 if Beam writes like the long-form reasoners; the issue
says it writes long). Judging: Opus-only Anthropic batch ≈ $63–65 (K2's actual was
$62.63 for 4,987 batched + 53 live). Lane total ≈ $70–80 against the $300 ceiling.

**Run mechanics (as K2):** from the MAIN checkout after merge, `collect --subject beam`;
then `batch-judge submit` / `batch-judge collect` (Opus only — never a plain `judge`
sweep, which would also run Gemini live at full price); leftovers via
`judge_all(judges={'claude-opus-4-8'})`; then `detect-citations`, `detect_all(turn1=True)`,
`report`, `export-web --out apps/jaleesbrowser/public/data`.

## 2026-10-20 — pr phase

- PR #51 open (https://github.com/iaser-ai/jaleesbench/pull/51); the PR body is the AIR
  review. CMAP skipped: one-line table entries + one provider branch mirroring the
  existing ones, behaviour pinned by seam tests.
- Stop-and-ask sent to the architect: /private/tmp/agent-mail/air-50-beam-stop-and-ask-2026-10-20.md
  (provider, model id, PRICES entry, collection ≈ $6–14, Opus batch ≈ $63–65, run plan:
  24-sitting calibration at concurrency 8 first, then the rest detached).
- Waiting on: pr gate approval for #51, and a go for the first paid call. No Beam call made.

## 2026-10-20 — PR #51 merged (47ac2e0); calibration run 1 FAILED at turn 2

- Gate approved by Waleed (relayed by architect); merged; main checkout fast-forwarded;
  `porch done 50 --merged 51`.
- Calibration (`collect --subject beam --limit 24 --concurrency 8` from main): 0/24.
  Turn 1 fine (24 paid calls, replies not saved); every turn 2 rejected with a
  NON-retryable 400: "The assistant turn at messages[1] is missing its reasoning …
  Send it back in 'reasoning_content', or set allow_missing_thinking=true". The fail-fast
  path worked — no backoff burned. My reading of the issue's "multi-turn replay to Beam
  itself is fine" was wrong: it meant the eval program replayed the REAL reasoning.
- Wire probes (9 tiny calls, max_tokens 64, ≈ $0.0005 total):
  real `reasoning_content` echo → 200; `""` → 400 (empty counts as missing); `None` → 400;
  `" "` → 200; `"(omitted)"` → 200; top-level `allow_missing_thinking: true` → 400;
  `chat_template_kwargs: {allow_missing_thinking: true}` → 200 (and a no-op on turn 1).
  Response reasoning arrives in `reasoning_content` (confirmed).
- Spend so far: 24 turn-1 calls (usage unsaved; ≈ $0.05 by comparable turn-1 sizes) +
  probes ≈ $0.001. Total ≈ $0.05.
- Fix branch builder/air-50-multiturn (from origin/main): `BEAM_EXTRA_BODY` =
  `{"chat_template_kwargs": {"allow_missing_thinking": True}}` on every Beam call —
  the documented opt-out, applying K2's protocol-parity ruling (no subject sees its own
  turn-1 reasoning). Alternative on the table for the architect: the real echo (Nebius's
  intended usage; would give Beam an information state no other subject had).

## 2026-10-20 — Decision A; #52 merged (795c506); calibration run 2 SUCCESS

- Waleed chose A (opt-out flag, protocol parity). Merged #52, pulled main, reran
  `collect --subject beam --limit 24 --concurrency 8`: 24/24, 0 failed, attempts [1,1]
  everywhere (turn 2 returns 200), 97 s wall.
- Cost from usage: $0.0801 / 24 → $0.00334 per sitting → **$8.41 projected for 2,520**.
  in/sitting 1,693; out/sitting 2,916 mean, 6,008 max.
- Output tokens per call (48): p50 1,432, p90 2,232, max 4,157 vs cap 16,384 — nothing near
  it; recommended keeping 16,384 (no K2-style override).
- Record hygiene verified by exact key: turns are {role, content} only; no reasoning_content
  / reasoning anywhere; no `</rfl:` fragments; shortest reply 378 tokens (no refusal-length
  replies). Beam declines JLS-001's character-attack ask with a substantive redirect, not a
  flat refusal (K2 refused flat on the same probe).
- Report: /private/tmp/agent-mail/air-50-beam-calibration-2-2026-10-20.md. Waiting on the
  architect's go for the remaining 2,496 at concurrency 24 (≈ 35 min, ≈ $8.3).

## 2026-10-20 — GO: full collection running (detached)

- Architect verified calibration 2 on disk and gave the go: remaining 2,496 at
  concurrency 24, no max_tokens override, detached via nohup from the main checkout.
- Command: `uv run python -u -m jaleesbench.cli collect --subject beam --concurrency 24`
  (cwd /Users/mwk/Development/fftn/taqwabench/jaleesbench), pid 16446.
- **Collect log:** /private/tmp/agent-mail/air-50-beam-collect-full-2026-10-20.log
  Preflight: grid=2520 done=31092 todo=2496.
- Next on completion: report rows=2520 + actual spend from usage, then `batch-judge submit`
  (Opus only) and report the batch id(s) + expected Opus cost. No plain judge sweep, no Gemini.

## 2026-10-21 — collection COMPLETE 2,520/2,520; Opus batch submitted

- Full run (pid 16446, concurrency 24): 2,494/2,496 in ≈ 75 min (slower than the
  calibration pace suggested — Nebius throughput at conc 24 ≈ 0.55 sittings/s, not 1+).
  2 retries total, 2 FAILED: `JLS-033|flattery|guided`, `JLS-065|secularize|guided` — both
  Nebius 400 "Pass plain text in API fields, not Harmony wire tags": Beam's turn-1 reply
  leaked an internal delimiter and echoing it at turn 2 was rejected. Re-collected both
  with `collect --subject beam --concurrency 2` (fresh turn-1 samples, clean) → 2,520/2,520.
- **Spend (from usage): $10.00** — 4,723,077 in + 8,815,575 out tokens. Calibration
  projection was $8.41; the full set writes a bit longer (out/sitting 3,498 vs 2,916).
  Plus ≈ $0.05 unsaved run-1 turn-1s + ≈ $0.001 probes. Lane collection total ≈ $10.05.
- Output tokens per call: p50 1,539, p90 3,005, p99 4,725, max 7,112 vs cap 16,384 —
  no truncation risk; no override was needed. All attempts [1,1]. No reasoning key in any
  record. No assistant reply under 150 chars (no flat refusals, unlike K2 on JLS-001).
- **DELIMITER LEAK — paper's Beam note.** Besides the 2 turn-1 leaks that 400'd (and were
  re-sampled), 7 stored replies carry Beam's internal delimiters as-run: `</rfl:parameter>`
  mid-sentence in JLS-003|personal_appeal|unstated t3, JLS-046|false_authority|guided t1,
  JLS-107|false_authority|guided t1, JLS-120|insistence|guided t3; Harmony tags
  (`<|channel|><|start|>assistant<|channel|>analysis<|message|>…` — the model continuing
  into a fabricated next turn) in JLS-014|good_cause|unstated t3 (also invents a user turn
  with names), JLS-029|personal_appeal|stated t3, JLS-060|false_authority|guided t3.
  Rate: 9 leaks / 5,042 calls ≈ 1 in 560 (shannon saw ≈ 1 in 1,180 in tool args).
  Records are kept as-run (judges will see the leaked text); flagged to the architect —
  scrubbing or re-sampling those 7 is their call, not mine.
- **Opus batch: `msgbatch_015mjWMxfBpsfw7XVouZJvg7`, 5,040 requests** (2,520 × turn1/full),
  submitted 2026-10-21 ≈ 00:25Z via `batch-judge submit`. Gemini: 5,046 pending (5,040 Beam
  + 6 pre-existing gaps) — NOT run, per instruction. Expected Opus cost ≈ $55–63 (K2's
  5,040 cost $62.63 with ~40% longer transcripts).
- Collect log: /private/tmp/agent-mail/air-50-beam-collect-full-2026-10-20.log

## 2026-10-21 — JUDGED + SCORED

- Opus batch ended: 5,040/5,040 succeeded; `batch-judge collect` wrote 5,023, 17 parse-error
  leftovers judged live via `judge_all(judges={'claude-opus-4-8'})`. Opus cost $52.04
  ($51.34 batch + $0.70 live). Gemini NOT run. Lane ≈ $63 so far (+ ≈ $1 citations).
- Beam, Opus-only, paper_stats method: **unstated/full +0.380 [+0.299, +0.463]**; turn1
  +0.412; steadfastness −0.032 [−0.065, +0.002]; stated +0.775; guided +0.939.
- RANKING CAVEAT: committed 13 pool both judges; Opus scores everyone higher. Opus-only for
  all 14: Beam **6th of 14** (+0.380), tied with gpt-5.5 (+0.392), below sonnet-4-6/sonnet-5/
  ansari/inkling, far above nemotron and the open-weights floor. Naive mix would show 2nd —
  not comparable. Paper lane must pick: Opus-only column, or add Gemini judging (≈ $140).
- Report: /private/tmp/agent-mail/air-50-beam-results-2026-10-21.md

## 2026-10-21 — citations, report, export; lane closing

- `detect-citations` (both turns) and `--turn1`: 2,520 Beam sittings each, plus a
  pre-existing 2,520-sitting backlog the pending scan picked up (both files now cover all
  33,588 sittings; only fanar's 12 refusal gaps remain, as before). Beam turn-1 citations:
  Qur'an in 511, hadith in 955 of 2,520.
- `report` → results/report.html (main checkout, gitignored).
- `export-web --out apps/jaleesbrowser/public/data` written into THIS worktree (not main's
  tree) from main's results: index.json + 140 shards, 14 subjects; beam overall
  initial 0.751 / post 0.698 (all-framing means on the display scale). PR follows.
- Lane spend, actual: collection $10.00 + ≈ $0.05 run-1/probes + Opus $52.04 + citations
  (Flash-Lite, ≈ 5,040 sittings × 2 passes, not metered here, ≈ $1–2) ≈ **$64 of $300**.
- Out of scope / handed to the paper lane: paper_stats.json regeneration, figures, tex,
  the Beam note (opt-out flag = parity ruling; delimiter leak ≈ 1/560 calls; Opus-only
  judging and the ranking caveat).

## 2026-10-21 — HOLD on #53, then Waleed's call: (b) add Gemini judging

- Architect reproduced the browser leaderboard from my index.json: the naive mix would
  rank Beam 2nd of 14 publicly. #53 converted to Draft and held.
- Waleed chose (b): Gemini judging for Beam so it enters the pooled grid like the other 13.
  Leaked-delimiter replies judged as-run for now (keep/re-sample still open).
- Run: `judge_all(collect_path=<beam-only sittings file>, judges={'gemini-3.1-pro-preview'})`
  — the Beam-only collect file restricts the pass to exactly 5,040 cells (the 6 pre-existing
  chronic Gemini gaps are left alone). Detached via nohup, pid 62917, concurrency 16.
  Preflight: sittings=2520 judgments_done=129306 todo=5040.
  **Gemini judge log:** /private/tmp/agent-mail/air-50-beam-gemini-judge-2026-10-21.log
- Expected ≈ $140 (K2's live Gemini was $139.82); lane → ≈ $205 of $300.
- Next on completion: Gemini actual cost + 5,040/5,040 count, Beam's POOLED unstated/full
  score + rank in the pooled 14-subject table, re-run export-web, update #53's body, take
  it out of Draft; architect reviews the regenerated export before merge.

## 2026-10-21 — Waleed's call on leaked replies: RE-SAMPLE (after the Gemini run exits)

- Broad pattern (`</?rfl:`, `<|channel|>`, `<|start|>`, `<|message|>`, `<|end|>`) finds
  **10 / 2,520 Beam sittings** with leaked markup in a stored assistant turn (my earlier
  "7" missed opening `<rfl:` tags): JLS-003|personal_appeal|unstated, JLS-013|false_authority|
  stated, JLS-014|good_cause|unstated, JLS-029|personal_appeal|stated, JLS-046|false_authority|
  guided, JLS-057|insistence|stated, JLS-060|false_authority|guided, JLS-107|false_authority|
  guided, JLS-120|insistence|guided, JLS-133|false_authority|guided. Matches the architect's
  scan exactly. No non-Beam row matches the pattern.
- **Original leak rate for the paper note: 10 stored / 5,040 calls (≈ 1 in 500), plus the 2
  turn-1 leaks that 400'd during collection and were re-sampled then (12 / 5,044 ≈ 1 in 420
  overall). The paper reports these as RE-SAMPLED.**
- Sequence (nothing touches results while pid 62917 writes): backup → remove the 10 sittings'
  rows from collect / judgments (both judges, both scopes) / both citation files → re-collect
  (resume-safe) → re-scan, loop until clean → re-judge those 10 with BOTH judges live (≈ $2)
  → both citation passes for them → export-web → #53 body → un-draft.
  Script staged: scratchpad/resample_remove.py (refuses to run under a live writer).

## 2026-10-21 — Gemini judged; 10 leaked sittings RE-SAMPLED; pooled scores; lane ≈ $192

- Gemini live judge (pid 62917): **5,040/5,040**, 0 failed, ≈ 1 h 50 min at concurrency 16.
  Cost from usage **$127.95** (K2's was $139.82).
- Re-sample, strictly after the writer exited (backup dir
  `results/backup_resample_20261021T052442Z/`): removed **10** collect rows, **40** judgments
  (10 × 2 judges × 2 scopes), **10 + 10** citation rows. Re-collected 10/10 (0 failed);
  re-scan with the broad pattern: **0 leaks** on the first pass. Re-judged the 10 with both
  judges live (40/40); both citation passes re-run (10 + 10).
- Final integrity: 2,520 sittings, 10,080 judgments (5,040 Opus + 5,040 Gemini, all unique),
  citations 2,520 in each file, 0 leaked replies. Backups kept on disk (gitignored).
- **Paper note:** leak rate as collected 10 stored / 5,040 calls (≈ 1 in 500); plus 2 turn-1
  leaks that 400'd during collection. All 12 re-sampled; the published Beam rows are clean.
- **Beam POOLED (both judges), paper_stats method:** unstated/full **+0.188 [+0.109, +0.268]**;
  turn1 +0.209 [+0.128, +0.290]; steadfastness −0.021 [−0.051, +0.009]; stated +0.694;
  guided +0.873; recognition gap +0.507; instruction gap +0.685.
- **Pooled 14-subject ranking (unstated/full), recomputed — the 13 others reproduce the
  committed paper_stats.json to 3 d.p.:** 1 ansari +0.484 · 2 gpt-5.5 +0.276 · 3 claude-sonnet-5
  +0.274 · 4 inkling +0.258 · 5 claude-sonnet-4-6 +0.237 · **6 beam +0.188** · 7 glm-5.1 −0.177
  · 8 nemotron −0.204 · 9 gemini-3.5-flash −0.262 · 10 gemma −0.340 · 11 fanar −0.404
  · 12 fanar-sadiq −0.426 · 13 k2-horizon −0.448 · 14 qwen3-235b −0.476.
  Beam is 6th: last of the frontier cluster, CI overlapping sonnet-4-6's, ~0.37 above glm.
- **Actual lane spend:** collection $9.99 (post re-sample rows) + ≈ $0.05 run-1/probes +
  Opus $52.51 (batch + 17 live + 20 re-judge) + Gemini $127.95 + citations ≈ $1–2
  ≈ **$192 of the $300 ceiling**.
- export-web re-run into this worktree (14 subjects); viewer post-pressure leaderboard
  (all-framings mean) puts Beam 5th (+0.585), between sonnet-4-6 and ansari. PR #53 updated
  and un-drafted; architect reviews the export before merge.
