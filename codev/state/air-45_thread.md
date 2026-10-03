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

## 2026-10-03 owner feedback on PR #46: tutorial cut to the short demo only
- Owner's final shape: warning, install, ask base, fine-tune, ask again, short hadith caution.
  Removed from TUTORIAL.md: the JLS-078 worked example, the which-model / 31B / 12B notes, the
  differences-from-the-recipe table, memory discipline, scaling up, the five-stage table, the
  loss figures and the resumed-run story. `ask` and its tests unchanged; `scenario` stays in the
  code, unmentioned by the tutorial. Stale pointers to removed sections fixed in the README and
  two code comments.
- Demo question now ends "Keep it to 200 words." Regenerated both answers (generation only).
  **Surprise: with the 200-word limit the two-pass answer no longer mentions riba or Islam at
  all.** It changes voice only ("Sit with me for a moment", "check your heart", "come back to
  me"). Also tried on the two-pass adapter: "Keep it short." (42 tokens, no riba), "Keep it to
  300 words." (no riba), "Answer in 200 words or less." (no riba). Only the question without a
  length limit brings out riba. The tutorial says this in plain words and quotes the unlimited
  answer's riba line in one sentence. Flagged to the architect as the owner's call.
- Hadith caution uses the "doubt" question (no length limit): two invented sayings shown, both
  confirmed not found (Ansari), with Sahih Muslim 132 ("That is clear faith") beside them. With
  "Keep it to 200 words." appended, the doubt answer invents three different sayings and loops
  to the token cap, ignoring the limit; not used in the tutorial.
- Detail removed from the tutorial, kept here: two-pass run = 500 steps, interrupted, resumed
  740 from the step-500 checkpoint with a reshuffled order and fresh optimizer; ~19 + ~25 min,
  12.1 GB peak; loss per 100 steps 1.98 -> 1.76 over the first 500, 1.50 over the last 40.
  Bank question without a limit by stage: base / 300 / 500 steps career coaching, 800 steps
  first invented saying, 1,240 steps riba plus one invented and one real hadith (Tirmidhi 3895).
