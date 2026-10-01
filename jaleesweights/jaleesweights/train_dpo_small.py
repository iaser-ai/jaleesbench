"""Inkling-Small stage 2: on-policy DPO at the distilled anchor
(JaleesWeights replication; Waleed's go 2026-08-05).

672 max-gap own-sample pairs from the SFT policy's K=4 census
(comparisons_train_small_sft2.jsonl, sha 473669b3…). Trains FROM the stage-1
SFT checkpoint (load_checkpoint_path = its state path); reference_model_name
stays None, so the cookbook's reference sampling client is a frozen snapshot
of the initial weights = the SFT checkpoint — the same policy≡ref-at-init
contract as gemma's two-adapter stage 2. Hypers mirror gemma stage 2:
beta 0.1, lr 1e-5, 1 epoch, r32, batch 8 (~84 steps).

Run: uv run --directory jaleesbench python ../tmp/dpo-experiment/train_dpo_small_sft2.py
"""

import pathlib

from tinker_cookbook.preference import train_dpo
from tinker_cookbook.preference.dpo_datasets import DPODatasetBuilderFromComparisons
from tinker_cookbook.preference.preference_datasets import ComparisonBuilderFromJsonl
from tinker_cookbook.supervised.types import ChatDatasetBuilderCommonConfig

ROOT = pathlib.Path(__file__).resolve().parent
MODEL = "thinkingmachines/Inkling-Small"
SFT_STATE = "tinker://ac84a01f-1cbb-55b0-80f4-f9f2b6e3df99:train:0/weights/final"

config = train_dpo.Config(
    log_path=str(ROOT / "dpo_small_sft2_run"),
    model_name=MODEL,
    recipe_name="jaleesweights-dpo-small-sft2",
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
            batch_size=8,  # counts comparisons: 8 pairs = 16 interleaved datums
        ),
    ),
    learning_rate=1e-5,
    num_epochs=1,
    dpo_beta=0.1,
    lora_rank=32,
    num_replicas=1,
    save_every=20,
    eval_every=0,
    infrequent_eval_every=0,
)

if __name__ == "__main__":
    train_dpo.main(config)
