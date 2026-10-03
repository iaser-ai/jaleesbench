"""Local demonstration: collect answers from a Gemma-family model (base or with an adapter)
through vLLM on one local GPU — the Modal collection and sampling functions' bodies, merged,
with local paths and the options the demonstration needs.

Two batched phases over the input cells: phase 1 generates every first reply, phase 2
appends the authored pressure turn and generates the second. With --guide the guide text is
folded into EVERY user message at request time and stored turns stay clean (the harness
contract; judges never see the guide). With --k > 1 each cell gets K independent chains
(stage-2 sampling), recorded with a `chain` field under one subject, exactly as the
Inkling-Small driver does, so `judge rate-samples` and `pairs` consume them unchanged.
Sampling: the model's own generation_config unless --temperature is given (sampling for
stage 2 used 1.3, which must exceed the config default).

--load-in-4bit (the 24 GB profile) has vLLM quantize the weights to 4-bit (nf4) in flight with
bitsandbytes, the adapter applied on top. This changes the sampled text, not just the
throughput: the demonstration's base, stage-1 and stage-2 arms are then all served quantized,
so comparisons within one profile stay like for like. Reducing --max-model-len or
--gpu-memory-utilization, by contrast, changes throughput only.

The four passes of the demonstration's run order:
    --inputs <train inputs> --guide           (stage-1 teacher pool)      subject e.g. gemma-demo
    --inputs <eval inputs>                     (baseline, bare)
    --inputs <eval inputs> --guide             (ceiling / guided guard)
    --inputs <train inputs> --k 4 --temperature 1.3 --adapter <stage-1 adapter>   (stage-2 sampling)

    uv run python -m jaleesweights.local.gemma_collect --inputs data/reference/eval_inputs_gemma.jsonl \\
        --subject gemma-demo --run demo --limit 5
"""

import importlib.util
from datetime import datetime, timezone
from pathlib import Path

import typer

from .. import paths
from ._common import GPU_GROUP_HINT, DEFAULT_MODEL, count_rows, precision_line, preflight, read_jsonl, require

app = typer.Typer(add_completion=False, help=__doc__)

VLLM_DTYPES = {"bf16": "bfloat16", "bfloat16": "bfloat16", "fp16": "float16", "float16": "float16",
               "fp32": "float32", "float32": "float32"}


def require_vllm_bitsandbytes(find_spec=importlib.util.find_spec) -> None:
    """vLLM up to 0.27 quantizes in flight in tree (nf4 hard-coded in its loader, the matmul
    in bf16); 0.28 moved that support to the vllm-bnb-plugin package. Stop by name when
    neither is present — never a silent unquantized load."""
    if (find_spec("vllm.model_executor.layers.quantization.bitsandbytes") is None
            and find_spec("vllm_bnb_plugin") is None):
        raise SystemExit("missing GPU dependency: vllm-bnb-plugin (this vLLM has no in-tree bitsandbytes "
                         f"support); {GPU_GROUP_HINT}")


def collect(rows: list[dict], out_path: Path, model_name: str, dtype: str, load_in_4bit: bool,
            adapter: Path | None, ctx: str | None, k: int, temperature: float | None,
            max_model_len: int, gpu_memory_utilization: float, subject: str) -> None:
    import json

    if load_in_4bit:
        require("bitsandbytes")  # first: vLLM's in-flight quantization needs it; no fallback to bf16
    transformers = require("transformers")
    vllm = require("vllm")
    if load_in_4bit:
        require_vllm_bitsandbytes()
    lora_request = require("vllm.lora.request")
    AutoTokenizer, GenerationConfig = transformers.AutoTokenizer, transformers.GenerationConfig
    LLM, SamplingParams, LoRARequest = vllm.LLM, vllm.SamplingParams, lora_request.LoRARequest

    def fold(text):
        return f"{ctx}\n\n{text}" if ctx else text

    gen = GenerationConfig.from_pretrained(model_name)
    base_temp = gen.temperature if gen.do_sample else 1.0
    if temperature is not None and k > 1 and temperature <= base_temp:
        raise RuntimeError(
            f"temperature {temperature} does not bump the config default {base_temp}")
    common = dict(
        top_p=getattr(gen, "top_p", 1.0) or 1.0,
        top_k=getattr(gen, "top_k", -1) or -1,
        max_tokens=8192, seed=3446,
    )
    temp = base_temp if temperature is None else temperature
    sp1 = SamplingParams(n=k, temperature=temp, **common)
    sp2 = SamplingParams(n=1, temperature=temp, **common)
    print(f"config default temp={base_temp}; sampling at {temp}, k={k}")

    tok = AutoTokenizer.from_pretrained(model_name)
    llm = LLM(model=model_name, dtype=dtype, max_model_len=max_model_len,
              gpu_memory_utilization=gpu_memory_utilization,
              quantization="bitsandbytes" if load_in_4bit else None,
              enable_lora=bool(adapter), max_lora_rank=32)
    lora = LoRARequest("policy", 1, str(adapter)) if adapter else None
    print("policy:", adapter or "base")

    def render(turns):
        return tok.apply_chat_template(turns, tokenize=False, add_generation_prompt=True)

    p1 = [render([{"role": "user", "content": fold(r["turn1"])}]) for r in rows]
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
        {"role": "user", "content": fold(rows[i]["turn1"])},
        {"role": "assistant", "content": a},
        {"role": "user", "content": fold(rows[i]["pressure_text"])},
    ]) for i, _, a, _ in chains]
    o2 = llm.generate(p2, sp2, lora_request=lora)

    model_tag = (model_name + ("@nf4" if load_in_4bit else "") + (f"+lora:{adapter}" if adapter else "@vllm-base")
                 + (f"@T{temp}" if k > 1 else ""))
    with open(out_path, "w") as fh:
        for (i, ki, a1, u1), x2 in zip(chains, o2):
            r = rows[i]
            fh.write(json.dumps({
                "subject": subject, "probe_id": r["probe_id"],
                "pressure": r["pressure"], "chain": ki,
                "framing": "guided" if ctx else "unstated",
                "model": model_tag,
                "context_prefix": ctx,
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
    print(f"done: {len(chains)} sittings -> {out_path}")


@app.command()
def main(
    inputs: Path = typer.Option(..., help="Conversation inputs: the training or the held-out half (output of `inputs`)."),
    subject: str = typer.Option("gemma-demo", help="Subject name stamped on every record."),
    run: str = typer.Option("new-run", help="Run directory name under data/runs/ for the output."),
    out: Path | None = typer.Option(None, help="Output file (default: <run dir>/collect_<subject>_<guided|unstated>[_k<K>].jsonl)."),
    model: str = typer.Option(DEFAULT_MODEL, help="Gemma-family model id."),
    dtype: str = typer.Option("bf16", help="Weights precision: bf16 (recipe of record), fp16 or fp32; the compute precision under --load-in-4bit."),
    load_in_4bit: bool = typer.Option(False, "--load-in-4bit", help="Serve 4-bit (nf4) weights, quantized in flight by vLLM with bitsandbytes: the 24 GB profile. Changes the sampled text, not only throughput."),
    adapter: Path | None = typer.Option(None, help="A LoRA adapter directory to apply (a stage-1 or stage-2 output)."),
    guide: bool = typer.Option(False, "--guide/--no-guide", help="Fold the companionship guide into every user turn."),
    k: int = typer.Option(1, help="Independent chains per cell (4 for stage-2 sampling)."),
    temperature: float | None = typer.Option(None, help="Sampling temperature (default: the model's config; 1.3 for stage-2 sampling)."),
    max_model_len: int = typer.Option(32768, help="vLLM context window (reduce on smaller GPUs)."),
    gpu_memory_utilization: float = typer.Option(0.92, help="Fraction of GPU memory vLLM may use."),
    limit: int = typer.Option(0, help="Use the first N input cells only (smoke test)."),
    dry_run: bool = typer.Option(False, "--dry-run", help="Print the preflight summary and stop before anything loads."),
) -> None:
    n = count_rows(inputs)
    if adapter is not None and not (adapter / "adapter_config.json").exists():
        raise typer.BadParameter(f"{adapter} is not a PEFT adapter directory (no adapter_config.json)")
    framing = "guided" if guide else "unstated"
    if guide and k > 1:
        raise typer.BadParameter("stage-2 sampling is bare: drop --guide when --k > 1 (pairs ignore guided records)")
    if k > 1 and temperature is None:
        raise typer.BadParameter("stage-2 sampling needs an explicit --temperature above the model's default (the recipe used 1.3)")
    dtype = VLLM_DTYPES.get(dtype)
    if dtype is None:
        raise typer.BadParameter(f"unknown dtype; use one of {sorted(VLLM_DTYPES)}")
    half = inputs.stem.removesuffix("_gemma").removesuffix("_inputs")  # train / eval / <custom>
    out = paths.output_path(out or paths.run_dir(run) / f"collect_{subject}_{half}_{framing}{f'_k{k}' if k > 1 else ''}.jsonl")
    if out.exists():
        raise typer.BadParameter(f"{out} already exists; choose another --out or --run (a run never overwrites)")
    out.parent.mkdir(parents=True, exist_ok=True)  # before the model loads, so a bad path cannot discard a finished run
    ctx = paths.GUIDED_PREFIX.read_text().strip() if guide else None
    rows = read_jsonl(inputs)
    if limit:
        rows = rows[:limit]
    missing = [kk for kk in ("probe_id", "pressure", "turn1", "pressure_text") if kk not in rows[0]]
    if missing:
        raise typer.BadParameter(f"{inputs} is not a conversation-inputs file (first row lacks {', '.join(missing)})")
    if preflight(f"local collection with vLLM from {model}" + (f" + adapter {adapter}" if adapter else " (base)"),
                 [f"inputs {inputs}: {n} cells" + (f", using the first {limit}" if limit else "") + f"; {framing}; k={k}"
                  + (f"; temperature {temperature}" if temperature is not None else "; model-default sampling"),
                  f"{dtype}, context window {max_model_len}, GPU memory utilization {gpu_memory_utilization}",
                  precision_line(model, dtype, load_in_4bit, training=False),
                  f"subject {subject} -> {out}"],
                 dry_run):
        return
    collect(rows, out, model, dtype, load_in_4bit, adapter, ctx, k, temperature, max_model_len,
            gpu_memory_utilization, subject)


if __name__ == "__main__":
    app()
