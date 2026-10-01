"""Inkling-Small SL stage 1: context-distillation SFT on Tinker
(JaleesWeights replication; mirrors the gemma stage-1 envelope).

310 of the model's own guided sittings rendered bare (build_sft_small.py),
messages format. tml_v0 renderer -> assistant-turn loss only (pressure turn
in context, masked) — same masking contract as every arm. lr 5e-5, 2 epochs,
batch 8 ≈ 78 steps: parity with the gemma stage-1 run that worked.

Run: uv run --directory jaleesbench python ../tmp/dpo-experiment/train_sft_small.py
"""

import asyncio
import pathlib

from tinker_cookbook.supervised import train
from tinker_cookbook.supervised.data import FromConversationFileBuilder
from tinker_cookbook.supervised.types import ChatDatasetBuilderCommonConfig

ROOT = pathlib.Path(__file__).resolve().parent
MODEL = "thinkingmachines/Inkling-Small"

config = train.Config(
    log_path=str(ROOT / "sft_small_run"),
    model_name=MODEL,
    recipe_name="jaleesweights-sft-small",
    lora_rank=32,
    dataset_builder=FromConversationFileBuilder(
        file_path=str(ROOT / "sft_train_small_messages.jsonl"),
        common_config=ChatDatasetBuilderCommonConfig(
            model_name_for_tokenizer=MODEL,
            renderer_name="tml_v0",
            max_length=16384,
            batch_size=8,
        ),
    ),
    learning_rate=5e-5,
    num_epochs=2,
    save_every=20,
    eval_every=0,
    infrequent_eval_every=0,
)

if __name__ == "__main__":
    asyncio.run(train.main(config))
