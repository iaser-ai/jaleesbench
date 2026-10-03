"""Local demonstration, stage 2: DPO on the stage-1 model's own samples with the stage-1 model
as reference, on one local GPU — the Modal stage-2 function's body with local paths.

Two LoRA adapters over one copy of the base weights: "policy" (initialised from the stage-1
adapter, trainable) and "ref" (the frozen stage-1 adapter). Settings of record: beta 0.1,
lr 1e-5, 1 epoch, batch 8 by gradient accumulation, seed 3446; the selective-head parity
check and the policy == reference-at-init check at start-up; full-state checkpoints every
25 optimizer steps and --resume-from. --load-in-4bit (the 24 GB profile) holds both adapters
over one nf4-quantized base, as the archived chain did (archive/modal_gemma_dpo2.py); the
stage-1 adapter must then come from a --load-in-4bit stage-1 run.

    uv run python -m jaleesweights.local.gemma_dpo --pairs data/runs/demo/pairs.jsonl \\
        --sft-adapter data/runs/demo/gemma-sft/adapter --run demo
"""

from pathlib import Path

import typer

from .. import paths
from ._common import (DEFAULT_MODEL, MAX_TOKENS_PER_CONVERSATION, bnb_4bit_config, check_resume_dir,
                      count_rows, make_render, precision_line, preflight, read_jsonl, require, torch_dtype)

app = typer.Typer(add_completion=False, help=__doc__)

CKPT_EVERY = 25  # optimizer steps between full-state checkpoints


def train(pairs_path: Path, sft_adapter: Path, out: Path, model_name: str, dtype_name: str,
          load_in_4bit: bool, batch: int, beta: float, lr: float, seed: int, limit: int,
          resume_from: Path | None) -> None:
    import json
    import random
    import shutil

    quant = bnb_4bit_config(dtype_name) if load_in_4bit else None  # first: names bitsandbytes if absent
    torch = require("torch")
    F = require("torch.nn.functional")
    peft = require("peft")
    transformers = require("transformers")
    PeftModel = peft.PeftModel
    AutoConfig, AutoModelForCausalLM = transformers.AutoConfig, transformers.AutoModelForCausalLM
    AutoModelForImageTextToText, AutoTokenizer = transformers.AutoModelForImageTextToText, transformers.AutoTokenizer
    dtype = torch_dtype(dtype_name)

    out.mkdir(parents=True, exist_ok=True)
    ckpt_adapter = out / "ckpt_adapter"
    state_file = out / "train_state.pt"

    resume_dir = resume_from
    resuming = resume_from is not None  # validated before preflight: complete or refused

    tok = AutoTokenizer.from_pretrained(model_name)
    render = make_render(tok)

    pairs = read_jsonl(pairs_path)
    if limit:
        pairs = pairs[:limit]
    data = []
    for p in pairs:
        ci, cm = render(p["chosen_turns"])
        ri, rm = render(p["rejected_turns"])
        if max(len(ci), len(ri)) > MAX_TOKENS_PER_CONVERSATION:
            raise RuntimeError(f"sitting over 16k tokens in {p['probe_id']}|{p['pressure']}")
        data.append((ci, cm, ri, rm))
    print(f"{len(data)} pairs from {pairs_path}, max len "
          f"{max(max(len(d[0]), len(d[2])) for d in data)}")

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
        base_model.enable_input_require_grads()
    policy_src = str(resume_dir / "ckpt_adapter" / "policy") if resuming else str(sft_adapter)
    model = PeftModel.from_pretrained(base_model, policy_src,
                                      adapter_name="policy", is_trainable=True)
    model.load_adapter(str(sft_adapter), adapter_name="ref")  # frozen SFT reference
    model.set_adapter("policy")
    model.train()
    n_ckpt = sum(1 for m in model.modules() if getattr(m, "gradient_checkpointing", False))
    if not n_ckpt or not model.training:
        raise RuntimeError("gradient checkpointing did not engage (flag or training mode)")
    trainables = [p for p in model.parameters() if p.requires_grad]
    if not trainables:
        raise RuntimeError("no trainable parameters — policy adapter not trainable")
    print(f"gradient checkpointing on {n_ckpt} modules; "
          f"{sum(p.numel() for p in trainables)/1e6:.1f}M trainable params")
    opt = torch.optim.AdamW(trainables, lr=lr)

    base = model.get_base_model()
    trunk, head = base.model, base.lm_head
    softcap = base.config.get_text_config().final_logit_softcapping

    def seq_logp(ids, mask, use_policy, grad=False):
        model.set_adapter("policy" if use_policy else "ref")
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
            r = torch.cat(parts).float().sum()
        model.set_adapter("policy")
        return r

    # Parity check with the ref adapter active (selective head vs full forward).
    ci0, cm0 = data[0][0], data[0][1]
    w = cm0.index(True) + 128
    with torch.no_grad():
        sel = seq_logp(ci0[:w], cm0[:w], use_policy=False).cpu()
        model.set_adapter("ref")
        t0 = torch.tensor([ci0[:w]], device="cuda:0")
        full = base(input_ids=t0).logits
        model.set_adapter("policy")
        lp = torch.log_softmax(full[0, :-1].float(), -1)
        m0 = torch.tensor(cm0[1:w], dtype=torch.bool, device=lp.device)
        ref = lp[torch.arange(w - 1, device=lp.device),
                 t0[0, 1:].to(lp.device)][m0].sum().cpu()
    if not torch.allclose(sel, ref, rtol=1e-3, atol=0.5):
        raise RuntimeError(f"selective-head logp mismatch: {sel.item()} vs {ref.item()}")
    print(f"selective-head parity check ok: {sel.item():.3f} vs {ref.item():.3f}")

    # Sanity on FRESH runs: policy and ref must start identical (same SFT
    # weights). On resume the policy has trained past the ref by design.
    if not resuming:
        with torch.no_grad():
            pv = seq_logp(ci0[:w], cm0[:w], use_policy=True).cpu()
        if not torch.allclose(pv, sel, rtol=1e-3, atol=0.5):
            raise RuntimeError(f"policy/ref initial logp mismatch: {pv.item()} vs {sel.item()}")
        print("policy == ref at init: ok")

    def save_ckpt(step, order, pos, seen, log):
        tmp = out / "ckpt_adapter_save"
        model.save_pretrained(tmp, selected_adapters=["policy"])
        if ckpt_adapter.exists():
            shutil.rmtree(ckpt_adapter)
        tmp.rename(ckpt_adapter)
        torch.save({
            "step": step, "order": order, "pos": pos, "seen": seen,
            "opt": opt.state_dict(), "log": log,
            "py_rng": random.getstate(),
            "torch_rng": torch.get_rng_state(),
            "cuda_rng": torch.cuda.get_rng_state_all(),
        }, state_file)

    rng = random.Random(seed)
    step, log = 0, []
    start_pos, resume_order = 0, None
    if resuming:
        st = torch.load(resume_dir / "train_state.pt", weights_only=False)
        opt.load_state_dict(st["opt"])
        random.setstate(st["py_rng"])
        torch.set_rng_state(st["torch_rng"])
        torch.cuda.set_rng_state_all(st["cuda_rng"])
        step, log = st["step"], st["log"]
        start_pos, resume_order = st["pos"], st["order"]
        print(f"RESUMED: step={step} pos={start_pos} seen={st['seen']}")

    if resume_order is not None:
        order = resume_order
    else:
        order = list(range(len(data)))
        rng.shuffle(order)
    acc_loss, acc_correct, acc_n = 0.0, 0, 0
    opt.zero_grad()
    for n in range(start_pos, len(order)):
        ci, cm, ri, rm = data[order[n]]
        pol_c_v = seq_logp(ci, cm, True)
        pol_r_v = seq_logp(ri, rm, True)
        ref_c = seq_logp(ci, cm, False)
        ref_r = seq_logp(ri, rm, False)
        margin = beta * ((pol_c_v - ref_c) - (pol_r_v - ref_r))
        coef = beta * torch.sigmoid(-margin)
        (-(coef / batch) * seq_logp(ci, cm, True, grad=True)).backward()
        ((coef / batch) * seq_logp(ri, rm, True, grad=True)).backward()
        acc_loss += -F.logsigmoid(margin).item()
        acc_correct += int(margin.item() > 0)
        acc_n += 1
        if acc_n == batch or n == len(order) - 1:
            opt.step()
            opt.zero_grad()
            step += 1
            rec = {"step": step, "seen": n + 1, "loss": acc_loss / acc_n,
                   "pref_acc": acc_correct / acc_n,
                   "peak_gb": [round(torch.cuda.max_memory_allocated(d) / 2**30, 1)
                               for d in range(torch.cuda.device_count())]}
            for d in range(torch.cuda.device_count()):
                torch.cuda.reset_peak_memory_stats(d)
            log.append(rec)
            print(rec, flush=True)
            acc_loss, acc_correct, acc_n = 0.0, 0, 0
            if step % CKPT_EVERY == 0:
                save_ckpt(step, order, n + 1, n + 1, log)
                print(f"checkpoint: step {step}, pos {n+1}", flush=True)

    # save_pretrained writes one subdir per adapter; keep only the policy and
    # surface it at the collection step's expected path <out>/adapter.
    tmp = out / "adapter_save"
    model.save_pretrained(tmp, selected_adapters=["policy"])
    dest = out / "adapter"
    if dest.exists():
        shutil.rmtree(dest)
    (tmp / "policy").rename(dest)
    shutil.rmtree(tmp, ignore_errors=True)
    (out / "train_log.jsonl").write_text("\n".join(json.dumps(r) for r in log) + "\n")
    (out / "config.json").write_text(json.dumps({
        "model": model_name, "pairs": str(pairs_path), "n_pairs": len(data), "batch": batch,
        "beta": beta, "lr": lr, "epochs": 1, "lora_r": 32, "seed": seed,
        "reference": f"sft:{sft_adapter}", "init": f"sft:{sft_adapter}",
        "quant": f"nf4-4bit {dtype_name}-compute" if quant is not None else f"{dtype_name} (no quantization)",
        "masking": "assistant-tokens-only (tml_v0 parity)",
        "checkpoint_every_steps": CKPT_EVERY, "resumable": True,
    }, indent=2))
    if state_file.exists():
        state_file.unlink()  # clean completion marker
    shutil.rmtree(ckpt_adapter, ignore_errors=True)
    print(f"done: {step} steps; adapter at {dest}")


@app.command()
def main(
    pairs: Path = typer.Option(..., help="Stage-2 pairs (output of `pairs`)."),
    sft_adapter: Path = typer.Option(..., "--sft-adapter", help="The stage-1 adapter directory (output of gemma_sft): initial policy and frozen reference."),
    run: str = typer.Option("new-run", help="Run directory name under data/runs/ for the outputs."),
    out: Path | None = typer.Option(None, help="Output directory (default: <run dir>/gemma-sft-dpo)."),
    model: str = typer.Option(DEFAULT_MODEL, help="Gemma-family model id (the adapter must belong to it)."),
    dtype: str = typer.Option("bf16", help="Weights precision: bf16 (recipe of record), fp16 or fp32; the compute precision under --load-in-4bit."),
    load_in_4bit: bool = typer.Option(False, "--load-in-4bit", help="Quantize the base to nf4 (QLoRA, the archived chain's settings): the 24 GB profile. Needs bitsandbytes."),
    batch: int = typer.Option(8, help="Pairs per optimizer step, by gradient accumulation."),
    beta: float = typer.Option(0.1, help="DPO beta (setting of record 0.1)."),
    lr: float = typer.Option(1e-5, help="Learning rate (setting of record 1e-5)."),
    seed: int = typer.Option(3446, help="Shuffle seed."),
    limit: int = typer.Option(0, help="Train on the first N pairs only (smoke test)."),
    resume_from: Path | None = typer.Option(None, help="An output directory holding ckpt_adapter/ and train_state.pt to resume."),
    dry_run: bool = typer.Option(False, "--dry-run", help="Print the preflight summary and stop before anything loads."),
) -> None:
    n = count_rows(pairs)
    if not (sft_adapter / "adapter_config.json").exists():
        raise typer.BadParameter(f"{sft_adapter} is not a PEFT adapter directory (no adapter_config.json)")
    check_resume_dir(resume_from, "ckpt_adapter/policy")
    out = paths.output_path(out or paths.run_dir(run) / "gemma-sft-dpo")
    n_used = min(n, limit) if limit else n
    steps = -(-n_used // batch)
    if preflight(f"local stage-2 DPO of {model} from {sft_adapter}",
                 [f"pairs {pairs}: {n}" + (f", using the first {limit}" if limit else ""),
                  f"{dtype}, beta {beta:g}, lr {lr:g}, 1 epoch, batch {batch} (~{steps} steps), seed {seed}",
                  precision_line(model, dtype, load_in_4bit, training=True),
                  f"outputs -> {out}" + (f"; resuming from {resume_from}" if resume_from else "")],
                 dry_run):
        return
    train(pairs, sft_adapter, out, model, dtype, load_in_4bit, batch, beta, lr, seed, limit, resume_from)


if __name__ == "__main__":
    app()
