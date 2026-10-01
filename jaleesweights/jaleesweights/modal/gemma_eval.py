"""Collect held-out eval sittings from the tuned Gemma adapter — Modal + vLLM.

Two batched phases over the 420 test-70 sittings (unstated framing = no
context prefix, matching the harness): phase 1 generates every turn-1 reply,
phase 2 appends the authored pressure turn and generates turn 2. Sampling uses
the model's own generation_config (the harness runs subjects at
provider-default sampling). Base is served bf16 with the LoRA applied; the bf16
recipe of record trains against a bf16 base too, so there is no precision
mismatch (the earlier 4-bit chain, now archived, had one).

Setup: modal volume put <volume> <eval_inputs_gemma.jsonl> /pairs/eval_inputs.jsonl
       (and, for the guided guard, the guide text: modal volume put <volume> <guided_prefix.txt> /pairs/guided_prefix.txt)
Run:   uv run modal run --detach -m jaleesweights.modal.gemma_eval --run-name gemma-sft-guided-bf16
       uv run modal run --detach -m jaleesweights.modal.gemma_eval --run-name base --subject gemma-base-vllm   (the same-stack control)
       uv run modal run --detach -m jaleesweights.modal.gemma_eval --run-name gemma-sft-guided-bf16 --subject gemma-sft-guided-bf16-G --context-file /pairs/guided_prefix.txt
       uv run modal run --detach -m jaleesweights.modal.gemma_eval --run-name gemma-sft-dpo-bf16   (stage 2, bare)
       Every real launch also takes --local-inputs <eval_inputs_gemma.jsonl> (and --local-context <guided_prefix.txt>
       for the guided guard): the local files the volume copies came from, checked before launch.
Out:   /vol/runs/<run-name>/collect_eval_gemma[_guided].jsonl (harness record schema)
Preflight only, no account needed: uv run python -m jaleesweights.modal.gemma_eval --run-name base
"""

import modal

from jaleesweights.modal._config import preflight_cli, MODEL, SERVE_IMAGE, hf_secret, preflight, volume

app = modal.App("jaleesbench-gemma-eval")
vol = volume()


@app.function(
    image=SERVE_IMAGE, gpu="H200", timeout=4 * 60 * 60, volumes={"/vol": vol},
    secrets=[hf_secret()],
)
def collect_eval(run_name: str, subject: str, context_file: str, inputs_path: str):
    import json
    import pathlib
    from datetime import datetime, timezone

    from transformers import AutoTokenizer, GenerationConfig
    from vllm import LLM, SamplingParams
    from vllm.lora.request import LoRARequest

    rows = [json.loads(l) for l in open(f"/vol{inputs_path}")]
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
def main(run_name: str, subject: str = "", context_file: str = "",
         inputs: str = "/pairs/eval_inputs.jsonl", local_inputs: str = "", local_context: str = "",
         dry_run: bool = False):
    out = f"/runs/{run_name}/collect_eval_gemma{'_guided' if context_file else ''}.jsonl"
    reads = [inputs] + ([context_file] if context_file else []) + ([f"/runs/{run_name}/adapter"] if run_name != "base" else [])
    local = {}
    if local_inputs:
        local[inputs] = (local_inputs, 420)  # 70 held-out scenarios x 6 pressures
    if local_context and context_file:
        local[context_file] = (local_context, None)
    if preflight(f"held-out collection with vLLM: run {run_name} ({'base model, no adapter' if run_name == 'base' else 'adapter'}), "
                 f"subject {subject or run_name}, {'with guide' if context_file else 'bare'}",
                 "H200", reads, [out], dry_run, local=local or None,
                 required_local=[inputs] + ([context_file] if context_file else [])):
        return
    collect_eval.remote(run_name, subject or run_name, context_file, inputs)


if __name__ == "__main__":
    preflight_cli(main)
