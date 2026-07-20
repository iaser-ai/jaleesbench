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
