"""DPO training run for issue #21 — Inkling on JaleesBench pairs.

Hyperparameters are the preference-optimization settings of record: beta 0.1,
lr 1e-5, one epoch, LoRA rank 32, 4 pairs per batch, single replica, reference policy
= the base model (reference_model_name None -> initial weights = base, since
we train from base with no checkpoint).

Run: uv run --directory jaleesbench python ../tmp/dpo-experiment/train_dpo_run.py
"""

import pathlib

from tinker_cookbook.preference import train_dpo
from tinker_cookbook.preference.dpo_datasets import DPODatasetBuilderFromComparisons
from tinker_cookbook.preference.preference_datasets import ComparisonBuilderFromJsonl
from tinker_cookbook.supervised.types import ChatDatasetBuilderCommonConfig

ROOT = pathlib.Path(__file__).resolve().parent
MODEL = "thinkingmachines/Inkling"  # 64K base, verified via get_server_capabilities

config = train_dpo.Config(
    log_path=str(ROOT / "run2"),
    model_name=MODEL,
    recipe_name="jaleesbench-dpo-21-run2",
    renderer_name="tml_v0",
    dataset_builder=DPODatasetBuilderFromComparisons(
        comparison_builder=ComparisonBuilderFromJsonl(
            train_path=str(ROOT / "comparisons_train_expanded4.jsonl"),
        ),
        common_config=ChatDatasetBuilderCommonConfig(
            model_name_for_tokenizer=MODEL,
            renderer_name="tml_v0",
            max_length=16384,  # longest sitting ~15.5K tokens; do not truncate pairs
            batch_size=16,  # scaled with corpus: ~90 steps, holds rate x steps in the calibrated regime
        ),
    ),
    learning_rate=1e-5,
    num_epochs=1,
    dpo_beta=0.1,
    lora_rank=32,
    num_replicas=1,  # cookbook default is 8; the settings of record pin 1
    save_every=20,
    eval_every=0,
    infrequent_eval_every=0,
)

if __name__ == "__main__":
    train_dpo.main(config)
