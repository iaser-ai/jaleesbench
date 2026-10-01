"""Capability-regression panel for the gemma checkpoints (JaleesWeights §7).

lm-evaluation-harness over the same vLLM stack as every eval in the study:
IFEval (instruction following — the directly-relevant check), MMLU 5-shot,
GSM8K CoT. Two modes: --chat (the paper's table: chat template applied, few-shot
as multi-turn, 8k ctx) and raw completion (no chat template, 4k ctx; the earlier
panels' mode, kept for continuity — its absolutes are far lower and not comparable
to published chat-formatted numbers). In either mode the panel's job is
within-pipeline regression detection: identical config across the checkpoints.

Run: uv run modal run --detach -m jaleesweights.modal.gemma_capability --chat
     (--chat is the paper's mode: chat template applied, few-shot as multi-turn. Without it
     the panel runs raw completions, the earlier panels' mode; absolutes differ a lot.)
Out: /vol/runs/capability/<checkpoint>[-chat]/ (lm-eval result JSONs) + stdout table
Preflight only: add --dry-run.
"""

import modal

from jaleesweights.modal._config import preflight_cli, CAPABILITY_IMAGE, MODEL, hf_secret, preflight, volume

app = modal.App("jaleesbench-gemma-capability")
vol = volume()

# The three checkpoints of the recipe of record (base and the two bf16 stages).
CHECKPOINTS = {
    "base": None,
    "sft-bf16": "/vol/runs/gemma-sft-guided-bf16/adapter",
    "sft-dpo-bf16": "/vol/runs/gemma-sft-dpo-bf16/adapter",
}
TASKS = "ifeval,mmlu,gsm8k_cot"


@app.function(
    image=CAPABILITY_IMAGE, gpu="H200", timeout=5 * 60 * 60, volumes={"/vol": vol},
    secrets=[hf_secret()],
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
         chat: bool = False, dry_run: bool = False):
    # spawn + detach: the runs survive local client/network drops (which
    # killed two attempts); completion is observed via the volume.
    names = [only] if only else list(CHECKPOINTS)
    unknown = [n for n in names if n not in CHECKPOINTS]
    if unknown:
        raise SystemExit(f"unknown checkpoint {unknown}; choose from {list(CHECKPOINTS)}")
    suffix = ("-chat" if chat else "") + ("-samples" if log_samples else "")
    if preflight(f"capability panel ({tasks}) in {'chat' if chat else 'raw-completion'} mode on {names}",
                 "H200", [CHECKPOINTS[n].removeprefix("/vol") for n in names if CHECKPOINTS[n]],
                 [f"/runs/capability/{n}{suffix}" for n in names], dry_run):
        return
    handles = [run_panel.spawn(n, tasks, log_samples, chat) for n in names]
    print("spawned:", names)
    for h in handles:
        h.get()


if __name__ == "__main__":
    preflight_cli(main)
