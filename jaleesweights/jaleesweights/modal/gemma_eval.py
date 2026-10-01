"""Collect held-out eval sittings from the tuned Gemma adapter — Modal + vLLM.

Two batched phases over the 420 test-70 sittings (unstated framing = no
context prefix, matching the harness): phase 1 generates every turn-1 reply,
phase 2 appends the authored pressure turn and generates turn 2. Sampling uses
the model's own generation_config (the harness runs subjects at
provider-default sampling). Base is served bf16 with the LoRA applied —
the adapter was trained against an nf4-quantized base (recorded deviation).

Setup: modal volume put gemma-dpo tmp/dpo-experiment/eval_inputs_gemma.jsonl /pairs/eval_inputs.jsonl
Run:   modal run --detach tmp/dpo-experiment/modal_gemma_eval.py --run-name gemma-dpo-r1
Out:   /vol/runs/<run-name>/collect_eval_gemma.jsonl (harness record schema)
"""

import modal

MODEL = "google/gemma-4-31B-it"
app = modal.App("jaleesbench-gemma-eval")
vol = modal.Volume.from_name("gemma-dpo")

# vLLM compiles gemma-4 router-GEMM kernels at startup — needs nvcc, so the
# image must carry the full CUDA toolkit (debian_slim lacks it).
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
def collect_eval(run_name: str, subject: str, context_file: str):
    import json
    import pathlib
    from datetime import datetime, timezone

    from transformers import AutoTokenizer, GenerationConfig
    from vllm import LLM, SamplingParams
    from vllm.lora.request import LoRARequest

    rows = [json.loads(l) for l in open("/vol/pairs/eval_inputs.jsonl")]
    out_path = pathlib.Path(
        f"/vol/runs/{run_name}/collect_eval_gemma{'_guided' if context_file else ''}.jsonl")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    # run_name "base" = no-adapter control: base gemma through the identical
    # serving stack, isolating tuning effects from vLLM-vs-Friendli drift and
    # single-sample bistability in every arm-vs-base comparison.
    use_adapter = run_name != "base"
    # Guided framing: the harness folds the context block into EVERY user
    # message at request time; stored turns stay clean (judges never see the
    # guide). Same contract here.
    ctx = open(f"/vol{context_file}").read().strip() if context_file else None

    def fold(text):
        return f"{ctx}\n\n{text}" if ctx else text

    gen = GenerationConfig.from_pretrained(MODEL)
    sp = SamplingParams(
        temperature=gen.temperature if gen.do_sample else 1.0,
        top_p=getattr(gen, "top_p", 1.0) or 1.0,
        top_k=getattr(gen, "top_k", -1) or -1,
        max_tokens=8192, seed=3446,
    )
    print("sampling:", sp)

    tok = AutoTokenizer.from_pretrained(MODEL)
    llm = LLM(model=MODEL, dtype="bfloat16", enable_lora=True, max_lora_rank=32,
              max_model_len=32768, gpu_memory_utilization=0.92)
    lora = LoRARequest("dpo", 1, f"/vol/runs/{run_name}/adapter") if use_adapter else None

    def render(turns):
        return tok.apply_chat_template(turns, tokenize=False, add_generation_prompt=True)

    p1 = [render([{"role": "user", "content": fold(r["turn1"])}]) for r in rows]
    o1 = llm.generate(p1, sp, lora_request=lora)
    reply1 = [o.outputs[0].text for o in o1]

    p2 = [render([
        {"role": "user", "content": fold(r["turn1"])},
        {"role": "assistant", "content": a},
        {"role": "user", "content": fold(r["pressure_text"])},
    ]) for r, a in zip(rows, reply1)]
    o2 = llm.generate(p2, sp, lora_request=lora)
    reply2 = [o.outputs[0].text for o in o2]

    with open(out_path, "w") as fh:
        for r, a1, a2, x1, x2 in zip(rows, reply1, reply2, o1, o2):
            fh.write(json.dumps({
                "subject": subject, "probe_id": r["probe_id"],
                "pressure": r["pressure"],
                "framing": "guided" if ctx else "unstated",
                "model": f"{MODEL}+lora:{run_name}" if use_adapter else f"{MODEL}@vllm-base",
                "context_prefix": ctx,
                "ts": datetime.now(timezone.utc).isoformat(),
                "attempts": [1, 1],
                "usage": [
                    {"prompt_tokens": len(x1.prompt_token_ids),
                     "completion_tokens": len(x1.outputs[0].token_ids)},
                    {"prompt_tokens": len(x2.prompt_token_ids),
                     "completion_tokens": len(x2.outputs[0].token_ids)},
                ],
                "turns": [
                    {"role": "user", "content": r["turn1"]},
                    {"role": "assistant", "content": a1},
                    {"role": "user", "content": r["pressure_text"]},
                    {"role": "assistant", "content": a2},
                ],
            }, sort_keys=True) + "\n")
    vol.commit()
    print(f"done: {len(rows)} sittings -> {out_path}")


@app.local_entrypoint()
def main(run_name: str, subject: str = "", context_file: str = ""):
    collect_eval.remote(run_name, subject or run_name, context_file)
