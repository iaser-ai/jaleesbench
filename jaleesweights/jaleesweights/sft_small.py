"""Stage-1 training set from a model's OWN guided collection (Inkling-Small, and the local
Gemma demonstration): the same filters and screens as `sft_guided`, sourced from a
collection this pipeline made rather than from the benchmark main run.

Writes the training set and, beside it, the same conversations in the Tinker trainer's
`{"messages": [...]}` form (what the as-run pipeline produced by hand).

    uv run python -m jaleesweights.sft_small --run my-run \\
        --collect data/reference/collect_small_train_guided.jsonl \\
        --judgments data/reference/judgments_small_selection.jsonl
"""

import collections
import hashlib
import json
from pathlib import Path

import typer

from . import paths
from .common import GEMINI, GUIDE_REF, dangling_markers, load_split

app = typer.Typer(add_completion=False, help=__doc__)


def build(collect_path: Path, judgments_path: Path, subject: str, split: dict | None = None):
    train = set((split or load_split())["train"])
    bands: dict = {}
    turn1_bands: dict = {}
    for line in open(judgments_path):
        j = json.loads(line)
        if j["judge"] == GEMINI and j["framing"] == "guided" and j["subject"] == subject:
            key = (j["probe_id"], j["pressure"])
            if j["scope"] == "full":
                bands[key] = j["band"]
            else:
                turn1_bands[key] = j["band"]

    band_hist = collections.Counter(bands.values())
    rows = []
    stats = collections.Counter()
    for line in open(collect_path):
        r = json.loads(line)
        if r["subject"] != subject or r["framing"] != "guided":
            stats["other_subject_or_framing"] += 1
            continue
        if r["probe_id"] not in train:
            # Training data never comes from held-out scenarios, whatever the collection holds.
            stats["not_training_half"] += 1
            continue
        key = (r["probe_id"], r["pressure"])
        b = bands.get(key)
        if b is None or b < 1:
            stats["band_below_1"] += 1
            continue
        if (turn1_bands.get(key) or -2) < 1:
            stats["turn1_below_1"] += 1
            continue
        text = r["turns"][1]["content"] + "\n" + r["turns"][3]["content"]
        if GUIDE_REF.search(text):
            stats["guide_ref_screened"] += 1
            continue
        if dangling_markers(r["turns"]):
            stats["dangling_screened"] += 1
            continue
        rows.append({"probe_id": r["probe_id"], "pressure": r["pressure"],
                     "band": b, "turn1_band": turn1_bands.get(key), "turns": r["turns"]})
        stats["kept"] += 1
    rows.sort(key=lambda x: (x["probe_id"], x["pressure"]))
    return rows, stats, band_hist


def write(rows, out: Path) -> tuple[str, str]:
    """Write the training set and its `_messages` form; return both sha256s."""
    out = paths.output_path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w") as fh:
        for row in rows:
            fh.write(json.dumps(row, sort_keys=True) + "\n")
    messages_out = out.with_name(out.stem + "_messages" + out.suffix)
    with open(messages_out, "w") as fh:
        for row in rows:
            fh.write(json.dumps({"messages": row["turns"]}) + "\n")
    return (hashlib.sha256(out.read_bytes()).hexdigest(),
            hashlib.sha256(messages_out.read_bytes()).hexdigest())


@app.command()
def main(
    collect: Path = typer.Option(..., help="The model's guided training-half collection (harness record schema)."),
    judgments: Path = typer.Option(..., help="Gemini ratings of that collection, both scopes."),
    subject: str = typer.Option("inkling-small", help="Subject name in the collection and ratings."),
    run: str = typer.Option("new-run", help="Run directory name under data/runs/ for the outputs."),
    out: Path | None = typer.Option(None, help="Output path (default: <run dir>/sft_train_small.jsonl)."),
) -> None:
    rows, stats, band_hist = build(collect, judgments, subject)
    out = out or paths.run_dir(run) / "sft_train_small.jsonl"
    sha, sha_messages = write(rows, out)
    typer.echo(f"guided band histogram (train-70, Gemini full): {dict(sorted(band_hist.items()))}")
    typer.echo(f"kept: {stats['kept']}  band<1: {stats['band_below_1']}"
               f"  turn1<1: {stats['turn1_below_1']}"
               f"  guide-ref: {stats['guide_ref_screened']}  dangling: {stats['dangling_screened']}"
               f"  skipped (other subject/framing): {stats['other_subject_or_framing']}"
               f"  skipped (held-out scenario): {stats['not_training_half']}")
    typer.echo(f"{len(rows)} rows -> {out}  sha256 {sha}")
    typer.echo(f"trainer form -> {out.with_name(out.stem + '_messages' + out.suffix)}  sha256 {sha_messages}")


if __name__ == "__main__":
    app()
