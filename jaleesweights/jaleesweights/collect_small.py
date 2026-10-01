"""Inkling-Small collections for the JaleesWeights replication (issue #21).

Three passes over the Tinker OAI endpoint (base lane, default sampling):
  train_guided   — train-70, guide folded into every user turn (SFT teacher pool)
  test_unstated  — test-70 bare (the model's own baseline)
  test_guided    — test-70 with guide (the model's own ceiling)

Harness conventions kept: the guide folds into EVERY user message at request
time; stored turns stay clean with context_prefix recorded separately.
Reasoning model: answer in message.content, hidden pass in reasoning_content
(not stored, matching the main run); ample max_tokens. Account-wide in-flight
cap ~30-40 -> concurrency 22, patient retries. Resume-safe (append + done-set).

Usage: uv run --directory jaleesbench python ../tmp/dpo-experiment/collect_small.py <pass>
       where <pass> is train_guided | test_unstated | test_guided
"""

import asyncio
import json
import os
import pathlib
import sys
from datetime import datetime, timezone

from openai import AsyncOpenAI

ROOT = pathlib.Path(__file__).resolve().parent
# Env overrides let the same driver collect from a tuned tinker:// checkpoint
# (adapter lane is thinner than base — drop concurrency accordingly).
MODEL = os.environ.get("SMALL_MODEL", "thinkingmachines/Inkling-Small")
SUBJECT = os.environ.get("SMALL_SUBJECT", "inkling-small")
CONCURRENCY = int(os.environ.get("SMALL_CONCURRENCY", "22"))
MAX_TOKENS = 12288
RETRIES = 6

PASSES = {
    "train_guided": (ROOT / "train_inputs_gemma.jsonl", "guided"),
    "train_unstated": (ROOT / "train_inputs_gemma.jsonl", "unstated"),
    "test_unstated": (ROOT / "eval_inputs_gemma.jsonl", "unstated"),
    "test_guided": (ROOT / "eval_inputs_gemma.jsonl", "guided"),
}
# K>1 draws K independent chains per cell (stage-2 sampling census); each
# chain is its own resume unit and is stamped into the record.
K = int(os.environ.get("SMALL_K", "1"))

which = sys.argv[1]
inputs_path, framing = PASSES[which]
suffix = os.environ.get("SMALL_OUT_SUFFIX", "")
out_path = ROOT / f"collect_small_{which}{suffix}.jsonl"

for line in pathlib.Path("/Users/mwk/Development/fftn/taqwabench/.env").read_text().splitlines():
    if line.startswith("TINKER_API_KEY"):
        os.environ["TINKER_API_KEY"] = line.split("=", 1)[1].strip().strip("\"'")

prefix = (ROOT / "guided_prefix.txt").read_text().strip() if framing == "guided" else None


def fold(text: str) -> str:
    return f"{prefix}\n\n{text}" if prefix else text


async def main() -> None:
    rows = [dict(json.loads(l), chain=c) for l in open(inputs_path) for c in range(K)]
    done = set()
    if out_path.exists():
        for line in out_path.read_text().splitlines():
            r = json.loads(line)
            done.add((r["probe_id"], r["pressure"], r.get("chain", 0)))
    todo = [r for r in rows if (r["probe_id"], r["pressure"], r["chain"]) not in done]
    print(f"{which}: {len(rows)} units ({K} chains/cell), {len(done)} done, {len(todo)} todo")
    if not todo:
        return

    client = AsyncOpenAI(
        base_url="https://tinker.thinkingmachines.dev/services/tinker-prod/oai/api/v1",
        api_key=os.environ["TINKER_API_KEY"], timeout=600,
    )
    sem = asyncio.Semaphore(CONCURRENCY)
    lock = asyncio.Lock()
    completed = failed = 0

    async def call(messages):
        last = None
        for attempt in range(RETRIES + 1):
            try:
                r = await client.chat.completions.create(
                    model=MODEL, messages=messages, max_tokens=MAX_TOKENS)
                content = r.choices[0].message.content
                if not content or not content.strip():
                    raise RuntimeError("empty content (reasoning may have eaten the budget)")
                return content, {"prompt_tokens": r.usage.prompt_tokens,
                                 "completion_tokens": r.usage.completion_tokens}, attempt + 1
            except Exception as e:  # noqa: BLE001
                last = e
                if attempt < RETRIES:
                    await asyncio.sleep(30 * (attempt + 1))
        raise RuntimeError(f"failed after {RETRIES + 1} attempts: {last}")

    async def one(r):
        nonlocal completed, failed
        try:
            async with sem:
                m1 = [{"role": "user", "content": fold(r["turn1"])}]
                a1, u1, n1 = await call(m1)
                m2 = m1 + [{"role": "assistant", "content": a1},
                           {"role": "user", "content": fold(r["pressure_text"])}]
                a2, u2, n2 = await call(m2)
        except Exception as e:  # noqa: BLE001
            async with lock:
                failed += 1
                print(f"  FAILED {r['probe_id']}|{r['pressure']}: {e}", flush=True)
            return
        rec = {
            "subject": SUBJECT, "probe_id": r["probe_id"], "pressure": r["pressure"],
            "chain": r["chain"],
            "framing": framing, "model": MODEL,
            "context_prefix": prefix,
            "ts": datetime.now(timezone.utc).isoformat(),
            "attempts": [n1, n2], "usage": [u1, u2],
            "turns": [
                {"role": "user", "content": r["turn1"]},
                {"role": "assistant", "content": a1},
                {"role": "user", "content": r["pressure_text"]},
                {"role": "assistant", "content": a2},
            ],
        }
        async with lock:
            with open(out_path, "a") as fh:
                fh.write(json.dumps(rec, sort_keys=True) + "\n")
            completed += 1
            if completed % 25 == 0:
                print(f"  {completed}/{len(todo)}", flush=True)

    await asyncio.gather(*[one(r) for r in todo])
    print(f"{which}: collected {completed}, failed {failed} -> {out_path}")
    if failed:
        raise SystemExit(1)


asyncio.run(main())
