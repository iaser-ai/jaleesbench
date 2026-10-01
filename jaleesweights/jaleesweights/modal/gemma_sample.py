"""On-policy sampling pass for the gemma DPO redesign (issue #21).

K independent chains per train-70 cell from BASE gemma (no adapter), at a
temperature bumped above the model's generation_config default — the bump is
what spreads the model's own candidates apart so the selection judge has real
chosen/rejected contrast to mine. Both assistant turns sample hot (the whole
sitting is the training completion). top_p / top_k stay at config defaults.

Phase 1 generates K turn-1 replies per cell (SamplingParams n=K); phase 2
continues each chain through the authored pressure turn. Output is
harness collect-schema, one record per chain, subject = gemma-onpol-s{k}.

Setup: modal volume put gemma-dpo tmp/dpo-experiment/train_inputs_gemma.jsonl /pairs/train_inputs.jsonl
Run:   modal run --detach tmp/dpo-experiment/modal_gemma_sample.py --temperature 1.3 --k 4
Out:   /vol/runs/gemma-onpol-sample/collect_train_samples.jsonl
"""

import modal

MODEL = "google/gemma-4-31B-it"
app = modal.App("jaleesbench-gemma-sample")
vol = modal.Volume.from_name("gemma-dpo")

# Same image as the eval job: vLLM compiles gemma-4 router-GEMM kernels at
# startup and needs nvcc, so the full CUDA toolkit is required.
image = (
    modal.Image.from_registry("nvidia/cuda:12.8.1-devel-ubuntu24.04", add_python="3.12")
    .pip_install("vllm>=0.10", "hf_transfer")
    .env({"HF_HUB_ENABLE_HF_TRANSFER": "1", "HF_HOME": "/vol/hf-cache",
          "VLLM_WORKER_MULTIPROC_METHOD": "spawn"})
)


@app.function(
    image=image, gpu="H200", timeout=4 * 60 * 60, volumes={"/vol": vol},
    secrets=[modal.Secret.from_name("huggingface")],
)
def sample_chains(temperature: float, k: int, adapter_run: str, out_run: str,
                  lane_prefix: str):
    import json
    import pathlib
    from datetime import datetime, timezone

    from transformers import AutoTokenizer, GenerationConfig
    from vllm import LLM, SamplingParams
    from vllm.lora.request import LoRARequest

    rows = [json.loads(l) for l in open("/vol/pairs/train_inputs.jsonl")]
    out_path = pathlib.Path(f"/vol/runs/{out_run}/collect_train_samples.jsonl")
    out_path.parent.mkdir(parents=True, exist_ok=True)

    gen = GenerationConfig.from_pretrained(MODEL)
    base_temp = gen.temperature if gen.do_sample else 1.0
    if temperature <= base_temp:
        raise RuntimeError(
            f"temperature {temperature} does not bump the config default {base_temp}")
    common = dict(
        top_p=getattr(gen, "top_p", 1.0) or 1.0,
        top_k=getattr(gen, "top_k", -1) or -1,
        max_tokens=8192, seed=3446,
    )
    sp1 = SamplingParams(n=k, temperature=temperature, **common)
    sp2 = SamplingParams(n=1, temperature=temperature, **common)
    print(f"config default temp={base_temp}; sampling at {temperature}, k={k}")
    print("phase1:", sp1)

    tok = AutoTokenizer.from_pretrained(MODEL)
    llm = LLM(model=MODEL, dtype="bfloat16", max_model_len=32768,
              gpu_memory_utilization=0.92,
              enable_lora=bool(adapter_run), max_lora_rank=32)
    lora = (LoRARequest("policy", 1, f"/vol/runs/{adapter_run}/adapter")
            if adapter_run else None)
    print("sampling policy:", adapter_run or "base")

    def render(turns):
        return tok.apply_chat_template(turns, tokenize=False, add_generation_prompt=True)

    p1 = [render([{"role": "user", "content": r["turn1"]}]) for r in rows]
    o1 = llm.generate(p1, sp1, lora_request=lora)

    # chains: (row_idx, k_idx, turn1_reply, phase1_usage)
    chains = []
    for i, (r, o) in enumerate(zip(rows, o1)):
        if len(o.outputs) != k:
            raise RuntimeError(f"row {i}: expected {k} samples, got {len(o.outputs)}")
        for ki, out in enumerate(o.outputs):
            chains.append((i, ki, out.text,
                           {"prompt_tokens": len(o.prompt_token_ids),
                            "completion_tokens": len(out.token_ids)}))

    p2 = [render([
        {"role": "user", "content": rows[i]["turn1"]},
        {"role": "assistant", "content": a},
        {"role": "user", "content": rows[i]["pressure_text"]},
    ]) for i, _, a, _ in chains]
    o2 = llm.generate(p2, sp2, lora_request=lora)

    with open(out_path, "w") as fh:
        for (i, ki, a1, u1), x2 in zip(chains, o2):
            r = rows[i]
            fh.write(json.dumps({
                "subject": f"{lane_prefix}{ki}", "probe_id": r["probe_id"],
                "pressure": r["pressure"], "framing": "unstated",
                "model": f"{MODEL}" + (f"+lora:{adapter_run}" if adapter_run else "")
                         + f"@T{temperature}",
                "context_prefix": None,
                "ts": datetime.now(timezone.utc).isoformat(),
                "attempts": [1, 1],
                "usage": [u1,
                          {"prompt_tokens": len(x2.prompt_token_ids),
                           "completion_tokens": len(x2.outputs[0].token_ids)}],
                "turns": [
                    {"role": "user", "content": r["turn1"]},
                    {"role": "assistant", "content": a1},
                    {"role": "user", "content": r["pressure_text"]},
                    {"role": "assistant", "content": x2.outputs[0].text},
                ],
            }, sort_keys=True) + "\n")
    vol.commit()
    print(f"done: {len(chains)} sampled sittings -> {out_path}")


@app.local_entrypoint()
def main(temperature: float = 1.3, k: int = 4, adapter_run: str = "",
         out_run: str = "gemma-onpol-sample", lane_prefix: str = "gemma-onpol-s"):
    sample_chains.remote(temperature, k, adapter_run, out_run, lane_prefix)
