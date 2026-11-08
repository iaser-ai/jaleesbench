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
