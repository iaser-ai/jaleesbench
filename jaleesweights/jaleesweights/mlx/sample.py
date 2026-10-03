"""Stage-2 sampling on a Mac with MLX: K independent answers per training cell from the base
model with the stage-1 adapter, at the recipe's sampling temperature (1.3). Each cell's K
first replies are drawn in one batch, then the authored pressure turn is appended to each
and the K second replies are drawn. The records are the harness's collection form with a
`chain` field (what `gemma_collect --k` writes), so `judge rate-samples` and `pairs` read
them unchanged. A small tuned model sometimes does not stop: a chain whose reply reaches
--max-tokens is dropped and counted, never written cut off.

Beside the output sits `<output>.state.json`: the sampling settings (with the adapter's
checksum) and the cells completed. A re-run continues after the last completed cell, so
Ctrl-C loses at most one cell; rows of a cell that was cut off mid-write are removed first.
A re-run whose settings differ is refused: one file holds one policy's samples.

    uv run python -m jaleesweights.mlx.sample --adapter data/runs/tutorial/mlx-sft/adapter \\
        --run tutorial --limit 40
"""

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path

import typer

from .. import paths
from ._common import DEFAULT_MODEL, cap_memory, ceiling_line, precision_line, preflight, read_jsonl, require_adapter, require_mlx

app = typer.Typer(add_completion=False, help=__doc__)

SECONDS_PER_SITTING = 18  # measured: gemma-4-E4B 4-bit on an M5 Pro, 4 chains batched


def spread(rows: list[dict], limit: int) -> list[dict]:
    """`limit` cells evenly spaced through the inputs (which are sorted by scenario), so a
    subset covers many scenarios rather than the first few; 0 or more than there are: all."""
    if not limit or limit >= len(rows):
        return rows
    return rows[:: len(rows) // limit][:limit]


def state_path(out: Path) -> Path:
    return out.with_name(out.name + ".state.json")


def load_done(out: Path, settings: dict) -> set:
    """The cells a previous run of this output completed. Stops if that run's settings differ
    (its samples would be mixed with another policy's), or if the output has rows but no
    state file to say what made them."""
    if not state_path(out).exists():
        if out.exists() and out.stat().st_size:
            raise typer.BadParameter(f"{out} has samples but no {state_path(out).name}; choose another --out or --run")
        return set()
    state = json.loads(state_path(out).read_text())
    changed = sorted(key for key in settings if state["settings"].get(key) != settings[key])
    if changed:
        raise typer.BadParameter(f"{out} was sampled with different settings ({', '.join(changed)}); "
                                 "choose another --out or --run (one file holds one policy's samples)")
    return {tuple(cell) for cell in state["done"]}


def write_atomic(path: Path, text: str) -> None:
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(text)
    os.replace(tmp, path)


def sample(rows: list[dict], done: set, out: Path, settings: dict, memory_limit_gb: float) -> None:
    model_name, adapter, subject = settings["model"], Path(settings["adapter"]), settings["subject"]
    k, temperature, max_tokens = settings["k"], settings["temperature"], settings["max_tokens"]
    mlx_lm = require_mlx()
    import mlx.core as mx
    from mlx_lm.sample_utils import make_sampler

    check_memory = cap_memory(mx, memory_limit_gb)
    model, tok = mlx_lm.load(model_name, adapter_path=str(adapter))
    print(f"policy: {adapter}; weights loaded, {mx.get_active_memory() / 2**30:.1f} GB resident")
    mx.random.seed(settings["seed"] + len(done))  # a resumed run draws fresh samples, not the first cells' again
    sampler = make_sampler(temp=temperature, top_p=settings["top_p"], top_k=settings["top_k"])
    if out.exists():  # rows of a cell that was cut off mid-write
        lines = [l for l in out.read_text().splitlines() if l.strip()]
        whole = [l for l in lines if (json.loads(l)["probe_id"], json.loads(l)["pressure"]) in done]
        if len(whole) < len(lines):
            print(f"removing {len(lines) - len(whole)} rows of an unfinished cell")
            write_atomic(out, "".join(l + "\n" for l in whole))

    def draw(conversations: list[list[dict]]) -> tuple[list[str], list[dict]]:
        prompts = [tok.apply_chat_template(c, add_generation_prompt=True, enable_thinking=False) for c in conversations]  # Gemma-4: answer directly, as the teacher data was made
        texts = mlx_lm.batch_generate(model, tok, prompts, max_tokens=max_tokens, sampler=sampler).texts
        check_memory()
        return texts, [{"prompt_tokens": len(p), "completion_tokens": len(tok.encode(t, add_special_tokens=False))}
                       for p, t in zip(prompts, texts)]

    todo = [r for r in rows if (r["probe_id"], r["pressure"]) not in done]
    written = 0
    for n, r in enumerate(todo, 1):
        opening = {"role": "user", "content": r["turn1"]}
        push = {"role": "user", "content": r["pressure_text"]}
        a1, u1 = draw([[opening]] * k)
        a2, u2 = draw([[opening, {"role": "assistant", "content": a}, push] for a in a1])
        kept = [c for c in range(k) if max(u1[c]["completion_tokens"], u2[c]["completion_tokens"]) < max_tokens]
        with open(out, "a") as fh:
            for chain in kept:
                fh.write(json.dumps({
                    "subject": subject, "probe_id": r["probe_id"], "pressure": r["pressure"], "chain": chain,
                    "framing": "unstated", "model": f"{model_name}+lora:{adapter}@T{temperature}",
                    "context_prefix": None, "ts": datetime.now(timezone.utc).isoformat(),
                    "attempts": [1, 1], "usage": [u1[chain], u2[chain]],
                    "turns": [opening, {"role": "assistant", "content": a1[chain]},
                              push, {"role": "assistant", "content": a2[chain]}],
                }, sort_keys=True) + "\n")
        done.add((r["probe_id"], r["pressure"]))
        write_atomic(state_path(out), json.dumps({"settings": settings, "done": sorted(done)}, indent=1))
        written += len(kept)
        print(f"{n}/{len(todo)} {r['probe_id']}/{r['pressure']}: {len(kept)} of {k} sittings kept, "
              f"peak memory {mx.get_peak_memory() / 2**30:.1f} GB", flush=True)
    print(f"done: {written} sittings -> {out}; {len(todo) * k - written} dropped at the {max_tokens}-token cap")


@app.command()
def main(
    adapter: Path = typer.Option(..., help="The stage-1 adapter directory (output of `mlx.sft`): the policy that is sampled."),
    inputs: Path | None = typer.Option(None, help="Conversation inputs (default: the training half, data/reference/train_inputs_gemma.jsonl)."),
    run: str = typer.Option("new-run", help="Run directory name under data/runs/ for the output."),
    out: Path | None = typer.Option(None, help="Output file (default: <run dir>/collect_<subject>_train_unstated_k<K>.jsonl)."),
    model: str = typer.Option(DEFAULT_MODEL, help="An MLX conversion of a Gemma-family model (the adapter must belong to it)."),
    subject: str = typer.Option("mlx-sft", help="Subject name stamped on every record."),
    limit: int = typer.Option(0, help="Sample only N cells, evenly spaced through the inputs (0: all)."),
    k: int = typer.Option(4, help="Independent chains per cell (the recipe used 4)."),
    temperature: float = typer.Option(1.3, help="Sampling temperature (the recipe used 1.3)."),
    top_p: float = typer.Option(0.95, help="Nucleus sampling (Gemma's generation default)."),
    top_k: int = typer.Option(64, help="Top-k sampling (Gemma's generation default)."),
    max_tokens: int = typer.Option(2048, help="Generation cap per turn; a chain whose reply reaches it is dropped, not written cut off."),
    seed: int = typer.Option(3446, help="Sampling seed."),
    memory_limit_gb: float = typer.Option(24.0, help="Memory ceiling in GB, checked after every pass: the job stops once its peak has passed it."),
    dry_run: bool = typer.Option(False, "--dry-run", help="Print the preflight summary and stop before anything loads."),
) -> None:
    inputs = inputs or paths.reference_file("train_inputs_gemma.jsonl")
    all_rows = read_jsonl(inputs)
    missing = [key for key in ("probe_id", "pressure", "turn1", "pressure_text") if key not in all_rows[0]]
    if missing:
        raise typer.BadParameter(f"{inputs} is not a conversation-inputs file (first row lacks {', '.join(missing)})")
    require_adapter(adapter)
    if k < 2:
        raise typer.BadParameter("pairs need at least two chains per cell")
    rows = spread(all_rows, limit)
    out = paths.output_path(out or paths.run_dir(run) / f"collect_{subject}_train_unstated_k{k}.jsonl")
    settings = {"model": model, "adapter": str(adapter), "inputs": str(inputs), "subject": subject, "k": k,
                "adapter_sha256": hashlib.sha256((adapter / "adapters.safetensors").read_bytes()).hexdigest(),
                "temperature": temperature, "top_p": top_p, "top_k": top_k, "max_tokens": max_tokens, "seed": seed}
    done = load_done(out, settings)
    n_todo = sum((r["probe_id"], r["pressure"]) not in done for r in rows)
    out.parent.mkdir(parents=True, exist_ok=True)
    if preflight(f"stage-2 sampling with MLX from {model} + adapter {adapter}",
                 [f"inputs {inputs}: {len(all_rows)} cells" + (f", {len(rows)} evenly spaced" if len(rows) < len(all_rows) else "")
                  + (f", {len(rows) - n_todo} already sampled" if n_todo < len(rows) else ""),
                  f"{n_todo} cells x {k} chains = {n_todo * k} sittings of two turns; temperature {temperature:g}, "
                  f"top-p {top_p:g}, top-k {top_k}, up to {max_tokens} tokens per turn, seed {seed}",
                  f"estimated time: about {n_todo * k * SECONDS_PER_SITTING / 60:.0f} minutes "
                  f"({SECONDS_PER_SITTING} s per sitting on an M5 Pro)",
                  precision_line(model), ceiling_line(memory_limit_gb), f"subject {subject} -> {out}"],
                 dry_run):
        return
    sample(rows, done, out, settings, memory_limit_gb)


if __name__ == "__main__":
    app()
