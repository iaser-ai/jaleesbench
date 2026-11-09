"""vLLM OpenAI-compatible server for experiment 58 (prompt fading): base Gemma-4-31B and the
JaleesWeights stage-2 adapter on one GPU, with a window long enough for the 64k level.

Adapted from the serving script of the MultiBench prompt-fading experiments (76/78). What
differs: a B200 instead of an H200 and an 80,000-token window instead of 32,768 (a 64k-token
conversation does not fit an H200's key-value cache next to 62 GB of bf16 weights); the
JaleesWeights adapter; the volume mounted read-only.

Two model names on the one endpoint (no API key):
  model="google/gemma-4-31B-it"  base                      (prompted arm)
  model="stage2"                 base + gemma-sft-dpo-bf16 (weights arm)

Deploy:  uv run modal deploy experiments/58_prompt_fading/serve_gemma_fading.py
Stop:    uv run modal app stop jaleesweights-fading-serve
The printed URL + "/v1" is the --base-url of collect_fading.py. Scales to zero when idle.
"""

import subprocess

import modal

# Self-contained on purpose (the container imports this file alone). The names and the image
# are those of jaleesweights/modal/_config.py: same volume, same secret, same serving image.
MODEL = "google/gemma-4-31B-it"
VOLUME = "gemma-dpo"
HF_SECRET = "huggingface"
ADAPTER = "/vol/runs/gemma-sft-dpo-bf16/adapter"
MAX_MODEL_LEN = 80_000
VLLM_PORT = 8000
MINUTES = 60

app = modal.App("jaleesweights-fading-serve")

# The volume holds the cached base weights and the adapters. It is mounted read-only: this
# experiment trains nothing and overwrites nothing. The cache is complete, so the hub is not
# contacted (HF_HUB_OFFLINE).
image = (
    modal.Image.from_registry("nvidia/cuda:12.8.1-devel-ubuntu24.04", add_python="3.12")
    .pip_install("vllm>=0.10", "hf_transfer")
    .env({"HF_HUB_ENABLE_HF_TRANSFER": "1", "HF_HOME": "/vol/hf-cache",
          "VLLM_WORKER_MULTIPROC_METHOD": "spawn", "HF_HUB_OFFLINE": "1"})
)


@app.function(
    image=image, gpu="B200", timeout=12 * 60 * MINUTES,
    volumes={"/vol": modal.Volume.from_name(VOLUME).read_only()},
    secrets=[modal.Secret.from_name(HF_SECRET)],
    scaledown_window=10 * MINUTES,
    max_containers=1,
)
@modal.concurrent(max_inputs=64)
@modal.web_server(port=VLLM_PORT, startup_timeout=20 * MINUTES)
def serve() -> None:
    cmd = [
        "vllm", "serve", MODEL,
        "--host", "0.0.0.0", "--port", str(VLLM_PORT),
        "--dtype", "bfloat16",
        "--max-model-len", str(MAX_MODEL_LEN),
        "--gpu-memory-utilization", "0.92",
        "--enable-lora", "--max-lora-rank", "32",
        "--lora-modules", f"stage2={ADAPTER}",
        "--enable-prompt-tokens-details",  # usage reports how much of a prompt came from the prefix cache
    ]
    print("launching:", " ".join(cmd), flush=True)
    subprocess.Popen(cmd)
