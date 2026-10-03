"""Stage 1 of the recipe on a Mac with MLX: LoRA fine-tuning (filtered context distillation)
of a Gemma-family MLX conversion on the released stage-1 training set, through `mlx_lm.lora`.

The data and filters are the recipe's: the `_messages` form `sft_small` writes. Each
conversation becomes two training rows, the first exchange and the full sitting, each
trained with `mlx_lm`'s --mask-prompt (loss on the last assistant turn only), so the loss
covers exactly the assistant tokens as the recipe's loss mask does. The settings differ from
the CUDA profiles where MLX needs it.

    uv run python -m jaleesweights.mlx.sft --run tutorial --limit 100 --iters 200
"""

import json
from pathlib import Path

import typer

from .. import paths
from ._common import DEFAULT_MODEL, precision_line, preflight, read_jsonl, require_mlx

app = typer.Typer(add_completion=False, help=__doc__)


def prefixes(rows: list[dict]) -> list[dict]:
    """Two rows per conversation: [user, assistant] and [user, assistant, user, assistant]."""
    out = []
    for r in rows:
        m = r["messages"]
        roles = [x["role"] for x in m]
        if roles != ["user", "assistant", "user", "assistant"]:
            raise typer.BadParameter(f"not a two-exchange conversation: roles {roles}")
        out.append({"messages": m[:2]})
        out.append({"messages": m})
    return out


def check_lengths(tok, rows: list[dict], cap: int) -> int:
    """Longest row in tokens; stop if any exceeds the cap (mlx_lm would truncate it silently,
    cutting off the very assistant turn the row trains on)."""
    lens = [len(tok.apply_chat_template(r["messages"])) for r in rows]
    over = sum(1 for n in lens if n > cap)
    if over:
        raise RuntimeError(f"{over} of {len(rows)} rows exceed --max-seq-length {cap} (longest {max(lens)}); raise the cap")
    return max(lens)


def thinking_off(tokenizer_utils) -> None:
    """Gemma-4's template has a thinking mode, and mlx_lm renders chat rows with it ON whenever
    the template has one. The teacher answers were made with it off and `scenario` asks with
    it off, so the rows train the same way. Stops if mlx_lm no longer exposes the switch."""
    if not isinstance(getattr(tokenizer_utils.TokenizerWrapper, "has_thinking", None), property):
        raise RuntimeError("mlx_lm changed: TokenizerWrapper.has_thinking is not a property; re-check the thinking-off rendering")
    tokenizer_utils.TokenizerWrapper.has_thinking = property(lambda self: False)


def train(data_path: Path, out: Path, model: str, rank: int, scale: float, layers: int, iters: int,
          batch: int, lr: float, max_seq_length: int, seed: int, limit: int) -> None:
    mlx_lm = require_mlx()
    import types
    from mlx_lm import lora, tokenizer_utils
    from mlx_lm.utils import load_tokenizer

    thinking_off(tokenizer_utils)
    rows = read_jsonl(data_path)[: limit or None]
    data_dir, adapter_dir = out / "data", out / "adapter"
    data_dir.mkdir(parents=True, exist_ok=True)
    train_rows = prefixes(rows)
    (data_dir / "train.jsonl").write_text("".join(json.dumps(r) + "\n" for r in train_rows))
    longest = check_lengths(load_tokenizer(model), train_rows, max_seq_length)
    print(f"{len(train_rows)} training rows from {len(rows)} conversations, longest {longest} tokens")

    settings = {"model": model, "train": True, "data": str(data_dir), "fine_tune_type": "lora",
                "optimizer": "adamw", "mask_prompt": True, "num_layers": layers, "batch_size": batch,
                "iters": iters, "learning_rate": lr, "max_seq_length": max_seq_length, "seed": seed,
                "grad_checkpoint": True, "adapter_path": str(adapter_dir), "steps_per_report": 10,
                "save_every": 100, "lora_parameters": {"rank": rank, "scale": scale, "dropout": 0.0}}
    (out / "config.json").write_text(json.dumps({
        **settings, "mlx_lm": mlx_lm.__version__, "data_source": str(data_path), "n_conversations": len(rows),
        "objective": "masked NLL over assistant tokens, by two prefixes per conversation (SL-CAI context distillation)",
    }, indent=2))
    lora.run(types.SimpleNamespace(**{**lora.CONFIG_DEFAULTS, **settings}))  # mlx_lm.lora's own entry point
    print(f"done: {iters} iterations; adapter at {adapter_dir}")


@app.command()
def main(
    run: str = typer.Option("new-run", help="Run directory name under data/runs/ for the outputs."),
    data: Path | None = typer.Option(None, help="Stage-1 training set in `messages` form (default: the released data/reference/sft_train_small_messages.jsonl)."),
    out: Path | None = typer.Option(None, help="Output directory (default: <run dir>/mlx-sft)."),
    model: str = typer.Option(DEFAULT_MODEL, help="An MLX conversion of a Gemma-family model (Hugging Face id or local directory)."),
    limit: int = typer.Option(0, help="Train on the first N conversations only (0: all)."),
    iters: int = typer.Option(200, help="Optimizer steps (mlx_lm iterations). One pass over N conversations is 2N/batch."),
    batch: int = typer.Option(1, help="Rows per step; 1 keeps peak memory at one sitting's activations."),
    lr: float = typer.Option(1e-5, help="Learning rate (AdamW)."),
    rank: int = typer.Option(8, help="LoRA rank."),
    scale: float = typer.Option(20.0, help="LoRA scale (mlx_lm's alpha/rank)."),
    layers: int = typer.Option(16, help="Number of transformer blocks, counted from the top, that get LoRA (mlx_lm's --num-layers; -1 for all)."),
    max_seq_length: int = typer.Option(4096, help="Longest row in tokens; a longer row is an error, never truncated."),
    seed: int = typer.Option(3446, help="Shuffle seed."),
    dry_run: bool = typer.Option(False, "--dry-run", help="Print the preflight summary and stop before anything loads."),
) -> None:
    data = data or paths.reference_file("sft_train_small_messages.jsonl")
    n = len(read_jsonl(data))
    n_used = min(n, limit) if limit else n
    out = paths.output_path(out or paths.run_dir(run) / "mlx-sft")
    if (out / "adapter" / "adapters.safetensors").exists():
        raise typer.BadParameter(f"{out} already holds an adapter; choose another --run or --out (a run never overwrites)")
    if preflight(f"MLX stage-1 LoRA of {model}",
                 [f"data {data}: {n} conversations" + (f", using the first {limit}" if limit else "") + f" -> {2 * n_used} rows",
                  f"LoRA rank {rank}, scale {scale:g}, top {layers} layers; lr {lr:g}, batch {batch}, {iters} iterations "
                  f"(~{iters * batch / (2 * n_used):.1f} passes), seq cap {max_seq_length}, seed {seed}",
                  precision_line(model), f"outputs -> {out}"],
                 dry_run):
        return
    train(data, out, model, rank, scale, layers, iters, batch, lr, max_seq_length, seed, limit)


if __name__ == "__main__":
    app()
