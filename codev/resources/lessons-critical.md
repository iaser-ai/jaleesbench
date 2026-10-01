# lessons-critical.md — Always-On Engineering Wisdom (HOT tier)

<!-- HOT tier: capped lessons + a bounded map of lessons-learned.md. Always injected into
every porch phase prompt and into CLAUDE.md/AGENTS.md. CAP: <=10 lessons, <=12 map topics,
<=35 lines. To add a lesson, DEMOTE a weaker one into lessons-learned.md (displacement).
MAINTAIN polices the cap and keeps the map in sync with lessons-learned.md's sections.
STARTER: a few universal lessons are seeded; add your project's as you learn them. -->

## Critical lessons (consult before deciding)
- Check for existing work (PRs, git history) before building from scratch.
- "It compiled" / "tests pass" is not "it works" — verify the real user path before calling it done.
- When stuck (2 failed hypotheses or ~30 min), get an outside perspective instead of guessing.
- This repository is public: private wording must be gone before the first commit, and the check is over `git log -p`, not the tree.
- Port research code by committing the as-run text first and proving the free steps byte-identical before touching anything paid.
- Do not edit the tree while a 3-way review round is running; the lanes read it live.

## Map of lessons-learned.md (consult when…)
- Publishing from a public repository — consult before committing or releasing anything that came from scratch files or another team.
- Porting as-run research code — consult when turning scripts into a package without re-running them.
- Tooling — consult when `uv`, `modal` or `consult` behave unexpectedly.
