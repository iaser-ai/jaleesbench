"""Inkling-Small collections through the Tinker OpenAI-compatible endpoint.

Four passes, each over one half of the split:
  train-guided    training half, guide folded into every user turn  (stage-1 teacher pool)
  train-unstated  training half bare                                (with --k 4: stage-2 sampling)
  test-unstated   held-out half bare                                (the baseline / an evaluation)
  test-guided     held-out half with guide                          (the ceiling / guided guard)

Harness conventions kept: the guide folds into EVERY user message at request time; stored
turns stay clean with `context_prefix` recorded separately. Reasoning model: the answer is in
`message.content`, the hidden pass in `reasoning_content` (not stored, matching the main
run); ample max_tokens. Account-wide in-flight cap ~30-40 -> concurrency 22 by default,
patient retries. Resume-safe (append + done set); K>1 makes each chain its own unit.

A tuned checkpoint is collected by passing its sampler address as --model and a new
--subject (the adapter lane is thinner than the base lane: lower --concurrency).

    uv run python -m jaleesweights.collect_small train-guided --run my-run
    uv run python -m jaleesweights.collect_small test-unstated --run my-run \\
        --model tinker://<your stage-1 checkpoint>/sampler_weights/final --subject inkling-small-sft --concurrency 3
"""

import asyncio
import json
import os
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path

import typer
from openai import AsyncOpenAI

from . import paths
from .env import load_keys

app = typer.Typer(add_completion=False, help=__doc__)

TINKER_URL = "https://tinker.thinkingmachines.dev/services/tinker-prod/oai/api/v1"
DEFAULT_MODEL = "thinkingmachines/Inkling-Small"
MAX_TOKENS = 12288
RETRIES = 6


class Pass(str, Enum):
    train_guided = "train-guided"
    train_unstated = "train-unstated"
    test_unstated = "test-unstated"
    test_guided = "test-guided"


def pass_inputs(which: Pass) -> tuple[str, str]:
    """(default inputs file name, framing) for a pass."""
    half = "train" if which.value.startswith("train") else "eval"
    framing = "guided" if which.value.endswith("guided") else "unstated"
    return f"{half}_inputs_gemma.jsonl", framing


def done_units(out_path: Path) -> set[tuple]:
    if not out_path.exists():
        return set()
    return {(r["probe_id"], r["pressure"], r.get("chain", 0))
            for r in (json.loads(l) for l in out_path.read_text().splitlines())}


def plan(inputs_path: Path, out_path: Path, k: int) -> tuple[list[dict], int]:
    rows = [dict(json.loads(l), chain=c) for l in open(inputs_path) for c in range(k)]
    done = done_units(out_path)
    todo = [r for r in rows if (r["probe_id"], r["pressure"], r["chain"]) not in done]
    return todo, len(rows)


async def collect(todo: list[dict], out_path: Path, model: str, subject: str, framing: str,
                  prefix: str | None, concurrency: int) -> None:
    def fold(text: str) -> str:
        return f"{prefix}\n\n{text}" if prefix else text

    client = AsyncOpenAI(base_url=TINKER_URL, api_key=os.environ["TINKER_API_KEY"], timeout=600)
    sem = asyncio.Semaphore(concurrency)
    lock = asyncio.Lock()
    completed = failed = 0

    async def call(messages):
        last = None
        for attempt in range(RETRIES + 1):
            try:
                r = await client.chat.completions.create(model=model, messages=messages, max_tokens=MAX_TOKENS)
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
                typer.echo(f"  FAILED {r['probe_id']}|{r['pressure']}: {e}")
            return
        rec = {
            "subject": subject, "probe_id": r["probe_id"], "pressure": r["pressure"],
            "chain": r["chain"],
            "framing": framing, "model": model,
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
                typer.echo(f"  {completed}/{len(todo)}")

    await asyncio.gather(*[one(r) for r in todo])
    typer.echo(f"collected {completed}, failed {failed} -> {out_path}")
    if failed:
        raise typer.Exit(1)


@app.command()
def main(
    which: Pass = typer.Argument(..., help="Which pass to collect."),
    run: str = typer.Option("new-run", help="Run directory name under data/runs/ for the output."),
    inputs: Path | None = typer.Option(None, help="Conversation inputs file (default: the reference inputs for the half)."),
    model: str = typer.Option(DEFAULT_MODEL, help="Model id or tinker:// sampler address of a tuned checkpoint."),
    subject: str = typer.Option("inkling-small", help="Subject name stamped on every record."),
    k: int = typer.Option(1, help="Independent chains per cell (4 for the stage-2 sampling pass)."),
    concurrency: int = typer.Option(22, help="Concurrent conversations (use ~3 for a tuned checkpoint's lane)."),
    out: Path | None = typer.Option(None, help="Output file (default: <run dir>/collect_small_<pass>[_<subject suffix>].jsonl)."),
    dry_run: bool = typer.Option(False, "--dry-run", help="Print the preflight summary and stop."),
) -> None:
    default_inputs, framing = pass_inputs(which)
    inputs_path = inputs or paths.reference_file(default_inputs)
    if out is None:
        suffix = "" if subject == "inkling-small" else "_" + subject.removeprefix("inkling-small-")
        if k > 1:
            suffix += f"_k{k}"
        out = paths.run_dir(run) / f"collect_small_{which.value.replace('-', '_')}{suffix}.jsonl"
    out_path = paths.output_path(out)
    load_keys(["TINKER_API_KEY"])
    prefix = paths.GUIDED_PREFIX.read_text().strip() if framing == "guided" else None
    todo, units = plan(inputs_path, out_path, k)
    typer.echo(f"preflight: {which.value} ({framing}) from {inputs_path.name}: {units} units "
               f"({k} chain{'s' if k != 1 else ''}/cell), {units - len(todo)} done, {len(todo)} to collect")
    typer.echo(f"  model {model}, subject {subject}, concurrency {concurrency} -> {out_path}; "
               f"billed to your Tinker account")
    if dry_run or not todo:
        return
    asyncio.run(collect(todo, out_path, model, subject, framing, prefix, concurrency))


if __name__ == "__main__":
    app()
