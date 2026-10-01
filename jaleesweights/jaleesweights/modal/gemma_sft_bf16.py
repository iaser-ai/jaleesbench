"""Stage-1 SFT rerun, bf16/B200 RECIPE OF RECORD (Waleed 2026-08-05).

Identical hypers to the original nf4 run (r32/alpha32, lr 5e-5, 2 epochs,
batch-8 accumulation, masked token-mean NLL, seed 3446, selective softcapped
head + startup parity check). Deviations vs our modal_gemma_sft.py:
bf16 LoRA (no bitsandbytes), B200 + cu128 image, full-state checkpointing
every 100 steps + --resume-from, spawn-detached launch.

Smoke:  uv run modal run -m jaleesweights.modal.gemma_sft_bf16 --data /pairs/sft_guided.jsonl --run-name smoke --limit 4 \\
            --local-data <sft_train_guided.jsonl>
Full:   uv run modal run --detach -m jaleesweights.modal.gemma_sft_bf16 --data /pairs/sft_guided.jsonl --run-name gemma-sft-guided-bf16 \\
            --local-data <sft_train_guided.jsonl>
--local-data is the file on this machine that /pairs/sft_guided.jsonl was uploaded from; a real
launch checks it first. Preflight only, no account needed:
        uv run python -m jaleesweights.modal.gemma_sft_bf16 --data /pairs/sft_guided.jsonl --run-name smoke
"""


import modal

from jaleesweights.modal._config import preflight_cli, MODEL, TRAIN_IMAGE, hf_secret, preflight, volume

CKPT_EVERY = 100  # optimizer steps between full-state checkpoints (deviation #1)
app = modal.App("jaleesbench-gemma-sft-bf16")
vol = volume()


@app.function(
    image=TRAIN_IMAGE, gpu="B200", timeout=8 * 60 * 60, volumes={"/vol": vol},
    secrets=[hf_secret()],
)
def train(data_path: str, run_name: str, batch: int, lr: float, epochs: int,
          seed: int, limit: int, resume_from: str):
    import json
    import pathlib
    import random

    import torch
    from peft import LoraConfig, PeftModel, get_peft_model
    from transformers import (
        AutoConfig, AutoModelForCausalLM, AutoModelForImageTextToText, AutoTokenizer,
    )

    out = pathlib.Path(f"/vol/runs/{run_name}")
    out.mkdir(parents=True, exist_ok=True)
    adapter_dir = out / "adapter"
    state_file = out / "train_state.pt"

    resume_dir = pathlib.Path(f"/vol/runs/{resume_from}") if resume_from else None
    resuming = bool(resume_from) and (resume_dir / "adapter").exists() and (resume_dir / "train_state.pt").exists()

    tok = AutoTokenizer.from_pretrained(MODEL)

    def render(turns):
        ids, mask, prev_ids = [], [], []
        for i in range(len(turns)):
            text = tok.apply_chat_template(turns[: i + 1], tokenize=False)
            full = tok(text, add_special_tokens=False).input_ids
            if full[: len(prev_ids)] != prev_ids:
                raise RuntimeError("chat template is not prefix-stable")
            span = full[len(prev_ids):]
            ids.extend(span)
            mask.extend([turns[i]["role"] == "assistant"] * len(span))
            prev_ids = full
        return ids, mask

    rows = [json.loads(l) for l in open(f"/vol{data_path}")]
    if limit:
        rows = rows[:limit]
    data = []
    for r in rows:
        ids, mask = render(r["turns"])
        if len(ids) > 16384:
            raise RuntimeError(f"sitting over 16k tokens in {r.get('probe_id')}|{r.get('pressure')}")
        data.append((ids, mask))
    print(f"{len(data)} examples from {data_path}, max len {max(len(d[0]) for d in data)}")

    cfg = AutoConfig.from_pretrained(MODEL)
    multimodal = hasattr(cfg, "vision_config")
    loader = AutoModelForImageTextToText if multimodal else AutoModelForCausalLM
    base_model = loader.from_pretrained(
        MODEL, torch_dtype=torch.bfloat16, device_map="auto", attn_implementation="sdpa",
    )  # bf16, no quantization (Waleed 2026-08-05)
    base_model.config.use_cache = False
    # bf16 equivalents of prepare_model_for_kbit_training's grad-checkpointing setup (no bnb):
    base_model.gradient_checkpointing_enable(gradient_checkpointing_kwargs={"use_reentrant": False})
    base_model.enable_input_require_grads()  # so grads flow to LoRA through the frozen base under GC
    proj = "(q_proj|k_proj|v_proj|o_proj|gate_proj|up_proj|down_proj)"
    if resuming:
        # Restore the LoRA weights from the checkpoint adapter (deviation #2).
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
        vol.commit()

    # Resume state (deviation #2): restore optimizer + RNG + data position.
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
                vol.commit()

    model.save_pretrained(adapter_dir)
    (out / "train_log.jsonl").write_text("\n".join(json.dumps(r) for r in log) + "\n")
    (out / "config.json").write_text(json.dumps({
        "model": MODEL, "data": data_path, "n_examples": len(data),
        "batch": batch, "lr": lr, "epochs": epochs, "lora_r": 32, "seed": seed,
        "objective": "masked token-mean NLL (SL-CAI context distillation)",
        "quant": "bf16 (no quantization; Waleed 2026-08-05)", "masking": "assistant-tokens-only (tml_v0 parity)",
        "checkpoint_every_steps": CKPT_EVERY, "resumable": True,
    }, indent=2))
    if state_file.exists():
        state_file.unlink()  # clean completion marker
    vol.commit()
    print(f"done: {step} steps; adapter at /vol/runs/{run_name}/adapter")


@app.local_entrypoint()
def main(data: str, run_name: str, batch: int = 8, lr: float = 5e-5,
         epochs: int = 2, seed: int = 3446, limit: int = 0, resume_from: str = "",
         local_data: str = "", dry_run: bool = False):
    # --local-data: the training set on this machine that `data` was (or will be) uploaded from;
    # checked for existence and row count before anything is rented.
    if preflight(f"stage-1 SFT of {MODEL}: run {run_name}, batch {batch}, lr {lr}, {epochs} epochs, seed {seed}"
                 + (f", limit {limit}" if limit else "") + (f", resume from {resume_from}" if resume_from else ""),
                 "B200", [data], [f"/runs/{run_name}/adapter", f"/runs/{run_name}/train_log.jsonl"], dry_run,
                 local={data: (local_data, None)} if local_data else None, required_local=[data]):
        return
    if limit:
        # smoke: block (remote) so loss / memory / B200-compat print directly to this client.
        train.remote(data, run_name, batch, lr, epochs, seed, limit, resume_from)
    else:
        # full run: --detach + spawn so it survives client/network drops (nf4 run-1 flap cancel).
        call = train.spawn(data, run_name, batch, lr, epochs, seed, limit, resume_from)
        print(f"spawned SFT: call_id={call.object_id}  run_name={run_name} resume_from={resume_from or '(fresh)'}")


if __name__ == "__main__":
    preflight_cli(main)
