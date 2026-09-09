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
