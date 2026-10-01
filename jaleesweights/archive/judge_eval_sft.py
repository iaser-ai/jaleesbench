"""Opus-judge the SL-CAI stage-1 (gemma-sft-guided) eval sittings.

Usage: uv run --directory jaleesbench python ../tmp/dpo-experiment/judge_eval_sft.py
"""

import asyncio
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent.parent / "jaleesbench"))

from jaleesbench.judge import judge_all  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent

asyncio.run(
    judge_all(
        collect_path=ROOT / "collect_eval_sft.jsonl",
        out_path=ROOT / "judgments_eval_gemma.jsonl",
        judges={"claude-opus-4-8"},
    )
)
