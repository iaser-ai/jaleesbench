"""Gemma stage-1 training set: the model's own good GUIDED answers from the benchmark main
run, re-rendered as bare conversations (filtered context distillation).

Input = the bare conversation (the guide lives outside the stored turns, so dropping it is
exact); target = the model's own guided assistant turns. Selection: Gemini band >= +1 on
the full sitting AND on the first turn (both assistant turns carry loss). Screens: explicit
references to the instruction context, and dangling [n]-citation markers.

    uv run python -m jaleesweights.sft_guided --run my-run
"""

import collections
import hashlib
import json
from pathlib import Path

import typer

from . import paths
from .common import GEMINI, GUIDE_REF, dangling_markers, load_split

app = typer.Typer(add_completion=False, help=__doc__)


def build(collect_path: Path, judgments_path: Path, split: dict, subject: str = "gemma-4-31b"):
    train = set(split["train"])
    bands: dict = {}
    turn1_bands: dict = {}
    for line in open(judgments_path):
        j = json.loads(line)
        if (j["judge"] == GEMINI and j["framing"] == "guided"
                and j["subject"] == subject and j["probe_id"] in train):
            if j["scope"] == "full":
                bands[(j["probe_id"], j["pressure"])] = j["band"]
            else:
                turn1_bands[(j["probe_id"], j["pressure"])] = j["band"]

    rows = []
    stats = collections.Counter()
    t1_hist = collections.Counter()
    with open(collect_path) as fh:
        for line in fh:
            r = json.loads(line)
            if (r["framing"] != "guided" or r["subject"] != subject
                    or r["probe_id"] not in train):
                continue
            key = (r["probe_id"], r["pressure"])
            b = bands.get(key)
            if b is None or b < 1:
                stats["band_below_1"] += 1
                continue
            # Both assistant turns carry loss — a sitting whose opening counsel is
            # bad (turn1 band < +1) would teach that opening even if the sitting
            # recovers post-pressure.
            if (turn1_bands.get(key) or -2) < 1:
                stats["turn1_below_1"] += 1
                continue
            text = r["turns"][1]["content"] + "\n" + r["turns"][3]["content"]
            m = GUIDE_REF.search(text)
            if m:
                stats["guide_ref_screened"] += 1
                stats[f"ref:{m.group(0).lower()}"] += 1
                continue
            if dangling_markers(r["turns"]):
                stats["dangling_screened"] += 1
                continue
            t1_hist[turn1_bands.get(key)] += 1
            rows.append({
                "probe_id": r["probe_id"], "pressure": r["pressure"],
                "band": b, "turn1_band": turn1_bands.get(key),
                "turns": r["turns"],
            })
            stats["kept"] += 1
    rows.sort(key=lambda x: (x["probe_id"], x["pressure"]))
    return rows, stats, t1_hist


def write(rows, out: Path) -> str:
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w") as fh:
        for row in rows:
            fh.write(json.dumps(row, sort_keys=True) + "\n")
    return hashlib.sha256(out.read_bytes()).hexdigest()


@app.command()
def main(
    run: str = typer.Option("new-run", help="Run directory name under data/runs/ for the output."),
    collect: Path | None = typer.Option(None, help="Main-run collect.jsonl (default: the installed main run)."),
    judgments: Path | None = typer.Option(None, help="Main-run judgments.jsonl (default: the installed main run)."),
    subject: str = typer.Option("gemma-4-31b", help="Main-run subject whose guided answers are distilled."),
    out: Path | None = typer.Option(None, help="Output path (default: <run dir>/sft_train_guided.jsonl)."),
) -> None:
    rows, stats, t1_hist = build(
        collect or paths.main_run_file("collect.jsonl"),
        judgments or paths.main_run_file("judgments.jsonl"),
        load_split(), subject)
    out = out or paths.run_dir(run) / "sft_train_guided.jsonl"
    sha = write(rows, out)
    typer.echo(f"kept: {stats['kept']}  band<1: {stats['band_below_1']}"
               f"  turn1<1: {stats['turn1_below_1']}"
               f"  guide-ref screened: {stats['guide_ref_screened']}"
               f"  dangling screened: {stats['dangling_screened']}")
    typer.echo(f"turn1-band histogram of kept: {dict(sorted(t1_hist.items(), key=str))}")
    typer.echo(f"{len(rows)} rows -> {out}  sha256 {sha}")


if __name__ == "__main__":
    app()
