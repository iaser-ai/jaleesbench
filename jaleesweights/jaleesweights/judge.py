"""Judging — the two judges never meet.

  opus           Score held-out collections with Claude Opus (the held-out judge), both scopes:
                 first response and after pushback. Needs ANTHROPIC_API_KEY only.
  gemini-select  Rate a guided training-half collection with Gemini (the selection judge),
                 both scopes — the stage-1 filter needs the first-turn band too. Needs a
                 Gemini credential only.
  rate-samples   Rate the stage-1 model's K sampled answers with Gemini, after-pushback scope
                 only (selection uses that band alone; judging both scopes would double the
                 spend). Chain-aware: records carrying a `chain` field are rated under
                 `<subject>-c<chain>`. Needs a Gemini credential only.

All three are resume-safe: judgments already in the output file are not redone, so pointed
at a complete reference output they report nothing to do and make no call. Every command
prints what it is about to do — how many judgments, which judge, which account is billed —
and `--dry-run` stops there.

    uv run python -m jaleesweights.judge opus --collect data/runs/my-run/collect_eval_gemma.jsonl --run my-run
"""

import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path

import typer
from jaleesbench.collect import load_probes
from jaleesbench.judge import call_judge, judge_all, judgment_key
from jaleesbench.prompts import judge_blocks, render_conversation
from jaleesbench.providers import make_clients

from . import paths
from .common import GEMINI, OPUS
from .env import load_keys

app = typer.Typer(add_completion=False, help=__doc__)

ANTHROPIC_KEYS = ["ANTHROPIC_API_KEY"]


def _sittings(path: Path) -> list[dict]:
    return [json.loads(l) for l in path.read_text().splitlines()]


def _done(out: Path) -> set[str]:
    if not out.exists():
        return set()
    return {judgment_key(json.loads(l)) for l in out.read_text().splitlines()}


def pending_two_scope(collect: Path, out: Path, judge: str) -> int:
    """How many judgments judge_all would make: two scopes per sitting, minus those done."""
    done = _done(out)
    n = 0
    for s in _sittings(collect):
        skey = f"{s['subject']}|{s['probe_id']}|{s['pressure']}|{s['framing']}"
        n += sum(1 for scope in ("turn1", "full") if f"{skey}|{judge}|{scope}" not in done)
    return n


def _preflight(collects: list[Path], out: Path, judge: str, account: str, scopes: str, counter) -> int:
    total = 0
    for c in collects:
        if not c.exists():
            raise typer.BadParameter(f"{c} does not exist")
        n = counter(c, out, judge)
        typer.echo(f"  {c.name}: {len(_sittings(c))} sittings, {n} judgments to make")
        total += n
    typer.echo(f"preflight: judge {judge}, {scopes}; {total} judgments to make -> {out}; "
               f"billed to your {account} account")
    return total


def _run_two_scope(collects: list[Path], out: Path, judge: str, required: list[str],
                   concurrency: int | None) -> None:
    for c in collects:
        asyncio.run(judge_all(collect_path=c, out_path=out, judges={judge},
                              required_keys=required, concurrency=concurrency))


@app.command()
def opus(
    collect: list[Path] = typer.Option(..., "--collect", help="Held-out collection(s) to score (harness record schema)."),
    run: str = typer.Option("new-run", help="Run directory name under data/runs/ for the output."),
    out: Path | None = typer.Option(None, help="Judgments file to append to (default: <run dir>/judgments_eval.jsonl)."),
    concurrency: int | None = typer.Option(None, help="Concurrent judge calls (default: the benchmark's)."),
    dry_run: bool = typer.Option(False, "--dry-run", help="Print the preflight summary and stop."),
) -> None:
    out = paths.output_path(out or paths.run_dir(run) / "judgments_eval.jsonl")
    load_keys(ANTHROPIC_KEYS)
    total = _preflight(collect, out, OPUS, "Anthropic", "both scopes", pending_two_scope)
    if dry_run or total == 0:
        return
    _run_two_scope(collect, out, OPUS, ANTHROPIC_KEYS, concurrency)


@app.command("gemini-select")
def gemini_select(
    collect: list[Path] = typer.Option(..., "--collect", help="Guided training-half collection(s) to rate."),
    run: str = typer.Option("new-run", help="Run directory name under data/runs/ for the output."),
    out: Path | None = typer.Option(None, help="Ratings file to append to (default: <run dir>/judgments_selection.jsonl)."),
    concurrency: int | None = typer.Option(None, help="Concurrent judge calls (default: the benchmark's)."),
    dry_run: bool = typer.Option(False, "--dry-run", help="Print the preflight summary and stop."),
) -> None:
    out = paths.output_path(out or paths.run_dir(run) / "judgments_selection.jsonl")
    load_keys([], gemini=True)
    total = _preflight(collect, out, GEMINI, "Gemini (Vertex or API key)", "both scopes", pending_two_scope)
    if dry_run or total == 0:
        return
    _run_two_scope(collect, out, GEMINI, [], concurrency)


# --- rate-samples: Gemini, after-pushback scope only, chain-aware ----------------------------

def sample_lane(s: dict) -> str:
    return f"{s['subject']}-c{s['chain']}" if "chain" in s else s["subject"]


def pending_samples(collect: Path, out: Path, judge: str = GEMINI) -> int:
    done = _done(out)
    n = 0
    for s in _sittings(collect):
        skey = f"{sample_lane(s)}|{s['probe_id']}|{s['pressure']}|{s['framing']}"
        if f"{skey}|{judge}|full" not in done:
            n += 1
    return n


async def rate_samples_async(collect: Path, out: Path, concurrency: int) -> None:
    probes = {p["id"]: p for p in load_probes()["probes"]}
    sittings = _sittings(collect)
    done = _done(out)
    jobs = []
    for s in sittings:
        subj = sample_lane(s)
        skey = f"{subj}|{s['probe_id']}|{s['pressure']}|{s['framing']}"
        if f"{skey}|{GEMINI}|full" not in done:
            jobs.append((s, subj, skey))
    typer.echo(f"sittings={len(sittings)} done={len(done)} todo={len(jobs)}")
    if not jobs:
        return

    clients = make_clients({"gemini"})
    sem = asyncio.Semaphore(concurrency)
    lock = asyncio.Lock()
    completed = failed = 0

    async def one(job):
        nonlocal completed, failed
        s, subj, skey = job
        parts = judge_blocks(probes[s["probe_id"]]["proof_texts"], render_conversation(s["turns"]))
        try:
            async with sem:
                verdict = await call_judge(GEMINI, parts, clients)
        except Exception as e:  # noqa: BLE001 — skip, report; a re-run retries it
            async with lock:
                failed += 1
                typer.echo(f"  FAILED {skey}: {e}")
            return
        rec = {"sitting_key": skey, "subject": subj, "probe_id": s["probe_id"],
               "pressure": s["pressure"], "framing": s["framing"],
               "judge": GEMINI, "scope": "full",
               "ts": datetime.now(timezone.utc).isoformat(), **verdict}
        async with lock:
            with open(out, "a") as fh:
                fh.write(json.dumps(rec) + "\n")
            completed += 1
            if completed % 50 == 0:
                typer.echo(f"  {completed}/{len(jobs)}")

    await asyncio.gather(*[one(j) for j in jobs])
    typer.echo(f"judged {completed} -> {out}" + (f"  ({failed} failed, re-run to retry)" if failed else ""))
    if failed:
        raise typer.Exit(1)


@app.command("rate-samples")
def rate_samples(
    collect: Path = typer.Option(..., help="The stage-1 model's sampled answers (K per training cell)."),
    run: str = typer.Option("new-run", help="Run directory name under data/runs/ for the output."),
    out: Path | None = typer.Option(None, help="Ratings file to append to (default: <run dir>/judgments_samples.jsonl)."),
    concurrency: int = typer.Option(16, help="Concurrent judge calls."),
    dry_run: bool = typer.Option(False, "--dry-run", help="Print the preflight summary and stop."),
) -> None:
    out = paths.output_path(out or paths.run_dir(run) / "judgments_samples.jsonl")
    load_keys([], gemini=True)
    total = _preflight([collect], out, GEMINI, "Gemini (Vertex or API key)", "after-pushback scope only", pending_samples)
    if dry_run or total == 0:
        return
    asyncio.run(rate_samples_async(collect, out, concurrency))


if __name__ == "__main__":
    app()
