"""Inkling-Small stage 1: context-distillation SFT on Tinker.

The model's own guided training-half answers rendered bare (output of `sft_small`, the
`_messages` form). tml_v0 renderer -> assistant-turn loss only (the pressure turn sits in
context, masked). Settings of record: LoRA rank 32, lr 5e-5, 2 epochs, batch 8 (~78 steps).

The checkpoint address this run produces (printed by the trainer and recorded in
<log dir>/checkpoints.jsonl as `state_path` / `sampler_path`) is what the stage-2 trainer
and the tuned-checkpoint collections take as input.

    uv run python -m jaleesweights.train_sft_small --run my-run
"""

import asyncio
from pathlib import Path

import typer
from tinker_cookbook.supervised import train
from tinker_cookbook.supervised.data import FromConversationFileBuilder
from tinker_cookbook.supervised.types import ChatDatasetBuilderCommonConfig

from . import paths
from .env import load_keys

app = typer.Typer(add_completion=False, help=__doc__)

MODEL = "thinkingmachines/Inkling-Small"


def make_config(data: Path, log_dir: Path, model: str, lr: float, epochs: int, batch: int,
                lora_rank: int, recipe_name: str) -> train.Config:
    return train.Config(
        log_path=str(log_dir),
        model_name=model,
        recipe_name=recipe_name,
        lora_rank=lora_rank,
        dataset_builder=FromConversationFileBuilder(
            file_path=str(data),
            common_config=ChatDatasetBuilderCommonConfig(
                model_name_for_tokenizer=model,
                renderer_name="tml_v0",
                max_length=16384,
                batch_size=batch,
            ),
        ),
        learning_rate=lr,
        num_epochs=epochs,
        save_every=20,
        eval_every=0,
        infrequent_eval_every=0,
    )


def count_rows(path: Path) -> int:
    if not path.exists():
        raise typer.BadParameter(f"{path} does not exist")
    return sum(1 for l in path.read_text().splitlines() if l.strip())


@app.command()
def main(
    run: str = typer.Option("new-run", help="Run directory name under data/runs/ for the trainer's log directory."),
    data: Path | None = typer.Option(None, help="Training set in the trainer's `messages` form (default: the reference set)."),
    log_dir: Path | None = typer.Option(None, help="Trainer log directory (default: <run dir>/sft_small_run)."),
    model: str = typer.Option(MODEL, help="Base model on Tinker."),
    lr: float = typer.Option(5e-5, help="Learning rate (setting of record 5e-5)."),
    epochs: int = typer.Option(2, help="Epochs (setting of record 2)."),
    batch: int = typer.Option(8, help="Conversations per batch (setting of record 8)."),
    lora_rank: int = typer.Option(32, help="LoRA rank (setting of record 32)."),
    recipe_name: str = typer.Option("jaleesweights-sft-small", help="Recipe name recorded by the trainer."),
    dry_run: bool = typer.Option(False, "--dry-run", help="Print the preflight summary and stop before training."),
) -> None:
    data = data or paths.reference_file("sft_train_small_messages.jsonl")
    log_dir = paths.output_path(log_dir or paths.run_dir(run) / "sft_small_run")
    n = count_rows(data)
    load_keys(["TINKER_API_KEY"])
    steps = -(-n * epochs // batch)
    typer.echo(f"preflight: will train {model} on {n} conversations from {data.name}: "
               f"LoRA rank {lora_rank}, lr {lr:g}, {epochs} epoch(s), batch {batch} (~{steps} steps); "
               f"logs -> {log_dir}; billed to your Tinker account")
    if dry_run:
        return
    asyncio.run(train.main(make_config(data, log_dir, model, lr, epochs, batch, lora_rank, recipe_name)))


if __name__ == "__main__":
    app()
