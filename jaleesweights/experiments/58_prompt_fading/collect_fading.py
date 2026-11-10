"""Experiment 58 — collector for the prompt-fading design on JaleesBench.

Adapted from the collector of the MultiBench prompt-fading experiment 78. One structural
departure from the benchmark's own collector: the arm's framing is delivered ONCE, as the
opening system message (the benchmark folds it into every user turn), and value-neutral
filler separates it from the dilemma at six levels. The stored turns are the clean
turn1/reply1/push/reply2 exchange in the benchmark's record schema, so the benchmark's judge
code scores them unchanged and never sees the framing or the filler.

Arms (stored as `subject`), levels (stored as `framing`):
  fading-P  base google/gemma-4-31B-it + the JaleesBench guide as the system message
  fading-W  JaleesWeights stage 2 (served as "stage2") + the stated sentence as the system message
  fading-B0 base model, no system message          (follow-up arm; pass --arms to collect)
  fading-W0 JaleesWeights stage 2, no system message (follow-up arm; pass --arms to collect)
  L0..L5    0, ~1k, ~4k, ~12k, ~32k, >=64k Gemma tokens of filler (see filler_levels.json)

Scenarios: the 70 held-out probes x 6 pressures, read from the reference inputs file the
JaleesWeights evaluations used, so the turn texts are those of the existing unprompted control.

Sampling: the model's own generation defaults, sent explicitly, as in the JaleesWeights
collections. Resume-safe: cells already in the output file are skipped.

    uv run python experiments/58_prompt_fading/collect_fading.py --base-url https://<modal-url>/v1 --dry-run
Smoke: add  --probes-limit 2 --pressures secularize --run fading-58-smoke
"""

import json
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from itertools import groupby
from pathlib import Path

import typer
from jaleesbench.prompts import GUIDE, STATED

from jaleesweights import paths

HERE = Path(__file__).resolve().parent

BASE_MODEL = "google/gemma-4-31B-it"
ARMS = {
    "fading-P": {"model": BASE_MODEL, "framing_source": "guide", "system": GUIDE},
    "fading-W": {"model": "stage2", "framing_source": "stated", "system": STATED},
    # Follow-up arms (registered after the first result, before their own data): no framing
    # at all, so the conversation opens with the filler, or with the dilemma at L0.
    "fading-B0": {"model": BASE_MODEL, "framing_source": "none", "system": None},
    "fading-W0": {"model": "stage2", "framing_source": "none", "system": None},
}
DEFAULT_ARMS = "fading-P,fading-W"
LEVELS = ["L0", "L1", "L2", "L3", "L4", "L5"]

# The model's generation_config.json (temperature 1.0, top-p 0.95, top-k 64): what the
# JaleesWeights collections sample with. Sent with every request so a server default cannot
# drift from it. Reply cap as in those collections.
SAMPLING = {"temperature": 1.0, "top_p": 0.95, "max_tokens": 8192, "seed": 3446}
EXTRA_BODY = {"top_k": 64}

app = typer.Typer(add_completion=False, help=__doc__)


def load_filler(bank: Path, levels: Path) -> dict[str, tuple[list[dict], int]]:
    """level -> (pre-filled user/assistant turns, Gemma tokens). Each level is the first N
    exchanges of the bank, so a level's filler is a prefix of the next level's."""
    import re
    pairs = []
    for block in bank.read_text().split("### exchange")[1:]:
        um = re.search(r"USER:\s*(.*?)\s*(?=\nASSISTANT:)", block, re.S)
        am = re.search(r"\nASSISTANT:\s*(.*)", block, re.S)
        pairs.append((um.group(1).strip(), am.group(1).strip()))
    spec = json.loads(levels.read_text())["levels"]
    out = {}
    for lv in LEVELS:
        n = spec[lv]["exchanges"]
        if n > len(pairs):
            raise SystemExit(f"{lv} needs {n} exchanges; the bank has {len(pairs)}")
        turns = []
        for u, a in pairs[:n]:
            turns += [{"role": "user", "content": u}, {"role": "assistant", "content": a}]
        out[lv] = (turns, spec[lv]["tokens"])
    return out


def cell_key(arm: str, probe_id: str, pressure: str, level: str) -> str:
    return f"{arm}|{probe_id}|{pressure}|{level}"


def make_caller(base_url: str, retries: int):
    from openai import OpenAI
    client = OpenAI(api_key="EMPTY", base_url=base_url, timeout=1800)

    def call(model: str, messages: list[dict]) -> tuple[str, dict]:
        last = None
        for attempt in range(retries + 1):
            try:
                r = client.chat.completions.create(model=model, messages=messages,
                                                   extra_body=EXTRA_BODY, **SAMPLING)
                choice = r.choices[0]
                if choice.finish_reason != "stop":
                    raise RuntimeError(f"finish_reason={choice.finish_reason!r} (reply not complete)")
                text = (choice.message.content or "").strip()
                if not text:
                    raise RuntimeError("empty reply")
                details = getattr(r.usage, "prompt_tokens_details", None)
                return text, {"prompt_tokens": r.usage.prompt_tokens,
                              "completion_tokens": r.usage.completion_tokens,
                              "cached_tokens": getattr(details, "cached_tokens", None) if details else None}
            except Exception as e:  # noqa: BLE001 — retry, then fail the cell loudly
                last = e
                if attempt < retries:
                    time.sleep(5 * (attempt + 1))
        raise RuntimeError(f"failed after {retries + 1} attempts: {last}")

    return call


def run_cell(arm: str, level: str, row: dict, filler: list[dict], filler_tokens: int, call) -> dict:
    spec = ARMS[arm]
    head = ([{"role": "system", "content": spec["system"]}] if spec["system"] else []) + filler
    turn1, push = row["turn1"], row["pressure_text"]
    t0 = time.time()
    reply1, u1 = call(spec["model"], head + [{"role": "user", "content": turn1}])
    reply2, u2 = call(spec["model"], head + [{"role": "user", "content": turn1},
                                              {"role": "assistant", "content": reply1},
                                              {"role": "user", "content": push}])
    return {
        # the benchmark's record schema: what the judge keys on and reads
        "subject": arm, "probe_id": row["probe_id"], "pressure": row["pressure"], "framing": level,
        "model": spec["model"], "context_prefix": None,
        "ts": datetime.now(timezone.utc).isoformat(), "attempts": [1, 1],
        "usage": [u1, u2],
        "turns": [{"role": "user", "content": turn1}, {"role": "assistant", "content": reply1},
                  {"role": "user", "content": push}, {"role": "assistant", "content": reply2}],
        # experiment audit, ignored by the judge
        "arm": arm, "level": level, "framing_source": spec["framing_source"],
        "framing_channel": "system" if spec["system"] else None, "filler_tokens": filler_tokens,
        "filler_turns": len(filler), "sampling": {**SAMPLING, **EXTRA_BODY},
        "seconds": round(time.time() - t0, 1),
    }


@app.command()
def main(
    base_url: str = typer.Option(..., help="The served endpoint, ending in /v1."),
    run: str = typer.Option("fading-58", help="Run directory name under data/runs/."),
    inputs: Path | None = typer.Option(None, help="Held-out inputs (default: the reference eval_inputs_gemma.jsonl)."),
    arms: str = typer.Option(DEFAULT_ARMS),
    levels: str = typer.Option(",".join(LEVELS)),
    pressures: str = typer.Option("", help="Comma list (default: all six)."),
    probes_limit: int = typer.Option(0, help="If >0, the first N probes only (smoke)."),
    concurrency: int = typer.Option(16),
    retries: int = typer.Option(3),
    dry_run: bool = typer.Option(False, "--dry-run", help="Print the preflight summary and stop."),
) -> None:
    arm_list = [a for a in arms.split(",") if a]
    level_list = [l for l in levels.split(",") if l]
    for a in arm_list:
        if a not in ARMS:
            raise typer.BadParameter(f"unknown arm {a!r}")
    for l in level_list:
        if l not in LEVELS:
            raise typer.BadParameter(f"unknown level {l!r}")

    rows = [json.loads(l) for l in (inputs or paths.reference_file("eval_inputs_gemma.jsonl")).read_text().splitlines() if l.strip()]
    if len(rows) != 420 or len({r["probe_id"] for r in rows}) != 70:
        raise SystemExit(f"expected the 420 held-out cells (70 probes x 6 pressures), got {len(rows)}")
    if pressures:
        want = set(pressures.split(","))
        rows = [r for r in rows if r["pressure"] in want]
    if probes_limit:
        keep = list(dict.fromkeys(r["probe_id"] for r in rows))[:probes_limit]
        rows = [r for r in rows if r["probe_id"] in keep]

    filler = load_filler(HERE / "filler_bank.md", HERE / "filler_levels.json")
    out = paths.output_path(paths.run_dir(run) / "collect_fading.jsonl")
    done = set()
    if out.exists():
        for line in out.read_text().splitlines():
            s = json.loads(line)
            done.add(cell_key(s["subject"], s["probe_id"], s["pressure"], s["framing"]))

    # Ordered by arm, then level: every cell of a group shares one long prefix (system
    # message + filler), which the server's prefix cache then computes once.
    cells = [(a, lv, r) for a in arm_list for lv in level_list for r in rows
             if cell_key(a, r["probe_id"], r["pressure"], lv) not in done]
    typer.echo(f"preflight: {len(cells)} sittings to collect ({len(done)} already in {out}); "
               f"2 generations each; endpoint {base_url}; billed to your Modal account (GPU time)")
    for lv in level_list:
        typer.echo(f"  {lv}: {filler[lv][1]:>6} filler tokens, {len(filler[lv][0]) // 2} exchanges")
    typer.echo(f"  arms {arm_list}; sampling {SAMPLING} {EXTRA_BODY}; concurrency {concurrency}")
    if dry_run or not cells:
        typer.echo("dry run: stopping before any call" if dry_run else "nothing to do")
        return

    call = make_caller(base_url, retries)
    lock = threading.Lock()
    counts = {"written": 0, "failed": 0}
    fh = out.open("a")

    def one(cell) -> None:
        a, lv, r = cell
        turns, ntok = filler[lv]
        try:
            rec = run_cell(a, lv, r, turns, ntok, call)
        except Exception as e:  # noqa: BLE001 — left pending; a re-run retries it
            with lock:
                counts["failed"] += 1
            typer.echo(f"  FAILED {cell_key(a, r['probe_id'], r['pressure'], lv)}: {e}")
            return
        with lock:
            fh.write(json.dumps(rec, sort_keys=True) + "\n")
            fh.flush()
            counts["written"] += 1

    for (a, lv), group in groupby(cells, key=lambda c: (c[0], c[1])):
        group = list(group)
        t0 = time.time()
        one(group[0])  # alone first, so the shared prefix is in the cache before the rest fan out
        with ThreadPoolExecutor(max_workers=max(1, concurrency)) as ex:
            list(ex.map(one, group[1:]))
        dt = time.time() - t0
        typer.echo(f"[{a} {lv}] {len(group)} sittings in {dt:.0f}s ({len(group) / dt * 3600:.0f}/h); "
                   f"written {counts['written']}, failed {counts['failed']}")
    fh.close()
    typer.echo(f"done: written {counts['written']}, failed {counts['failed']} -> {out}")
    if counts["failed"]:
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
