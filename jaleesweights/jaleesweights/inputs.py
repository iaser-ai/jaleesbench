"""Conversation inputs for both halves of the split, from the benchmark main run.

Each row is one (scenario, pressure) cell: the opening user turn and the authored
pressure turn, which are identical across subjects within a cell (asserted; the step fails
if they are not). The training half drives sampling and the Inkling-Small guided
collection; the held-out half drives every evaluation collection. The file names carry
"gemma" for continuity with the runs of record, but the rows are model-independent.

Ordering reproduces the frozen files exactly: the training half sorted by (scenario,
pressure), the held-out half in the split's scenario order × the bank's pressure order.

    uv run python -m jaleesweights.inputs --run my-run
"""

import hashlib
import json
from pathlib import Path

import typer
from jaleesbench.collect import load_probes

from . import paths
from .common import load_split

app = typer.Typer(add_completion=False, help=__doc__)

CELLS_PER_HALF = 420  # 70 scenarios x 6 pressures


def build(collect_path: Path, split: dict) -> dict[str, list[dict]]:
    train, test = set(split["train"]), set(split["test"])
    buckets: dict[str, dict] = {"train": {}, "test": {}}
    with open(collect_path) as fh:
        for line in fh:
            r = json.loads(line)
            if r["framing"] != "unstated":
                continue
            side = "train" if r["probe_id"] in train else "test" if r["probe_id"] in test else None
            if side is None:
                continue
            row = {
                "probe_id": r["probe_id"],
                "pressure": r["pressure"],
                "turn1": r["turns"][0]["content"],
                "pressure_text": r["turns"][2]["content"],
            }
            key = (r["probe_id"], r["pressure"])
            prev = buckets[side].get(key)
            if prev is None:
                buckets[side][key] = row
            elif prev != row:
                raise RuntimeError(f"cell {key} differs across subjects ({r['subject']})")
    for side, cells in buckets.items():
        if len(cells) != CELLS_PER_HALF:
            raise RuntimeError(f"{side}: expected {CELLS_PER_HALF} cells, got {len(cells)}")
    pressures = [p["id"] if isinstance(p, dict) else p for p in load_probes()["pressures"]]
    return {
        "train": [buckets["train"][k] for k in sorted(buckets["train"])],
        "test": [buckets["test"][(pid, pr)] for pid in split["test"] for pr in pressures],
    }


def write_jsonl(rows: list[dict], out: Path) -> str:
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w") as fh:
        for r in rows:
            fh.write(json.dumps(r) + "\n")
    return hashlib.sha256(out.read_bytes()).hexdigest()


@app.command()
def main(
    run: str = typer.Option("new-run", help="Run directory name under data/runs/ for the outputs."),
    collect: Path | None = typer.Option(None, help="Main-run collect.jsonl (default: the installed main run)."),
) -> None:
    collect_path = collect or paths.main_run_file("collect.jsonl")
    out_dir = paths.run_dir(run)
    halves = build(collect_path, load_split())
    mismatched = []
    for side, name in (("train", "train_inputs_gemma.jsonl"), ("test", "eval_inputs_gemma.jsonl")):
        out = out_dir / name
        sha = write_jsonl(halves[side], out)
        typer.echo(f"{len(halves[side])} rows -> {out}  sha256 {sha}")
        ref = paths.REFERENCE / name
        if ref.exists():
            same = hashlib.sha256(ref.read_bytes()).hexdigest() == sha
            typer.echo(f"  {'identical to' if same else 'DIFFERS FROM'} reference {ref.name}")
            if not same:
                mismatched.append(name)
    if mismatched:
        # The inputs are derived from the main run; a difference means the main run
        # installed here is not the one the runs of record used.
        raise RuntimeError(f"rebuilt inputs differ from the reference copies: {', '.join(mismatched)}")


if __name__ == "__main__":
    app()
