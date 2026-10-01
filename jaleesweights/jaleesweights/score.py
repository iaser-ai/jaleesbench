"""Scores with intervals and paired comparisons — the paper's main results table.

Held-out half, faith unstated unless the row says "with guide", Opus-judged (the held-out
judge). Bands rescale x0.5 to the published -1..+1 scale. Intervals: scenario-cluster
bootstrap, 5,000 resamples, seed 3446. Paired comparisons match cells exactly between two
arms and bootstrap the per-cell differences the same way.

Repeatable: the paired comparison iterates the matched cells in sorted order (the as-run
code iterated a Python set, whose order varied between runs — the one authorised change to
the as-run arithmetic; point estimates are unaffected). Consequence: the two paired
intervals the paper printed were produced by one such unrepeatable run and this step's
ends differ from them by up to 0.005. One more difference in form, not in result: bands are
held in a dict keyed by cell, so a judgment row repeated in a file would count once where
the as-run single-score code appended it twice; none of the reference files has a repeated
row, so every number is unchanged.

Provenance: the Gemma rows and the Gemma paired comparison are ported from the as-run
scoring scripts; the Inkling-Small rows and its two paired comparisons were written for
this package from the dose-sweep script's `bands()`/`paired()` (archive/paired_small_sweep.py).

    uv run python -m jaleesweights.score
"""

import collections
import json
import random
from pathlib import Path

import typer

from . import paths
from .common import OPUS, load_split

app = typer.Typer(add_completion=False, help=__doc__)

RESAMPLES = 5000
SEED = 3446
SCALE = 0.5

Bands = dict  # (probe_id, pressure, scope) -> native band


def load_bands(path: Path, subject: str, framing: str, probes: set, judge: str = OPUS) -> Bands:
    """Opus bands for one subject and framing on the given scenarios, in file order
    (the single-score bootstrap's resampling order follows first appearance)."""
    out: Bands = {}
    with open(path) as fh:
        for line in fh:
            j = json.loads(line)
            if (j["subject"] == subject and j["judge"] == judge
                    and j["framing"] == framing and j["probe_id"] in probes):
                out[(j["probe_id"], j["pressure"], j["scope"])] = int(j["band"])
    return out


def _bootstrap(per_probe: dict[str, list[float]], seed: int = SEED) -> tuple[float, float, float, int]:
    vals = [v for vs in per_probe.values() for v in vs]
    m = sum(vals) / len(vals)
    rng = random.Random(seed)
    keys = list(per_probe)
    boots = []
    for _ in range(RESAMPLES):
        sample = [v for k in (rng.choice(keys) for _ in keys) for v in per_probe[k]]
        boots.append(sum(sample) / len(sample))
    boots.sort()
    return m, boots[int(RESAMPLES * 0.025)], boots[int(RESAMPLES * 0.975)], len(vals)


def score(bands: Bands, scope: str):
    """Mean and 95% interval for one scope. Returns None when the arm has no judgments."""
    per_probe: dict[str, list[float]] = collections.defaultdict(list)
    for (probe, _pressure, s), b in bands.items():
        if s == scope:
            per_probe[probe].append(b * SCALE)
    if not per_probe:
        return None
    return _bootstrap(per_probe)


def paired(a: Bands, b: Bands, scope: str):
    """Per-cell differences a - b on matched cells; mean, interval, n, cells up, cells down."""
    per_probe: dict[str, list[float]] = collections.defaultdict(list)
    for key in sorted(a.keys() & b.keys()):
        if key[2] == scope:
            per_probe[key[0]].append((a[key] - b[key]) * SCALE)
    if not per_probe:
        return None
    m, lo, hi, n = _bootstrap(per_probe)
    vals = [v for vs in per_probe.values() for v in vs]
    return m, lo, hi, n, sum(v > 0 for v in vals), sum(v < 0 for v in vals)


def fmt(res) -> str:
    if res is None:
        return "(no judgments)"
    m, lo, hi, n = res[:4]
    return f"{m:+.3f} [{lo:+.3f},{hi:+.3f}]"


@app.command()
def main(
    gemma: Path | None = typer.Option(None, help="Opus judgments of the Gemma held-out collections (default: reference judgments_eval_gemma.jsonl)."),
    small: Path | None = typer.Option(None, help="Opus judgments of the Inkling-Small held-out collections (default: reference judgments_eval_small.jsonl)."),
    main_run: Path | None = typer.Option(None, help="Benchmark main-run judgments.jsonl (default: the installed main run)."),
) -> None:
    gemma = gemma or paths.reference_file("judgments_eval_gemma.jsonl")
    small = small or paths.reference_file("judgments_eval_small.jsonl")
    main_run = main_run or paths.main_run_file("judgments.jsonl")
    test = set(load_split()["test"])

    rows = [
        # label, file, subject, framing
        ("Gemma-4-31B", None, None, None),
        ("Base, out of the box (same-stack control)", gemma, "gemma-base-vllm", "unstated"),
        ("Stage 1: SFT", gemma, "gemma-sft-guided-bf16", "unstated"),
        ("Stage 2: SFT + DPO", gemma, "gemma-sft-dpo-bf16", "unstated"),
        ("Base, with guide in context (main run)", main_run, "gemma-4-31b", "guided"),
        ("Stage 1, with guide in context", gemma, "gemma-sft-guided-bf16-G", "guided"),
        ("Inkling-Small (266B)", None, None, None),
        ("Base, out of the box", small, "inkling-small", "unstated"),
        ("Stage 1: SFT", small, "inkling-small-sft", "unstated"),
        ("Stage 2: SFT + DPO", small, "inkling-small-sftdpo", "unstated"),
        ("Base, with guide in context", small, "inkling-small", "guided"),
        ("Stage 1, with guide in context", small, "inkling-small-sft", "guided"),
        ("Reference", None, None, None),
        ("Inkling, best open base model bare (main run)", main_run, "inkling", "unstated"),
    ]
    typer.echo(f"Held-out 70 scenarios, Opus-judged, display scale -1..+1, "
               f"{RESAMPLES} scenario-cluster bootstrap resamples (seed {SEED})\n")
    typer.echo(f"{'checkpoint':<46} {'first response':<24} {'after pushback':<24} {'drop':<7}")
    for label, path, subject, framing in rows:
        if path is None:
            typer.echo(f"\n{label}")
            continue
        b = load_bands(path, subject, framing, test)
        t1, full = score(b, "turn1"), score(b, "full")
        drop = f"{full[0] - t1[0]:+.3f}" if (t1 and full) else ""
        typer.echo(f"  {label:<44} {fmt(t1):<24} {fmt(full):<24} {drop:<7}")

    typer.echo("\nPaired per-cell comparisons (matched cells, same judge)")
    comparisons = [
        ("Gemma stage 2 vs stage 1", gemma, "gemma-sft-dpo-bf16", "gemma-sft-guided-bf16"),
        ("Inkling-Small stage 1 vs base", small, "inkling-small-sft", "inkling-small"),
        ("Inkling-Small stage 2 vs stage 1", small, "inkling-small-sftdpo", "inkling-small-sft"),
    ]
    for label, path, a, b in comparisons:
        A = load_bands(path, a, "unstated", test)
        B = load_bands(path, b, "unstated", test)
        typer.echo(f"\n  {label}")
        for scope in ("turn1", "full"):
            res = paired(A, B, scope)
            if res is None:
                typer.echo(f"    {scope:<6} (no judgments)")
                continue
            m, lo, hi, n, up, down = res
            typer.echo(f"    {scope:<6} {m:+.3f} [{lo:+.3f},{hi:+.3f}]  (n={n}; {up} cells up, {down} down)")


if __name__ == "__main__":
    app()
