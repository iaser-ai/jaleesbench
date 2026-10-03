"""Local demonstration, stage 1: supervised fine-tuning (filtered context distillation) of a
Gemma-family model on one local GPU — the Modal stage-1 function's body with local paths.

Same objective and settings as the recipe of record unless you change them: LoRA rank 32 on
the language model's attention and MLP projections, masked token-mean NLL over assistant
tokens only, lr 5e-5, 2 epochs, batch 8 by gradient accumulation, seed 3446, bf16 base with
no quantization, gradient checkpointing, the selective-head parity check at start-up,
full-state checkpoints every 100 optimizer steps and --resume-from.

--load-in-4bit (the 24 GB profile) quantizes the base to nf4 with the archived 4-bit chain's
settings (archive/modal_gemma_sft.py) and trains the same LoRA on top (QLoRA); everything
else is unchanged. Default model: google/gemma-4-12B-it (the owner's default for the
demonstration). The 31B model of the paper fits an 80 GB GPU with thin headroom (measured
66 GB peak) in bf16.

Smoke test (first thing to run on a GPU machine; add --load-in-4bit on a 24 GB card):
    uv run python -m jaleesweights.local.gemma_sft --data data/runs/demo/sft_train_small.jsonl --run demo --limit 4
Full:
    uv run python -m jaleesweights.local.gemma_sft --data data/runs/demo/sft_train_small.jsonl --run demo
"""

from pathlib import Path

import typer

from .. import paths
from ._common import (DEFAULT_MODEL, MAX_TOKENS_PER_CONVERSATION, bnb_4bit_config, check_resume_dir,
                      count_rows, make_render, precision_line, preflight, read_jsonl, require, torch_dtype)

app = typer.Typer(add_completion=False, help=__doc__)

CKPT_EVERY = 100  # optimizer steps between full-state checkpoints


def train(data_path: Path, out: Path, model_name: str, dtype_name: str, load_in_4bit: bool,
          batch: int, lr: float, epochs: int, seed: int, limit: int, resume_from: Path | None) -> None:
    import json
    import random

    quant = bnb_4bit_config(dtype_name) if load_in_4bit else None  # first: names bitsandbytes if absent
    torch = require("torch")
    peft = require("peft")
    transformers = require("transformers")
    LoraConfig, PeftModel, get_peft_model = peft.LoraConfig, peft.PeftModel, peft.get_peft_model
    AutoConfig, AutoModelForCausalLM = transformers.AutoConfig, transformers.AutoModelForCausalLM
    AutoModelForImageTextToText, AutoTokenizer = transformers.AutoModelForImageTextToText, transformers.AutoTokenizer
    dtype = torch_dtype(dtype_name)

    out.mkdir(parents=True, exist_ok=True)
    adapter_dir = out / "adapter"
    state_file = out / "train_state.pt"

    resume_dir = resume_from
    resuming = resume_from is not None  # validated before preflight: complete or refused

    tok = AutoTokenizer.from_pretrained(model_name)
    render = make_render(tok)

    rows = read_jsonl(data_path)
    if limit:
        rows = rows[:limit]
    data = []
    for r in rows:
        ids, mask = render(r["turns"])
        if len(ids) > MAX_TOKENS_PER_CONVERSATION:
            raise RuntimeError(f"sitting over 16k tokens in {r.get('probe_id')}|{r.get('pressure')}")
        data.append((ids, mask))
    print(f"{len(data)} examples from {data_path}, max len {max(len(d[0]) for d in data)}")

    cfg = AutoConfig.from_pretrained(model_name)
    multimodal = hasattr(cfg, "vision_config")
    loader = AutoModelForImageTextToText if multimodal else AutoModelForCausalLM
    base_model = loader.from_pretrained(
        model_name, torch_dtype=dtype, device_map="auto", attn_implementation="sdpa",
        quantization_config=quant,  # None: no quantization
    )
    base_model.config.use_cache = False
    if quant is not None:  # the archived chain's set-up: checkpointing + input grads + fp32 casts
        base_model = peft.prepare_model_for_kbit_training(
            base_model, use_gradient_checkpointing=True,
            gradient_checkpointing_kwargs={"use_reentrant": False})
    else:
        base_model.gradient_checkpointing_enable(gradient_checkpointing_kwargs={"use_reentrant": False})
        base_model.enable_input_require_grads()  # so grads flow to LoRA through the frozen base under GC
    proj = "(q_proj|k_proj|v_proj|o_proj|gate_proj|up_proj|down_proj)"
    if resuming:
        model = PeftModel.from_pretrained(base_model, str(resume_dir / "adapter"), is_trainable=True)
    else:
        model = get_peft_model(base_model, LoraConfig(
            r=32, lora_alpha=32, lora_dropout=0.0, bias="none",
            target_modules=(rf".*language_model.*{proj}" if multimodal else rf".*{proj}"),
            task_type="CAUSAL_LM",
        ))
    model.train()
    n_ckpt = sum(1 for m in model.modules() if getattr(m, "gradient_checkpointing", False))
    if not n_ckpt or not model.training:
        raise RuntimeError("gradient checkpointing did not engage (flag or training mode)")
    print(f"gradient checkpointing active on {n_ckpt} modules")
    model.print_trainable_parameters()
    opt = torch.optim.AdamW((p for p in model.parameters() if p.requires_grad), lr=lr)

    base = model.get_base_model()
    trunk, head = base.model, base.lm_head
    softcap = base.config.get_text_config().final_logit_softcapping

    def seq_logp(ids, mask, grad=False):
        t = torch.tensor([ids], device="cuda:0")
        pos = [i for i in range(len(ids) - 1) if mask[i + 1]]
        tgt = torch.tensor([ids[i + 1] for i in pos])
        pos = torch.tensor(pos)
        with torch.enable_grad() if grad else torch.no_grad():
            h = trunk(input_ids=t).last_hidden_state
            pos, tgt = pos.to(h.device), tgt.to(h.device)
            hs = h[0, pos].to(head.weight.dtype)
            parts = []
            for s in range(0, len(tgt), 256):
                lg = head(hs[s:s + 256])
                if softcap is not None:
                    lg = torch.tanh(lg / softcap) * softcap
                idx = tgt[s:s + 256, None].to(lg.device)
                parts.append(lg.gather(1, idx)[:, 0] - lg.logsumexp(-1))
            return torch.cat(parts).float().sum(), len(tgt)

    # Parity check vs the model's own full forward (holds regardless of weights).
    ci0, cm0 = data[0]
    w = cm0.index(True) + 128
    with torch.no_grad():
        sel, _ = seq_logp(ci0[:w], cm0[:w]); sel = sel.cpu()
        t0 = torch.tensor([ci0[:w]], device="cuda:0")
        full = base(input_ids=t0).logits
        lp = torch.log_softmax(full[0, :-1].float(), -1)
        m0 = torch.tensor(cm0[1:w], dtype=torch.bool, device=lp.device)
        ref = lp[torch.arange(w - 1, device=lp.device), t0[0, 1:].to(lp.device)][m0].sum().cpu()
    if not torch.allclose(sel, ref, rtol=1e-3, atol=0.5):
        raise RuntimeError(f"selective-head logp mismatch: {sel.item()} vs {ref.item()}")
    print(f"selective-head parity check ok: {sel.item():.3f} vs {ref.item():.3f}")

    def save_ckpt(step, ep, order, pos, seen, log):
        model.save_pretrained(adapter_dir)
        torch.save({
            "step": step, "epoch": ep, "order": order, "pos": pos, "seen": seen,
            "opt": opt.state_dict(), "log": log,
            "py_rng": random.getstate(),
            "torch_rng": torch.get_rng_state(),
            "cuda_rng": torch.cuda.get_rng_state_all(),
        }, state_file)

    rng = random.Random(seed)
    step, log = 0, []
    start_ep, start_pos, resume_order = 0, 0, None
    if resuming:
        st = torch.load(resume_dir / "train_state.pt", weights_only=False)
        opt.load_state_dict(st["opt"])
        random.setstate(st["py_rng"])
        torch.set_rng_state(st["torch_rng"])
        torch.cuda.set_rng_state_all(st["cuda_rng"])
        step, log = st["step"], st["log"]
        start_ep, start_pos, resume_order = st["epoch"], st["pos"], st["order"]
        print(f"RESUMED: step={step} epoch={start_ep} pos={start_pos} seen={st['seen']}")

    acc_loss, acc_n = 0.0, 0
    opt.zero_grad()
    seen = step * batch  # approximate; exact 'seen' tracked per example below
    for ep in range(start_ep, epochs):
        if ep == start_ep and resume_order is not None:
            order = resume_order
        else:
            order = list(range(len(data))); rng.shuffle(order)
        pos0 = start_pos if ep == start_ep else 0
        for j in range(pos0, len(order)):
            ids, mask = data[order[j]]
            logp, ntok = seq_logp(ids, mask, grad=True)
            loss = -(logp / ntok)
            (loss / batch).backward()
            acc_loss += loss.item(); acc_n += 1; seen += 1
            last = (ep == epochs - 1) and (j == len(order) - 1)
            if acc_n == batch or last:
                opt.step(); opt.zero_grad(); step += 1
                rec = {"step": step, "epoch": ep, "seen": seen, "nll_per_token": acc_loss / acc_n,
                       "peak_gb": [round(torch.cuda.max_memory_allocated(d) / 2**30, 1)
                                   for d in range(torch.cuda.device_count())]}
                for d in range(torch.cuda.device_count()):
                    torch.cuda.reset_peak_memory_stats(d)
                log.append(rec); print(rec, flush=True)
                acc_loss, acc_n = 0.0, 0
                if step % CKPT_EVERY == 0:
                    save_ckpt(step, ep, order, j + 1, seen, log)
                    print(f"checkpoint: step {step}, epoch {ep}, pos {j+1}", flush=True)

    model.save_pretrained(adapter_dir)
    (out / "train_log.jsonl").write_text("\n".join(json.dumps(r) for r in log) + "\n")
    (out / "config.json").write_text(json.dumps({
        "model": model_name, "data": str(data_path), "n_examples": len(data),
        "batch": batch, "lr": lr, "epochs": epochs, "lora_r": 32, "seed": seed,
        "objective": "masked token-mean NLL (SL-CAI context distillation)",
        "quant": f"nf4-4bit {dtype_name}-compute" if quant is not None else f"{dtype_name} (no quantization)", "masking": "assistant-tokens-only (tml_v0 parity)",
        "checkpoint_every_steps": CKPT_EVERY, "resumable": True,
    }, indent=2))
    if state_file.exists():
        state_file.unlink()  # clean completion marker
    print(f"done: {step} steps; adapter at {adapter_dir}")


@app.command()
def main(
    data: Path = typer.Option(..., help="Stage-1 training set (output of `sft_small` or `sft_guided`)."),
    run: str = typer.Option("new-run", help="Run directory name under data/runs/ for the outputs."),
    out: Path | None = typer.Option(None, help="Output directory (default: <run dir>/gemma-sft)."),
    model: str = typer.Option(DEFAULT_MODEL, help="Gemma-family model id."),
    dtype: str = typer.Option("bf16", help="Weights precision: bf16 (recipe of record), fp16 or fp32; the compute precision under --load-in-4bit."),
    load_in_4bit: bool = typer.Option(False, "--load-in-4bit", help="Quantize the base to nf4 (QLoRA, the archived chain's settings): the 24 GB profile. Needs bitsandbytes."),
    batch: int = typer.Option(8, help="Conversations per optimizer step, by gradient accumulation."),
    lr: float = typer.Option(5e-5, help="Learning rate (setting of record 5e-5)."),
    epochs: int = typer.Option(2, help="Epochs (setting of record 2)."),
    seed: int = typer.Option(3446, help="Shuffle seed."),
    limit: int = typer.Option(0, help="Train on the first N examples only (the smoke test uses 4)."),
    resume_from: Path | None = typer.Option(None, help="An output directory holding adapter/ and train_state.pt to resume."),
    dry_run: bool = typer.Option(False, "--dry-run", help="Print the preflight summary and stop before anything loads."),
) -> None:
    n = count_rows(data)
    check_resume_dir(resume_from, "adapter")
    out = paths.output_path(out or paths.run_dir(run) / "gemma-sft")
    n_used = min(n, limit) if limit else n
    steps = -(-n_used * epochs // batch)
    if preflight(f"local stage-1 SFT of {model}",
                 [f"data {data}: {n} conversations" + (f", using the first {limit}" if limit else ""),
                  f"{dtype}, LoRA rank 32, lr {lr:g}, {epochs} epoch(s), batch {batch} (~{steps} steps), seed {seed}",
                  precision_line(model, dtype, load_in_4bit, training=True),
                  f"outputs -> {out}" + (f"; resuming from {resume_from}" if resume_from else "")],
                 dry_run):
        return
    train(data, out, model, dtype, load_in_4bit, batch, lr, epochs, seed, limit, resume_from)


if __name__ == "__main__":
    app()
