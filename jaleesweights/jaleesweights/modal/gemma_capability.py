"""Capability-regression panel for the gemma checkpoints (JaleesWeights §7).

lm-evaluation-harness over the same vLLM stack as every eval in the study:
IFEval (instruction following — the directly-relevant check), MMLU 5-shot,
GSM8K CoT. Raw-completion (no chat template) at 4k ctx: absolutes are NOT
comparable to Google's published chat-formatted numbers (MMLU-Pro 85.2);
the panel's job is within-pipeline regression detection, identical config.

Run: modal run --detach tmp/dpo-experiment/modal_gemma_capability.py
Out: /vol/runs/capability/<checkpoint>/ (lm-eval result JSONs) + stdout table
"""

import modal

MODEL = "google/gemma-4-31B-it"
app = modal.App("jaleesbench-gemma-capability")
vol = modal.Volume.from_name("gemma-dpo")

image = (
    modal.Image.from_registry("nvidia/cuda:12.8.1-devel-ubuntu24.04", add_python="3.12")
    .pip_install("vllm>=0.10", "lm_eval[vllm,ifeval]>=0.4.8", "hf_transfer")
    .env({"HF_HUB_ENABLE_HF_TRANSFER": "1", "HF_HOME": "/vol/hf-cache",
          "VLLM_WORKER_MULTIPROC_METHOD": "spawn",
          "HF_ALLOW_CODE_EVAL": "1"})
)

CHECKPOINTS = {
    "base": None,
    "sft-guided": "/vol/runs/gemma-sft-guided/adapter",
    "sft-dpo": "/vol/runs/gemma-sft-dpo/adapter",
    "sft-bf16": "/vol/runs/gemma-sft-guided-bf16/adapter",
    "sft-dpo-bf16": "/vol/runs/gemma-sft-dpo-bf16/adapter",
}
TASKS = "ifeval,mmlu,gsm8k_cot"


@app.function(
    image=image, gpu="H200", timeout=5 * 60 * 60, volumes={"/vol": vol},
    secrets=[modal.Secret.from_name("huggingface")],
)
def run_panel(name: str, tasks: str = TASKS, log_samples: bool = False,
              chat: bool = False):
    import subprocess

    adapter = CHECKPOINTS[name]
    # Chat mode = the deployment-faithful config for an -it model: the chat
    # template applied, few-shot as multi-turn, headroom for template tokens.
    # Raw-completion mode kept only for continuity with the earlier panels.
    max_len = 8192 if chat else 4096
    margs = (f"pretrained={MODEL},dtype=bfloat16,gpu_memory_utilization=0.9,"
             f"max_model_len={max_len}")
    if adapter:
        margs += f",enable_lora=True,max_lora_rank=32,lora_local_path={adapter}"
    suffix = ("-chat" if chat else "") + ("-samples" if log_samples else "")
    out = f"/vol/runs/capability/{name}{suffix}"
    cmd = ["lm_eval", "--model", "vllm", "--model_args", margs,
           "--tasks", tasks, "--batch_size", "auto", "--output_path", out]
    if chat:
        cmd += ["--apply_chat_template", "--fewshot_as_multiturn"]
    if log_samples:
        cmd.append("--log_samples")
    print("running:", " ".join(cmd), flush=True)
    subprocess.run(cmd, check=True)
    vol.commit()
    print(f"panel done: {name}")


@app.local_entrypoint()
def main(only: str = "", tasks: str = TASKS, log_samples: bool = False,
         chat: bool = False):
    # spawn + detach: the runs survive local client/network drops (which
    # killed two attempts); completion is observed via the volume.
    names = [only] if only else list(CHECKPOINTS)
    handles = [run_panel.spawn(n, tasks, log_samples, chat) for n in names]
    print("spawned:", names)
    for h in handles:
        h.get()
