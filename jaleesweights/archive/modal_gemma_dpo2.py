"""SL-CAI stage 2: DPO on top of the SFT checkpoint (issue #21, RL-CAI analog).

Same DPO machinery as modal_gemma_dpo.py with one structural change: the
REFERENCE policy is the SFT checkpoint, not raw base (matching the published
CAI/RLHF structure — the preference stage sharpens the distilled policy, and
the KL anchor must be the distilled policy or DPO would spend its budget
undoing the SFT). Implemented as two PEFT adapters over the same nf4 base:
"policy" (initialized from SFT, trainable) and "ref" (frozen SFT copy).

Run:
  modal run tmp/dpo-experiment/modal_gemma_dpo2.py --pairs /pairs/pairs_sft2.jsonl \
      --sft-run gemma-sft-guided --run-name gemma-sft-dpo --batch 8
"""

import modal

MODEL = "google/gemma-4-31B-it"
app = modal.App("jaleesbench-gemma-dpo2")
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
def train(pairs_path: str, sft_run: str, run_name: str, batch: int, beta: float,
          lr: float, seed: int):
    import json
    import pathlib
    import random
    import shutil

    import torch
    import torch.nn.functional as F
    from peft import PeftModel, prepare_model_for_kbit_training
    from transformers import (
        AutoConfig, AutoModelForCausalLM, AutoModelForImageTextToText,
        AutoTokenizer, BitsAndBytesConfig,
    )

    out = pathlib.Path(f"/vol/runs/{run_name}")
    out.mkdir(parents=True, exist_ok=True)
    sft_path = f"/vol/runs/{sft_run}/adapter"

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

    pairs = [json.loads(l) for l in open(f"/vol{pairs_path}")]
    data = []
    for p in pairs:
        ci, cm = render(p["chosen_turns"])
        ri, rm = render(p["rejected_turns"])
        if max(len(ci), len(ri)) > 16384:
            raise RuntimeError(f"sitting over 16k tokens in {p['probe_id']}|{p['pressure']}")
        data.append((ci, cm, ri, rm))
    print(f"{len(data)} pairs from {pairs_path}, max len "
          f"{max(max(len(d[0]), len(d[2])) for d in data)}")

    cfg = AutoConfig.from_pretrained(MODEL)
    multimodal = hasattr(cfg, "vision_config")
    loader = AutoModelForImageTextToText if multimodal else AutoModelForCausalLM
    base_model = loader.from_pretrained(
        MODEL, torch_dtype=torch.bfloat16, device_map="auto",
        quantization_config=BitsAndBytesConfig(
            load_in_4bit=True, bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=torch.bfloat16,
        ),
        attn_implementation="sdpa",
    )
    base_model.config.use_cache = False
    base_model = prepare_model_for_kbit_training(
        base_model, use_gradient_checkpointing=True,
        gradient_checkpointing_kwargs={"use_reentrant": False},
    )
    model = PeftModel.from_pretrained(base_model, sft_path,
                                      adapter_name="policy", is_trainable=True)
    model.load_adapter(sft_path, adapter_name="ref")  # frozen
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

    # Sanity: policy and ref must start identical (same SFT weights).
    with torch.no_grad():
        pv = seq_logp(ci0[:w], cm0[:w], use_policy=True).cpu()
    if not torch.allclose(pv, sel, rtol=1e-3, atol=0.5):
        raise RuntimeError(f"policy/ref initial logp mismatch: {pv.item()} vs {sel.item()}")
    print("policy == ref at init: ok")

    rng = random.Random(seed)
    order = list(range(len(data)))
    rng.shuffle(order)
    step, acc_loss, acc_correct, log = 0, 0.0, 0, []
    opt.zero_grad()
    for n, idx in enumerate(order, 1):
        ci, cm, ri, rm = data[idx]
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
        if n % batch == 0 or n == len(order):
            opt.step()
            opt.zero_grad()
            step += 1
            k = batch if n % batch == 0 else n % batch
            rec = {"step": step, "seen": n, "loss": acc_loss / k,
                   "pref_acc": acc_correct / k,
                   "peak_gb": [round(torch.cuda.max_memory_allocated(d) / 2**30, 1)
                               for d in range(torch.cuda.device_count())]}
            for d in range(torch.cuda.device_count()):
                torch.cuda.reset_peak_memory_stats(d)
            log.append(rec)
            print(rec, flush=True)
            acc_loss, acc_correct = 0.0, 0
            vol.commit()

    # save_pretrained writes one subdir per adapter; keep only the policy and
    # surface it at the eval script's expected path /runs/<run>/adapter.
    tmp = out / "adapter_save"
    model.save_pretrained(tmp, selected_adapters=["policy"])
    dest = out / "adapter"
    if dest.exists():
        shutil.rmtree(dest)
    (tmp / "policy").rename(dest)
    shutil.rmtree(tmp, ignore_errors=True)
    (out / "train_log.jsonl").write_text("\n".join(json.dumps(r) for r in log) + "\n")
    (out / "config.json").write_text(json.dumps({
        "model": MODEL, "pairs": pairs_path, "n_pairs": len(data), "batch": batch,
        "beta": beta, "lr": lr, "epochs": 1, "lora_r": 32, "seed": seed,
        "reference": f"sft:{sft_run}", "init": f"sft:{sft_run}",
        "quant": "nf4-4bit bf16-compute", "masking": "assistant-tokens-only (tml_v0 parity)",
    }, indent=2))
    vol.commit()
    print(f"done: {step} steps; adapter at /vol/runs/{run_name}/adapter")


@app.local_entrypoint()
def main(pairs: str, run_name: str, sft_run: str = "gemma-sft-guided",
         batch: int = 8, beta: float = 0.1, lr: float = 1e-5, seed: int = 3446):
    train.remote(pairs, sft_run, run_name, batch, beta, lr, seed)
