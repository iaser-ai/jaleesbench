"""Export a pairs file to the Tinker trainer's LabeledComparison schema.

Prompt = the shared opening user turn. Completion = the rest of the sitting (assistant
turn 1, the authored pressure turn, assistant turn 2); the renderer masks user turns, so
only assistant tokens carry loss. Which side is A is a seeded coin flip per pair.

    uv run python -m jaleesweights.comparisons --src data/runs/my-run/pairs_train70_small_sft2.jsonl
"""

import hashlib
import json
import random
from pathlib import Path

import typer

app = typer.Typer(add_completion=False, help=__doc__)

SEED = 3446


def build(src: Path, seed: int = SEED) -> tuple[list[dict], int]:
    rng = random.Random(seed)
    rows = []
    for line in open(src):
        p = json.loads(line)
        ch, rj = p["chosen_turns"], p["rejected_turns"]
        if ch[0] != rj[0]:
            raise RuntimeError(f"prompt mismatch in {p['probe_id']}|{p['pressure']}")
        for side in (ch, rj):
            if [t["role"] for t in side] != ["user", "assistant", "user", "assistant"]:
                raise RuntimeError(f"unexpected turn roles in {p['probe_id']}|{p['pressure']}")
        chosen_is_a = rng.random() < 0.5
        comp = {
            "prompt_conversation": [ch[0]],
            "completion_A": (ch if chosen_is_a else rj)[1:],
            "completion_B": (rj if chosen_is_a else ch)[1:],
        }
        rows.append({"comparison": comp, "label": "A" if chosen_is_a else "B"})
    return rows, sum(1 for r in rows if r["label"] == "A")


def write(rows, out: Path) -> str:
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w") as fh:
        for r in rows:
            fh.write(json.dumps(r, sort_keys=True) + "\n")
    return hashlib.sha256(out.read_bytes()).hexdigest()


@app.command()
def main(
    src: Path = typer.Option(..., help="Pairs file (output of `pairs`)."),
    out: Path | None = typer.Option(None, help="Output path (default: beside src, 'pairs_train70' -> 'comparisons_train')."),
) -> None:
    rows, n_a = build(src)
    out = out or src.with_name(src.name.replace("pairs_train70", "comparisons_train"))
    if out == src:
        raise typer.BadParameter("give --out: the default name would overwrite the source")
    sha = write(rows, out)
    typer.echo(f"{len(rows)} comparisons  label A: {n_a}  label B: {len(rows) - n_a}")
    typer.echo(f"-> {out}  sha256 {sha}")


if __name__ == "__main__":
    app()
