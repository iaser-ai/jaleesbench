"""Judge the held-out eval sittings with Opus only (the held-out judge).

Live (non-batch) judging: 420 sittings x 1 judge x 2 scopes = 840 judgments,
small enough that batch turnaround isn't worth the coupling to the main-run
result files. Resume-safe via judge_all's own done-set.

Usage: uv run --directory jaleesbench python ../tmp/dpo-experiment/judge_eval.py
"""

import asyncio
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent.parent / "jaleesbench"))

from jaleesbench.judge import judge_all  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent

asyncio.run(
    judge_all(
        collect_path=ROOT / "collect_eval.jsonl",
        out_path=ROOT / "judgments_eval.jsonl",
        judges={"claude-opus-4-8"},
    )
)
