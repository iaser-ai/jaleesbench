# ===== as-run: judge_train_samples.py =====
"""Selection-judge the on-policy sampled sittings (issue #21 gemma redesign).

Gemini only (the selection judge — Opus stays held out for eval), and ONLY
the post-pressure (full) scope: selection uses post-pressure bands alone, and
judge_all's hardcoded two-scope loop would double the spend for bands we
never read. Mirrors judge_all's job loop otherwise, resume-safe via the same
judgment key set.

Usage: uv run --directory jaleesbench python ../tmp/dpo-experiment/judge_train_samples.py
"""

import asyncio
import json
import pathlib
import sys
from datetime import datetime, timezone

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent.parent / "jaleesbench"))

from jaleesbench.collect import load_env, load_probes  # noqa: E402
from jaleesbench.judge import call_judge, judgment_key  # noqa: E402
from jaleesbench.prompts import judge_blocks, render_conversation  # noqa: E402
from jaleesbench.providers import make_clients  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent
GEMINI = "gemini-3.1-pro-preview"
CONCURRENCY = 16

import os  # noqa: E402

COLLECT = ROOT / os.environ.get("COLLECT", "collect_train_samples.jsonl")
OUT = ROOT / os.environ.get("OUT", "judgments_train_samples.jsonl")


async def main() -> None:
    load_env()
    probes = {p["id"]: p for p in load_probes()["probes"]}
    sittings = [json.loads(l) for l in COLLECT.read_text().splitlines()]

    done: set[str] = set()
    if OUT.exists():
        for line in OUT.read_text().splitlines():
            done.add(judgment_key(json.loads(line)))

    jobs = []
    for s in sittings:
        # Chain-aware: K-chain census files carry a 'chain' field on a single
        # subject; fold it into the subject (gemma's files pre-suffixed theirs).
        subj = f"{s['subject']}-c{s['chain']}" if "chain" in s else s["subject"]
        skey = f"{subj}|{s['probe_id']}|{s['pressure']}|{s['framing']}"
        if f"{skey}|{GEMINI}|full" not in done:
            jobs.append((s, subj, skey))
    print(f"sittings={len(sittings)} done={len(done)} todo={len(jobs)}")
    if not jobs:
        return

    clients = make_clients({"gemini"})
    sem = asyncio.Semaphore(CONCURRENCY)
    lock = asyncio.Lock()
    completed = failed = 0

    async def one(job):
        nonlocal completed, failed
        s, subj, skey = job
        parts = judge_blocks(probes[s["probe_id"]]["proof_texts"],
                             render_conversation(s["turns"]))
        try:
            async with sem:
                verdict = await call_judge(GEMINI, parts, clients)
        except Exception as e:  # noqa: BLE001 — skip, report; a re-run retries it
            async with lock:
                failed += 1
                print(f"  FAILED {skey}: {e}")
            return
        rec = {"sitting_key": skey, "subject": subj, "probe_id": s["probe_id"],
               "pressure": s["pressure"], "framing": s["framing"],
               "judge": GEMINI, "scope": "full",
               "ts": datetime.now(timezone.utc).isoformat(), **verdict}
        async with lock:
            with open(OUT, "a") as fh:
                fh.write(json.dumps(rec) + "\n")
            completed += 1
            if completed % 50 == 0:
                print(f"  {completed}/{len(jobs)}")

    await asyncio.gather(*[one(j) for j in jobs])
    print(f"judged {completed} -> {OUT}" + (f"  ({failed} failed, re-run to retry)" if failed else ""))
    if failed:
        raise SystemExit(1)


asyncio.run(main())

# ===== as-run: judge_eval_basevllm.py =====
"""Opus-judge the base-gemma vLLM control sittings (no adapter).

The control isolates tuning effects from vLLM-vs-Friendli serving drift and
single-sample bistability in every arm-vs-base comparison. Appends to
judgments_eval_gemma.jsonl (resume-safe, new subject).

Usage: uv run --directory jaleesbench python ../tmp/dpo-experiment/judge_eval_basevllm.py
"""

import asyncio
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent.parent / "jaleesbench"))

from jaleesbench.judge import judge_all  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent

asyncio.run(
    judge_all(
        collect_path=ROOT / "collect_eval_basevllm.jsonl",
        out_path=ROOT / "judgments_eval_gemma.jsonl",
        judges={"claude-opus-4-8"},
    )
)

# ===== as-run: judge_eval_bf16.py =====
"""Opus-judge the bf16 recipe-of-record stage-1 evals (bare + guided guard).

Usage: uv run --directory jaleesbench python ../tmp/dpo-experiment/judge_eval_bf16.py
"""

import asyncio
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent.parent / "jaleesbench"))

from jaleesbench.judge import judge_all  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent

for name in ("collect_eval_bf16.jsonl", "collect_eval_bf16_guided.jsonl"):
    asyncio.run(
        judge_all(
            collect_path=ROOT / name,
            out_path=ROOT / "judgments_eval_gemma.jsonl",
            judges={"claude-opus-4-8"},
        )
    )

# ===== as-run: judge_eval_sftdpo_bf16.py =====
"""Opus-judge the bf16 recipe-of-record stage-2 eval (bare only).

Usage: uv run --directory jaleesbench python ../tmp/dpo-experiment/judge_eval_sftdpo_bf16.py
"""

import asyncio
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent.parent / "jaleesbench"))

from jaleesbench.judge import judge_all  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent

asyncio.run(
    judge_all(
        collect_path=ROOT / "collect_eval_sftdpo_bf16.jsonl",
        out_path=ROOT / "judgments_eval_gemma.jsonl",
        judges={"claude-opus-4-8"},
    )
)

# ===== as-run: judge_small_selection.py =====
"""Gemini-judge Inkling-Small's train-70 guided sittings (selection judge,
both scopes — the SFT filter needs full AND turn1 bands).

Usage: uv run --directory jaleesbench python ../tmp/dpo-experiment/judge_small_selection.py
"""

import asyncio
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent.parent / "jaleesbench"))

from jaleesbench.judge import judge_all  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent

asyncio.run(
    judge_all(
        collect_path=ROOT / "collect_small_train_guided.jsonl",
        out_path=ROOT / "judgments_small_selection.jsonl",
        judges={"gemini-3.1-pro-preview"},
    )
)

# ===== as-run: judge_small_baselines.py =====
"""Opus-judge Inkling-Small's two test-70 baselines (unstated + guided),
sequentially into one held-out judgments file.

Usage: uv run --directory jaleesbench python ../tmp/dpo-experiment/judge_small_baselines.py
"""

import asyncio
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent.parent / "jaleesbench"))

from jaleesbench.judge import judge_all  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent

for which in ("test_unstated", "test_guided"):
    asyncio.run(
        judge_all(
            collect_path=ROOT / f"collect_small_{which}.jsonl",
            out_path=ROOT / "judgments_eval_small.jsonl",
            judges={"claude-opus-4-8"},
        )
    )

# ===== as-run: judge_small_sft.py =====
"""Opus-judge Inkling-Small's stage-1 SFT test-70 evals (unstated + guided),
sequentially into the shared held-out judgments file.

Usage: uv run --directory jaleesbench python ../tmp/dpo-experiment/judge_small_sft.py
"""

import asyncio
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent.parent / "jaleesbench"))

from jaleesbench.judge import judge_all  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent

for which in ("test_unstated", "test_guided"):
    asyncio.run(
        judge_all(
            collect_path=ROOT / f"collect_small_{which}_sft.jsonl",
            out_path=ROOT / "judgments_eval_small.jsonl",
            judges={"claude-opus-4-8"},
        )
    )

# ===== as-run: judge_small_sftdpo.py =====
"""Opus-judge Inkling-Small's stage-2 (sft-dpo) test-70 unstated eval into the
shared held-out judgments file.

Usage: uv run --directory jaleesbench python ../tmp/dpo-experiment/judge_small_sftdpo.py
"""

import asyncio
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent.parent / "jaleesbench"))

from jaleesbench.judge import judge_all  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent

asyncio.run(
    judge_all(
        collect_path=ROOT / "collect_small_test_unstated_sftdpo.jsonl",
        out_path=ROOT / "judgments_eval_small.jsonl",
        judges={"claude-opus-4-8"},
    )
)
