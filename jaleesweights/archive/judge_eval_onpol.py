"""Judge the on-policy arm's held-out eval sittings with Opus only.

Same held-out-judge protocol as the prior arms; appends to
judgments_eval_gemma.jsonl (judge_all's done-set makes this resume-safe and
collision-free — the subject is new).

Usage: uv run --directory jaleesbench python ../tmp/dpo-experiment/judge_eval_onpol.py
"""

import asyncio
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent.parent / "jaleesbench"))

from jaleesbench.judge import judge_all  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent

asyncio.run(
    judge_all(
        collect_path=ROOT / "collect_eval_onpol.jsonl",
        out_path=ROOT / "judgments_eval_gemma.jsonl",
        judges={"claude-opus-4-8"},
    )
)
