# air-9 — Bucket A+B: mechanical + editorial fixes from multibench audit (issue #9)

## 2026-07-19 — Implement

- AIR strict mode; porch in Implement phase. Implemented all 15 items inline
  (small interdependent edits across one package — parallel mutation would conflict);
  ultracode opt-in honored with a multi-agent review workflow over the diff before PR.
- **Item 3 checkpoint**: `commentary.json` IS consumed by `html_report.py`
  (optionally, `exists()`-guarded; jaleesbrowser does not use it). Asked architect
  per the issue's stop-and-ask clause; architect approved untrack+gitignore
  (2026-07-20T02:10Z) — fresh clones must stop getting numbers contradicting the paper.
- Gitignored inputs (`prompts_ar.json`, `tmp/paper_stats.py`, results data) absent
  from this fresh worktree — sourced from the main checkout read-only.
- Retag result: islamic split is now **clean 54 / leaky 44 / intrinsic 42**
  (was 58/40/42). probes.json v2→v3 with version_note; probes_ar.json gains
  version:2 + note (renders EN v2 texts; v3 changed tags only).
- `paper_stats.py` promoted to `jaleesbench/paper_stats.py`; verified runnable via
  `uv run python -m jaleesbench.paper_stats` against main-checkout results data:
  scorecard matches the paper; citation clean/leaky columns shift exactly as the
  issue predicts (architect regenerates Table 2 + web export post-merge). Committed
  `results/paper_stats.json` is the current paper-matching artifact, not the
  post-retag rerun — deliberate, so the artifact tracks the published paper until
  the architect regenerates both together.
- `load_env()` rewritten: repo-root `.env` only, already-set env wins, fails naming
  missing KEYS. claude-opus-4-8 removed from SUBJECTS (stays a judge; comment notes
  the paper's ten-subject grid).
- `judge --lang ar` routes to `collect_ar.jsonl`/`judgments_ar.jsonl`, mirroring
  `batching._cfg` so AR judgments never mix into the EN files.
- Tests: 66 passed, 1 pre-existing skip. New: load_env behavior, CLI flag wiring
  (typer CliRunner + monkeypatch), judge_all SystemExit(1) on partial failure,
  probe-bank v3 data assertions, AR prompts shipped in data/.

## 2026-07-19 — Review (ultracode workflow) + PR

- Ran a 4-dimension multi-agent review (wiring / scope / data / tests) with
  adversarial verification over the diff (6 agents, ~286k tokens). Two confirmed
  findings, both fixed in 6855924:
  1. paper_stats.py executed its whole bootstrap at import and clobbered the
     tracked artifact on bare import — wrapped in main() + __main__ guard.
  2. Committed paper_stats.json is pre-retag (deliberate: tracks the published
     paper until the architect regenerates post-merge) — now disclosed in the
     PR body; the module's hardcoded Table 2 sanity numbers were softened.
- Minors fixed: --lang validates against {en, ar}; pinning test for the
  ten-subject grid. Minor accepted as-is: numpy stays a dev-group dep (the
  module needs unshipped results data anyway; `uv run` syncs dev by default).
- Data dimension verified: exactly four islamic tags changed, no text rewording,
  prompts_ar.json byte-identical to source; final suite 69 passed / 1 skip.
