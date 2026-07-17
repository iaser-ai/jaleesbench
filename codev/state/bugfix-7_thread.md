# bugfix-7 thread — Issue #7: export_web stale polarizing-preset test + zero-spread guard

## Investigate (2026-07-17)

Reproduced both halves of the issue with a scratch script driving `export_web`
against the test fixture's synthetic data:

- **Stale test**: `test_presets_polarizing_present_and_empty_omitted` (skipped in
  PR #6) asserts full-scope semantics (`a=ansari`, `b=gpt-5.5` from full-scope
  spread), but since commit 986165e the polarizing preset ranks on turn-1 spread.
- **Self-pairing**: the fixture gives every subject turn-1 band = 1, so spread is
  zero and `max`/`min` both resolve to `ansari` → the exporter emits
  `"ansari vs ansari"` entries with `params.a == params.b`.

**Browser-UX check for the zero-spread guard** (issue work item 2): the browser
(`apps/jaleesbrowser/src/guided.ts`) computes its own "Models split" list in-app
from the score blob and only consumes the *exported* presets for the
"judges-differed" list (`/judg/i.test(p.key)`). The exported polarizing preset is
never rendered, so skipping zero-spread cells cannot regress the UI — and an
`X vs X` entry is meaningless for any other contract consumer. **Decision: add
the guard** (skip cells where hi and lo scores are equal).

Fix plan (small, well within BUGFIX scope):
1. `export_web.py::_compute_presets`: in the spreads loop, `continue` when
   `d[hi] == d[lo]` (zero spread).
2. Test fixture: give gpt-5.5 turn-1 band = −1 (ansari stays +1) so turn-1 has
   real spread. Only other fixture-band-sensitive assertions are ansari-side
   (`scores["data"][1] == 0.5`, `overall.initial == 0.5`) — unaffected.
3. Un-skip the test; assert turn-1 semantics (`a=ansari`, `b=gpt-5.5`,
   `scope=turn1`) and add a regression test for the zero-spread guard
   (degenerate turn-1 → polarizing preset omitted, no self-pairing).
