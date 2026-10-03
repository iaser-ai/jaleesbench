# air-38 thread

## 2026-10-03 implement
- Issue #38: added `.github/workflows/tests.yml` — one job, matrix over `jaleesbench` and `jaleesweights`, each running `uv run --directory <project> pytest -q` on pull requests and pushes to main.
- No new tests: the change is workflow config only. The proof is the workflow's own run on the PR (Linux, fresh clone, no gitignored data).
- Local (macOS): jaleesbench 112 passed / 1 skipped; jaleesweights 114 passed / 1 skipped.
