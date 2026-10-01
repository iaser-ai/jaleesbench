# Lessons Learned

Durable engineering wisdom captured across the project's work. Update it during the review
phase of any work that surfaces a generally-applicable pattern, gotcha, or constraint.

## Publishing from a public repository

- Private wording must be removed **before the first commit**. A clean final tree is not
  enough: history is published with it. Search `git log -p <base>..HEAD` for the forbidden
  patterns, not just the working tree, and do it before pushing (issue #36).
- Build release archives deterministically (sorted members, zeroed metadata, gzip mtime 0)
  so a rebuild gives the same checksum and the committed checksum list stays honest.
- Files that "look like lockfile diffs" may not be: the `code.diff` records of the Tinker
  cookbook carried diffs of unrelated repository files, including an architect state file.
  Inspect what a tool captured before deciding it is harmless.

## Porting as-run research code

- Commit the as-run text first, at the final path, then port in later commits: every change
  is then a reviewable diff against what produced the published numbers, with no duplicate
  "original" files in the tree.
- Prove deterministic steps by byte-identity against frozen outputs before touching the
  paid steps; a port that reproduces 316 / 310 / 502 / 672 rows byte for byte needs no
  argument.
- A bootstrap that iterates a Python set is not repeatable across runs (string hashing
  varies). Sort the keys. Expect printed intervals from such code to be unrecoverable.
- When the data a step reads has a companion overlay (here `judgments_v2.jsonl`), decide
  explicitly which one the port reads and say so; the benchmark's own tests depend on the
  overlay being present.

## Tooling

- `uv` installs a path dependency non-editable unless told otherwise; a package that
  resolves data paths from its module location must be installed editable.
- A `[tool.uv.sources]` index entry for `torch` scoped to a dependency group still leaks
  into the default graph on the same platform, because uv resolves one torch per platform.
  Unless a special CUDA build is really required, let torch come from PyPI.
- `modal run <app> --help` works without an account; `modal run <app> <args>` does not —
  it needs a token before the local entrypoint runs. Free preflights need a plain-Python entry.
- During a 3-way review round, do not edit the tree: the lanes read the worktree live and
  will report half-applied edits as bugs.
- Background `consult` lanes were killed repeatedly (exit 144, no output) late in a long
  session while the same commands completed in the foreground; when a lane dies without
  writing its file, re-run it in the foreground.
