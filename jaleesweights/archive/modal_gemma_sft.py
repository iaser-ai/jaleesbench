"""SL-CAI stage 1: SFT gemma-4-31b on its own good guided responses,
rendered unstated — Modal job (issue #21, 08-04).

Context distillation: the model learns to produce its guided-ceiling
behavior without the guide in context. Same QLoRA/masking/selective-head
machinery as modal_gemma_dpo.py; loss is plain token-mean NLL over masked
assistant tokens (tml_v0 parity: pressure turn in context, masked).
lr 5e-5: SFT convention runs hotter than DPO's calibrated 1e-5 — the DPO
rate was tuned for DPO's small effective gradient, not for NLL.

Run:
  modal run tmp/dpo-experiment/modal_gemma_sft.py --data /pairs/sft_guided.jsonl \
      --run-name gemma-sft-guided --batch 8 --lr 5e-5 --epochs 2
"""

import modal

MODEL = "google/gemma-4-31B-it"
app = modal.App("jaleesbench-gemma-sft")
vol = modal.Volume.from_name("gemma-dpo")

image = (
    modal.Image.debian_slim(python_version="3.12")
    .pip_install(
        "torch==2.6.0", "transformers>=4.53", "peft>=0.15", "bitsandbytes>=0.45",
        "accelerate>=1.3", "hf_transfer",
    )
    .env({"HF_HUB_ENABLE_HF_TRANSFER": "1", "HF_HOME": "/vol/hf-cache",
          "PYTORCH_CUDA_ALLOC_CONF": "expandable_segments:True"})
)


@app.function(
    image=image, gpu="H200", timeout=6 * 60 * 60, volumes={"/vol": vol},
    secrets=[modal.Secret.from_name("huggingface")],
)
def train(data_path: str, run_name: str, batch: int, lr: float, epochs: int,
          seed: int):
    import json
    import pathlib
    import random

    import torch
    from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
    from transformers import (
        AutoConfig, AutoModelForCausalLM, AutoModelForImageTextToText,
        AutoTokenizer, BitsAndBytesConfig,
    )

    out = pathlib.Path(f"/vol/runs/{run_name}")
    out.mkdir(parents=True, exist_ok=True)

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
    data = []
    for r in rows:
        ids, mask = render(r["turns"])
        if len(ids) > 16384:
            raise RuntimeError(f"sitting over 16k tokens in {r['probe_id']}|{r['pressure']}")
        data.append((ids, mask))
    print(f"{len(data)} examples from {data_path}, max len "
          f"{max(len(d[0]) for d in data)}")

    cfg = AutoConfig.from_pretrained(MODEL)
    multimodal = hasattr(cfg, "vision_config")
    loader = AutoModelForImageTextToText if multimodal else AutoModelForCausalLM
    model = loader.from_pretrained(
        MODEL, torch_dtype=torch.bfloat16, device_map="auto",
        quantization_config=BitsAndBytesConfig(
            load_in_4bit=True, bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=torch.bfloat16,
        ),
        attn_implementation="sdpa",
    )
    model.config.use_cache = False
    model = prepare_model_for_kbit_training(
        model, use_gradient_checkpointing=True,
        gradient_checkpointing_kwargs={"use_reentrant": False},
    )
    proj = "(q_proj|k_proj|v_proj|o_proj|gate_proj|up_proj|down_proj)"
    model = get_peft_model(model, LoraConfig(
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

    # Parity check vs the model's own full forward (as in the DPO driver).
    ci0, cm0 = data[0]
    w = cm0.index(True) + 128
    with torch.no_grad():
        sel, _ = seq_logp(ci0[:w], cm0[:w])
        sel = sel.cpu()
        t0 = torch.tensor([ci0[:w]], device="cuda:0")
        full = base(input_ids=t0).logits
        lp = torch.log_softmax(full[0, :-1].float(), -1)
        m0 = torch.tensor(cm0[1:w], dtype=torch.bool, device=lp.device)
        ref = lp[torch.arange(w - 1, device=lp.device),
                 t0[0, 1:].to(lp.device)][m0].sum().cpu()
    if not torch.allclose(sel, ref, rtol=1e-3, atol=0.5):
        raise RuntimeError(f"selective-head logp mismatch: {sel.item()} vs {ref.item()}")
    print(f"selective-head parity check ok: {sel.item():.3f} vs {ref.item():.3f}")

    rng = random.Random(seed)
    step, acc_loss, acc_n, log = 0, 0.0, 0, []
    opt.zero_grad()
    seen = 0
    for ep in range(epochs):
        order = list(range(len(data)))
        rng.shuffle(order)
        for idx in order:
            ids, mask = data[idx]
            logp, ntok = seq_logp(ids, mask, grad=True)
            loss = -(logp / ntok)
            (loss / batch).backward()
            acc_loss += loss.item()
            acc_n += 1
            seen += 1
            if acc_n == batch or seen == epochs * len(data):
                opt.step()
                opt.zero_grad()
                step += 1
                rec = {"step": step, "epoch": ep, "seen": seen,
                       "nll_per_token": acc_loss / acc_n,
                       "peak_gb": [round(torch.cuda.max_memory_allocated(d) / 2**30, 1)
                                   for d in range(torch.cuda.device_count())]}
                for d in range(torch.cuda.device_count()):
                    torch.cuda.reset_peak_memory_stats(d)
                log.append(rec)
                print(rec, flush=True)
                acc_loss, acc_n = 0.0, 0
                vol.commit()

    model.save_pretrained(out / "adapter")
    (out / "train_log.jsonl").write_text("\n".join(json.dumps(r) for r in log) + "\n")
    (out / "config.json").write_text(json.dumps({
        "model": MODEL, "data": data_path, "n_examples": len(data),
        "batch": batch, "lr": lr, "epochs": epochs, "lora_r": 32, "seed": seed,
        "objective": "masked token-mean NLL (SL-CAI context distillation)",
        "quant": "nf4-4bit bf16-compute", "masking": "assistant-tokens-only (tml_v0 parity)",
    }, indent=2))
    vol.commit()
    print(f"done: {step} steps; adapter at /vol/runs/{run_name}/adapter")


@app.local_entrypoint()
def main(data: str, run_name: str, batch: int = 8, lr: float = 5e-5,
         epochs: int = 2, seed: int = 3446):
    train.remote(data, run_name, batch, lr, epochs, seed)
