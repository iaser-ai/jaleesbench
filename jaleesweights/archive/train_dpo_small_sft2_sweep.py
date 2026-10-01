"""Inkling-Small stage 2, learning-rate sweep (2026-08-25).

The run of record (train_dpo_small_sft2.py, lr 1e-5) under-fit its pairs:
training preference accuracy ended ~0.75, DPO loss ~0.51 (Gemma's stage 2
reached 0.99 / ~0.17 at the same hypers). This sweep re-runs the identical
stage 2 — same SFT anchor, same 672 pairs, beta 0.1, r32, batch 8, 1 epoch —
at larger learning rates, to test whether the flat held-out result was
"nothing to buy" or "did not fit".

Run: uv run --directory jaleesbench python ../tmp/dpo-experiment/train_dpo_small_sft2_sweep.py --lr 1e-4
"""

import pathlib

import typer
from tinker_cookbook.preference import train_dpo
from tinker_cookbook.preference.dpo_datasets import DPODatasetBuilderFromComparisons
from tinker_cookbook.preference.preference_datasets import ComparisonBuilderFromJsonl
from tinker_cookbook.supervised.types import ChatDatasetBuilderCommonConfig

ROOT = pathlib.Path(__file__).resolve().parent
MODEL = "thinkingmachines/Inkling-Small"
SFT_STATE = "tinker://ac84a01f-1cbb-55b0-80f4-f9f2b6e3df99:train:0/weights/final"


def main(lr: float = typer.Option(..., help="learning rate"),
         epochs: int = typer.Option(1, help="epochs")):
    tag = f"lr{lr:g}" + (f"_ep{epochs}" if epochs != 1 else "")
    config = train_dpo.Config(
        log_path=str(ROOT / f"dpo_small_sft2_sweep_{tag}"),
        model_name=MODEL,
        recipe_name=f"jaleesweights-dpo-small-sft2-{tag}",
        renderer_name="tml_v0",
        load_checkpoint_path=SFT_STATE,
        dataset_builder=DPODatasetBuilderFromComparisons(
            comparison_builder=ComparisonBuilderFromJsonl(
                train_path=str(ROOT / "comparisons_train_small_sft2.jsonl"),
            ),
            common_config=ChatDatasetBuilderCommonConfig(
                model_name_for_tokenizer=MODEL,
                renderer_name="tml_v0",
                max_length=16384,
                batch_size=8,
            ),
        ),
        learning_rate=lr,
        num_epochs=epochs,
        dpo_beta=0.1,
        lora_rank=32,
        num_replicas=1,
        save_every=20,
        eval_every=0,
        infrequent_eval_every=0,
    )
    train_dpo.main(config)


if __name__ == "__main__":
    typer.run(main)
