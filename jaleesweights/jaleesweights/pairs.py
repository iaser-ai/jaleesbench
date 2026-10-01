"""Stage-2 preference pairs: max-gap, both-direction anchored pairs from the stage-1
policy's OWN sampled answers (K draws per training cell), rated by the selection judge.

Pool per training cell = the K sampled conversations, Gemini-rated after pushback. Every
draw anchors up to two pairs: (the most-differently-rated draw ABOVE it, anchor) and
(anchor, the most-differently-rated draw BELOW it), gap >= MIN_GAP on the native -2..+2
scale, deduplicated; dangling-citation screen on chosen sides. The base model's answers
are deliberately absent: stage 2 is on-policy contrast with the stage-1 model as reference.

One builder for both models. Sampled records that carry a `chain` field (the Inkling-Small
driver's K draws under one subject name) are keyed `<subject>-c<chain>`, matching the
ratings file; records without it (the Gemma driver's `<lane>-s<k>` subjects) are keyed by
subject.

    uv run python -m jaleesweights.pairs --run my-run \\
        --samples data/reference/collect_sftbf16_samples.jsonl \\
        --judgments data/reference/judgments_sftbf16_samples.jsonl --out-name pairs_train70_sftbf16.jsonl
"""

import collections
import hashlib
import json
from pathlib import Path

import typer

from . import paths
from .common import GEMINI, MIN_GAP, dangling_markers, load_split

app = typer.Typer(add_completion=False, help=__doc__)


def lane(record: dict) -> str:
    return f"{record['subject']}-c{record['chain']}" if "chain" in record else record["subject"]


def build(samples_path: Path, judgments_path: Path, split: dict):
    train = set(split["train"])
    bands: dict = collections.defaultdict(dict)
    for line in open(judgments_path):
        j = json.loads(line)
        if (j["judge"] == GEMINI and j["framing"] == "unstated"
                and j["scope"] == "full" and j["probe_id"] in train):
            bands[(j["probe_id"], j["pressure"])][j["subject"]] = j["band"]

    sittings: dict = {}
    for line in open(samples_path):
        r = json.loads(line)
        sittings[(r["probe_id"], r["pressure"], lane(r))] = r["turns"]

    pairs = []
    stats = collections.Counter()
    band_hist = collections.Counter()
    seen = set()

    for (probe, pressure), lanes in sorted(bands.items()):
        havers = {s: b for s, b in lanes.items() if (probe, pressure, s) in sittings}
        for b in havers.values():
            band_hist[b] += 1
        emitted = False
        for anchor in sorted(havers):
            ab = havers[anchor]
            above = [s for s, b in havers.items() if b - ab >= MIN_GAP]
            below = [s for s, b in havers.items() if ab - b >= MIN_GAP]
            cands = []
            if above:
                top = max(havers[s] for s in above)
                cands.append((sorted(s for s in above if havers[s] == top)[0], anchor))
            if below:
                bot = min(havers[s] for s in below)
                cands.append((anchor, sorted(s for s in below if havers[s] == bot)[0]))
            for ch, rj in cands:
                key = (probe, pressure, ch, rj)
                if key in seen:
                    continue
                seen.add(key)
                if dangling_markers(sittings[(probe, pressure, ch)]):
                    stats["chosen_screened_dangling"] += 1
                    continue
                pairs.append({
                    "probe_id": probe, "pressure": pressure,
                    "chosen_subject": ch, "rejected_subject": rj,
                    "chosen_band": havers[ch], "rejected_band": havers[rj],
                    "chosen_cites": None, "rejected_is_inkling": False,
                    "chosen_turns": sittings[(probe, pressure, ch)],
                    "rejected_turns": sittings[(probe, pressure, rj)],
                })
                stats["pair"] += 1
                stats[f"chosen_band={havers[ch]}"] += 1
                emitted = True
        stats["cells_covered" if emitted else "cells_no_spread"] += 1
    return pairs, stats, band_hist, len(bands)


def write(pairs, out: Path) -> str:
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w") as fh:
        for p in pairs:
            fh.write(json.dumps(p, sort_keys=True) + "\n")
    return hashlib.sha256(out.read_bytes()).hexdigest()


@app.command()
def main(
    samples: Path = typer.Option(..., help="The stage-1 model's K sampled conversations per training cell."),
    judgments: Path = typer.Option(..., help="Gemini ratings of those samples (after-pushback scope)."),
    run: str = typer.Option("new-run", help="Run directory name under data/runs/ for the output."),
    out_name: str = typer.Option("pairs.jsonl", help="Output file name inside the run directory."),
    out: Path | None = typer.Option(None, help="Explicit output path (overrides --run/--out-name)."),
) -> None:
    pairs, stats, band_hist, n_cells = build(samples, judgments, load_split())
    out = out or paths.run_dir(run) / out_name
    sha = write(pairs, out)
    typer.echo(f"pairs: {stats['pair']}  cells covered: {stats['cells_covered']}/{n_cells}"
               f"  no-spread: {stats['cells_no_spread']}"
               f"  dangling-screened: {stats['chosen_screened_dangling']}")
    typer.echo(f"band histogram (all sampled draws): {dict(sorted(band_hist.items()))}")
    typer.echo("chosen-band mix: " + str({k.split('=')[1]: v for k, v in sorted(stats.items())
                                          if k.startswith('chosen_band=')}))
    typer.echo(f"{len(pairs)} pairs -> {out}  sha256 {sha}")


if __name__ == "__main__":
    app()
