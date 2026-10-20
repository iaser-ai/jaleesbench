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
