# air-45 thread: tutorial quick demo (free-text question) and do-not-use warning

## 2026-10-03 implement
- New sibling command `jaleesweights.mlx.ask "<question>" [--adapter <dir>]`: one user turn,
  thinking off, greedy, same preflight / `--dry-run` / named missing-`mlx_lm` message as
  `scenario`. Prints the answer and writes nothing. A reply that reaches `--max-tokens` is
  printed as far as it got and then the command exits non-zero (decision: `scenario` refuses a
  capped reply outright, but here a non-stopping answer is the thing to show, not hide).
- No training run. Generation only, one model at a time, from the adapters already trained on
  this machine (the 300-step tutorial adapter; the two-pass run's checkpoints at 500, 800 and
  1,240 steps).
- Re-ran the bank question at all five stages. Matches the issue's table, with two additions:
  the 800-step checkpoint already invents a saying of the Prophet (and calls it "a general
  principle, not a direct quote" in the same breath), and the two-pass answer carries one
  invented hadith and one real one (Tirmidhi 3895), side by side.
- "Is it a sin to doubt God sometimes?" on the two-pass adapter: four invented sayings, then
  the last repeated 74 more times until the 2,048-token cap (the issue said ten; it does not
  stop on its own).
- The quoted sayings were checked against the collections through Ansari before the tutorial
  labels any of them invented or real.
- The two-pass adapter came from an interrupted-and-resumed run (500 steps, then 740 from the
  checkpoint with a reshuffled order and fresh optimizer); the tutorial says so. Time and
  memory from its logs: about 45 minutes, 12.1 GB peak; loss per 100 steps 1.98 -> 1.76 over
  the first 500, 1.50 over the last 40.
- TUTORIAL.md: caution block under the title; Quick demo section after "What you need"; the
  JLS-078 walkthrough stays as the longer worked example.
- Pre-existing, unrelated: `tests/test_local_demo.py::test_collect_preflight_names_pass_and_output`
  fails in this worktree and passes under a different pytest temp directory; its assertion reads
  an error message through Typer's wrapped box, so it depends on the temp path's length. Left
  alone; reported in the PR.
