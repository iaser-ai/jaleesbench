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
