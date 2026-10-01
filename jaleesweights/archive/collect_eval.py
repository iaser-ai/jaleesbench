"""Collect held-out-70 sittings from a tuned Inkling checkpoint (issue #21).

Reuses the harness's run_sitting/make_clients wholesale — same retries, same
patient tinker backoff, same record shape — but registers the checkpoint as a
new subject and writes to its own results file. Resume-safe by sitting_key.

Usage:
  uv run --directory jaleesbench python ../tmp/dpo-experiment/collect_eval.py <subject> [framing ...]

Subjects are defined in CHECKPOINTS below; framings default to unstated.
"""

import asyncio
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent.parent / "jaleesbench"))

from jaleesbench import collect  # noqa: E402
from jaleesbench.providers import make_clients  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent
OUT = ROOT / "collect_eval.jsonl"
# Sampler-path (LoRA adapter) serving sustains far less concurrency than the
# base model — 40 in flight stalled to ~1 record/40min while training shared
# the account. Overridable for tuning.
CONCURRENCY = int(__import__("os").environ.get("EVAL_CONCURRENCY", "3"))

CHECKPOINTS = {
    "inkling-dpo-r1": "tinker://fdee7166-f738-5344-920e-5f49a9b9ac29:train:0/sampler_weights/final",
    "inkling-dpo-r2": "tinker://12e251d0-6c35-5bce-9af1-a1aec4fa4352:train:0/sampler_weights/final",
}


async def main(subject: str, framings: list[str]) -> None:
    collect.load_env()
    collect.SUBJECTS[subject] = {
        "provider": "tinker",
        "model": CHECKPOINTS[subject],
        "framings": framings,
    }
    split = json.loads((ROOT / "split_70_70.json").read_text())
    probes = {p["id"]: p for p in collect.load_probes()["probes"]}
    pressures = [
        p["id"] if isinstance(p, dict) else p
        for p in collect.load_probes()["pressures"]
    ]

    done = set()
    if OUT.exists():
        for line in open(OUT):
            done.add(collect.sitting_key(json.loads(line)))

    todo = [
        (probes[pid], pr, fr)
        for pid in split["test"]
        for pr in pressures
        for fr in framings
        if f"{subject}|{pid}|{pr}|{fr}" not in done
    ]
    print(f"{subject}: {len(todo)} sittings to collect ({len(done)} already done)")
    if not todo:
        return

    clients = make_clients({"tinker"})
    # Wedged-connection mitigation: the default 600s timeout leaves dead reads
    # hanging for 10 min per attempt. Override to recycle them faster.
    t = float(__import__("os").environ.get("TINKER_TIMEOUT", "0"))
    if t:
        clients["tinker"] = clients["tinker"].with_options(timeout=t)
    sem = asyncio.Semaphore(CONCURRENCY)
    lock = asyncio.Lock()
    n_ok = 0

    async def one(probe, pressure, framing):
        nonlocal n_ok
        rec = await collect.run_sitting(subject, probe, pressure, framing, sem, clients)
        async with lock:
            with open(OUT, "a") as fh:
                fh.write(json.dumps(rec) + "\n")
            n_ok += 1
            if n_ok % 20 == 0:
                print(f"progress: {n_ok}/{len(todo)}")

    results = await asyncio.gather(
        *(one(p, pr, fr) for p, pr, fr in todo), return_exceptions=True
    )
    errs = [r for r in results if isinstance(r, Exception)]
    print(f"done: {n_ok} ok, {len(errs)} failed")
    for e in errs[:5]:
        print("ERR:", str(e)[:200])
    if errs:
        sys.exit(1)


if __name__ == "__main__":
    subj = sys.argv[1]
    frs = sys.argv[2:] or ["unstated"]
    asyncio.run(main(subj, frs))
