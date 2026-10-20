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
