"""Inkling-Small stage 2: on-policy DPO at the distilled anchor, on Tinker.

Max-gap pairs mined from the stage-1 model's own K=4 samples (output of `pairs` then
`comparisons`). Trains FROM the stage-1 state checkpoint; the cookbook's reference is a
frozen snapshot of the initial weights, i.e. the stage-1 model — the same policy == reference
at init contract as the Gemma two-adapter stage 2. Settings of record: beta 0.1, lr 1e-5,
1 epoch, LoRA rank 32, batch 8 (~84 steps on 672 pairs).

The stage-1 checkpoint is an input: the `state_path` of the final checkpoint your own stage-1
run wrote (see <stage-1 log dir>/checkpoints.jsonl).

    uv run python -m jaleesweights.train_dpo_small --run my-run \\
        --sft-checkpoint tinker://<your stage-1 run>/weights/final
"""

from pathlib import Path

import typer
from tinker_cookbook.preference import train_dpo
from tinker_cookbook.preference.dpo_datasets import DPODatasetBuilderFromComparisons
from tinker_cookbook.preference.preference_datasets import ComparisonBuilderFromJsonl
from tinker_cookbook.supervised.types import ChatDatasetBuilderCommonConfig

from . import paths
from .env import load_keys
from .train_sft_small import MODEL, count_rows

app = typer.Typer(add_completion=False, help=__doc__)


def make_config(comparisons: Path, sft_checkpoint: str, log_dir: Path, model: str, lr: float,
                epochs: int, beta: float, batch: int, lora_rank: int, recipe_name: str) -> train_dpo.Config:
    return train_dpo.Config(
        log_path=str(log_dir),
        model_name=model,
        recipe_name=recipe_name,
        renderer_name="tml_v0",
        load_checkpoint_path=sft_checkpoint,
        dataset_builder=DPODatasetBuilderFromComparisons(
            comparison_builder=ComparisonBuilderFromJsonl(train_path=str(comparisons)),
            common_config=ChatDatasetBuilderCommonConfig(
                model_name_for_tokenizer=model,
                renderer_name="tml_v0",
                max_length=16384,
                batch_size=batch,  # counts comparisons: 8 pairs = 16 interleaved datums
            ),
        ),
        learning_rate=lr,
        num_epochs=epochs,
        dpo_beta=beta,
        lora_rank=lora_rank,
        num_replicas=1,
        save_every=20,
        eval_every=0,
        infrequent_eval_every=0,
    )


@app.command()
def main(
    sft_checkpoint: str = typer.Option(..., "--sft-checkpoint", help="tinker://.../weights/final of YOUR stage-1 run (required)."),
    run: str = typer.Option("new-run", help="Run directory name under data/runs/ for the trainer's log directory."),
    comparisons: Path | None = typer.Option(None, help="Pairs in the trainer's comparison form (default: the reference set)."),
    log_dir: Path | None = typer.Option(None, help="Trainer log directory (default: <run dir>/dpo_small_sft2_run)."),
    model: str = typer.Option(MODEL, help="Base model on Tinker (the checkpoint must belong to it)."),
    lr: float = typer.Option(1e-5, help="Learning rate (setting of record 1e-5)."),
    epochs: int = typer.Option(1, help="Epochs (setting of record 1)."),
    beta: float = typer.Option(0.1, help="DPO beta (setting of record 0.1)."),
    batch: int = typer.Option(8, help="Pairs per batch (setting of record 8)."),
    lora_rank: int = typer.Option(32, help="LoRA rank (setting of record 32)."),
    recipe_name: str = typer.Option("jaleesweights-dpo-small-sft2", help="Recipe name recorded by the trainer."),
    dry_run: bool = typer.Option(False, "--dry-run", help="Print the preflight summary and stop before training."),
) -> None:
    if not sft_checkpoint.startswith("tinker://"):
        raise typer.BadParameter("--sft-checkpoint must be a tinker:// state address of your stage-1 run")
    comparisons = comparisons or paths.reference_file("comparisons_train_small_sft2.jsonl")
    log_dir = paths.output_path(log_dir or paths.run_dir(run) / "dpo_small_sft2_run")
    n = count_rows(comparisons)
    load_keys(["TINKER_API_KEY"])
    steps = -(-n * epochs // batch)
    typer.echo(f"preflight: will train {model} from {sft_checkpoint} on {n} pairs from {comparisons.name}: "
               f"beta {beta:g}, lr {lr:g}, {epochs} epoch(s), batch {batch}, LoRA rank {lora_rank} (~{steps} steps); "
               f"logs -> {log_dir}; billed to your Tinker account")
    if dry_run:
        return
    train_dpo.main(make_config(comparisons, sft_checkpoint, log_dir, model, lr, epochs, beta, batch, lora_rank, recipe_name))


if __name__ == "__main__":
    app()
