# air-1 — Issue #1: pytest test suite (offline, mocked providers)

Protocol: AIR (strict). No spec/plan; review goes in the PR body.

## Plan
Add `pytest` + `pytest-asyncio` dev deps to `jaleesbench/pyproject.toml`; tests in `jaleesbench/tests/`.

Coverage targets (from issue):
- Pure units: `collect.sitting_key`, `collect.ctx_block`, `collect.load_probes`,
  `judge.parse_judgment`, `judge.judgment_key`, `prompts.render_conversation`,
  `prompts.judge_blocks` / `judge_blocks_ar`, `score.fmt` (band→[-1,+1]) + `score.load_judgments` v2 overlay.
- Provider seam (fake async clients): `providers.openai/anthropic/gemini_complete`,
  `providers.make_clients(which=)`, `collect.call_subject` (routing + ctx fold + anthropic cache
  layout + retry-then-raise), `judge.call_judge` (routing + parse + usage).

Hermetic strategy: monkeypatch `collect.DATA` / `score.RESULTS` to tmp dirs (never touch canonical
data or `results/`); monkeypatch `prompts._ar_prompts`; fake clients capture call kwargs; patch
`asyncio.sleep` to a no-op for the retry test.

## Log
- Read all five target modules; understood the provider seam. Starting implementation.
- Added `pytest` + `pytest-asyncio` dev deps via `uv add --dev`; configured
  `asyncio_mode = "auto"` + `testpaths = ["tests"]` in pyproject.
- Wrote 4 test files (conftest fakes + units + providers + seam), 45 tests.
  `uv run pytest` → 45 passed. Only warning is a third-party google-genai/py3.14
  DeprecationWarning, not from our code.
- No canonical data or `results/` touched: tests monkeypatch `collect.DATA` /
  `score.RESULTS` to tmp dirs and `prompts._ar_prompts` to a canned dict.
- No production logic changed beyond pyproject dev deps + pytest config.

## BLOCKED (porch check mismatch) — 2026-06-17
Committed as `54b6dbf`. `porch check 1` FAILS because AIR's skeleton
`protocol.json` implement-phase checks are hardwired to npm:
  - build → `npm run build`
  - tests → `npm test -- --exclude='**/e2e/**'`
This repo is Python/uv — no npm. These checks can never pass here. Not a flaky
test and not a defect in my work; the suite itself is green (`uv run pytest` →
45 passed from `jaleesbench/`).

Per role: not editing status.yaml, not bypassing/skipping checks. Escalated to
architect. Recommended fix: project-local `codev/protocols/air/protocol.json`
override (resolution tier 2) pointing the implement-phase checks at uv, e.g.
  - tests → `uv run --directory jaleesbench pytest -q`
  - build → a real check or no-op (Python has no compile step; "build" needs an
    architect decision — `uv build --directory jaleesbench`? drop it?).
Waiting for guidance before re-running `porch check 1` / `porch done 1`.

## UNBLOCKED + PR ready — 2026-06-17
Architect added project-local `codev/protocols/air/protocol.json` on main
(implement check → `uv run --directory jaleesbench pytest -q`; build dropped;
e2e no-op). Merged origin/main into builder/air-1 (clean, single new file).
protocol.json kept OUT of PR scope (already on main).

- `porch check 1` → tests ✓. `porch done 1` → advanced to PR phase.
- Pushed branch; opened **PR #2** (review in the body, per AIR — no review file).
- PR-phase checks: `pr_exists` ✓, `e2e_tests` ✓ (no-op).
- `porch done 1` → `porch gate 1` → **WAITING on `pr` gate (human approval)**.
  Not calling `porch approve` (human-only). Notified architect.
