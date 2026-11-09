"""Experiment 58 — Opus judging through the Anthropic batch API (half price), after-pushback
scope only: one judgment per sitting.

The request is the benchmark's own (same rubric, proof texts and cache breakpoints as
`jaleesbench.batching`); what differs is the file locations, one judge, one scope. Records
have the benchmark's judgment shape, with usage marked batch=True.

  submit  send every sitting not yet judged and not in a batch still in flight
  fetch   write the results of finished batches; requests that failed stay pending
  cost    usage-computed spend of the judgments on file

    uv run python experiments/58_prompt_fading/judge_batch.py submit --run fading-58 --dry-run
"""

import json
from datetime import datetime, timezone
from pathlib import Path

import typer
from jaleesbench.collect import load_probes
from jaleesbench.judge import JUDGE_MAX_TOKENS, judgment_key, parse_judgment
from jaleesbench.prompts import judge_blocks, render_conversation
from jaleesbench.score import add_usage, usage_cost

from jaleesweights import paths
from jaleesweights.common import OPUS
from jaleesweights.env import load_keys

SCOPE = "full"
CHUNK = 10_000

app = typer.Typer(add_completion=False, help=__doc__)


def _files(run: str) -> tuple[Path, Path, Path]:
    d = paths.run_dir(run)
    return d / "collect_fading.jsonl", paths.output_path(d / "judgments_fading.jsonl"), paths.output_path(d / "batch_state.json")


def _lines(p: Path) -> list[dict]:
    return [json.loads(l) for l in p.read_text().splitlines() if l.strip()] if p.exists() else []


def _state(p: Path) -> list[dict]:
    return json.loads(p.read_text()) if p.exists() else []


@app.command()
def submit(run: str = typer.Option("fading-58"),
           dry_run: bool = typer.Option(False, "--dry-run", help="Print the preflight summary and stop.")) -> None:
    collect, jpath, spath = _files(run)
    sittings = _lines(collect)
    done = {judgment_key(j) for j in _lines(jpath)}
    state = _state(spath)
    for b in state:
        if not b["done"]:
            done.update(b["manifest"].values())
    jobs = []
    for s in sittings:
        key = f"{s['subject']}|{s['probe_id']}|{s['pressure']}|{s['framing']}|{OPUS}|{SCOPE}"
        if key not in done:
            jobs.append((s, key))
    typer.echo(f"preflight: {len(sittings)} sittings, {len(jobs)} judgments to submit; judge {OPUS}, "
               f"after-pushback scope, batch API; billed to your Anthropic account -> {jpath}")
    if dry_run or not jobs:
        return
    load_keys(["ANTHROPIC_API_KEY"])
    import anthropic
    client = anthropic.Anthropic()
    probes = {p["id"]: p for p in load_probes()["probes"]}
    for c0 in range(0, len(jobs), CHUNK):
        manifest, requests = {}, []
        for i, (s, key) in enumerate(jobs[c0:c0 + CHUNK]):
            parts = judge_blocks(probes[s["probe_id"]]["proof_texts"], render_conversation(s["turns"]))
            cid = f"f{len(state):02d}_{c0 + i:06d}"
            manifest[cid] = key
            requests.append({"custom_id": cid, "params": {
                "model": OPUS, "max_tokens": JUDGE_MAX_TOKENS,
                "messages": [{"role": "user", "content": [
                    {"type": "text", "text": parts[0], "cache_control": {"type": "ephemeral", "ttl": "1h"}},
                    {"type": "text", "text": parts[1], "cache_control": {"type": "ephemeral", "ttl": "1h"}},
                    {"type": "text", "text": parts[2]},
                ]}]}})
        batch = client.messages.batches.create(requests=requests)
        state.append({"batch_id": batch.id, "manifest": manifest, "done": False})
        spath.write_text(json.dumps(state, indent=1))
        typer.echo(f"batch {batch.id}: {len(requests)} requests")


@app.command()
def fetch(run: str = typer.Option("fading-58")) -> None:
    _, jpath, spath = _files(run)
    state = _state(spath)
    load_keys(["ANTHROPIC_API_KEY"])
    import anthropic
    client = anthropic.Anthropic()
    open_batches = 0
    for b in state:
        if b["done"]:
            continue
        batch = client.messages.batches.retrieve(b["batch_id"])
        if batch.processing_status != "ended":
            typer.echo(f"{b['batch_id']}: {batch.processing_status} ({batch.request_counts.processing} processing)")
            open_batches += 1
            continue
        have = {judgment_key(j) for j in _lines(jpath)}
        wrote = failed = 0
        with open(jpath, "a") as fh:
            for result in client.messages.batches.results(b["batch_id"]):
                key = b["manifest"][result.custom_id]
                if result.result.type != "succeeded":
                    failed += 1
                    continue
                msg = result.result.message
                try:
                    verdict = parse_judgment("".join(x.text for x in msg.content if x.type == "text"))
                except ValueError:
                    failed += 1
                    continue
                u = msg.usage
                verdict["usage"] = {"in": u.input_tokens, "out": u.output_tokens,
                                    "cache_write": getattr(u, "cache_creation_input_tokens", 0) or 0,
                                    "cache_read": getattr(u, "cache_read_input_tokens", 0) or 0,
                                    "batch": True}
                subject, probe_id, pressure, framing, judge, scope = key.split("|")
                rec = {"sitting_key": f"{subject}|{probe_id}|{pressure}|{framing}", "subject": subject,
                       "probe_id": probe_id, "pressure": pressure, "framing": framing,
                       "judge": judge, "scope": scope,
                       "ts": datetime.now(timezone.utc).isoformat(), **verdict}
                if judgment_key(rec) not in have:
                    fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
                    wrote += 1
        b["done"] = True
        spath.write_text(json.dumps(state, indent=1))
        typer.echo(f"{b['batch_id']}: wrote {wrote}, failed {failed} (failed ones are pending again; run submit)")
    typer.echo(f"{open_batches} batch(es) still in flight" if open_batches else "no batch in flight")
    if open_batches:
        raise typer.Exit(2)


@app.command()
def cost(run: str = typer.Option("fading-58")) -> None:
    _, jpath, _ = _files(run)
    acc: dict = {}
    js = _lines(jpath)
    for j in js:
        add_usage(acc, j["usage"])
    usd = usage_cost(OPUS, acc)
    typer.echo(f"{len(js)} judgments; tokens {acc}; ${usd:.4f} (${usd / max(1, len(js)):.5f} each)")


if __name__ == "__main__":
    app()
