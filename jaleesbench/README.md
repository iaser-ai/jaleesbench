# JaleesBench pilot harness

See ../docs/jaleesbench-design.md for the design.

- `uv run jaleesbench smoke` — 2 sittings, verify keys/model ids
- `uv run jaleesbench collect` — run the full 360-sitting grid (resumable)
- `uv run jaleesbench judge` — score sittings with both judges at both turns
- `uv run jaleesbench report` — aggregate into the pilot report
