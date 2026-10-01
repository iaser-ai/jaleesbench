"""DPO-tune gemma-4-31b on JaleesBench pairs — Modal job (issue #21 hedge arm).

Mirrors the tinker runs: β0.1, lr 1e-5, 1 epoch, LoRA r32 on all linear
layers, batch 4 (1/cell arm) or 16 (expanded arm) via grad accumulation.
Loss masking matches tml_v0: only assistant tokens in the completion carry
loss; the authored pressure user turn sits in context but is masked.
Deviation from tinker (bf16 LoRA): base is bitsandbytes 4-bit nf4 (QLoRA),
bf16 compute. Ref logps come from the same base with the adapter disabled.

Setup (once):
  modal volume create gemma-dpo
  modal volume put gemma-dpo tmp/dpo-experiment/pairs_train70_gemma-4-31b.jsonl /pairs/pairs_small.jsonl
  modal volume put gemma-dpo tmp/dpo-experiment/pairs_train70_gemma-4-31b_expanded4.jsonl /pairs/pairs_expanded.jsonl
  # No HF token needed: gemma-4 is Apache 2.0 and ungated (verified 08-03).

Run:
  modal run tmp/dpo-experiment/modal_gemma_dpo.py --pairs /pairs/pairs_small.jsonl --run-name gemma-dpo-r1 --batch 4
  modal run tmp/dpo-experiment/modal_gemma_dpo.py --pairs /pairs/pairs_expanded.jsonl --run-name gemma-dpo-r2 --batch 16

Adapter lands in the volume at /runs/<run-name>/adapter (+ train_log.jsonl).
"""

import modal

MODEL = "google/gemma-4-31B-it"
app = modal.App("jaleesbench-gemma-dpo")
vol = modal.Volume.from_name("gemma-dpo", create_if_missing=True)

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
def train(pairs_path: str, run_name: str, batch: int, beta: float, lr: float,
          seed: int, probe: bool = False):
    import json
    import pathlib
    import random

    import torch
    import torch.nn.functional as F
    from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
    from transformers import (
        AutoConfig, AutoModelForCausalLM, AutoModelForImageTextToText,
        AutoTokenizer, BitsAndBytesConfig,
    )

    out = pathlib.Path(f"/vol/runs/{run_name}")
    out.mkdir(parents=True, exist_ok=True)

    tok = AutoTokenizer.from_pretrained(MODEL)

    def render(turns):
        """Token ids + per-token loss mask for one sitting.

        Prompt = the shared opening user turn; completion = everything after.
        Mask is True only on assistant-turn tokens inside the completion,
        computed by prefix-rendering the conversation turn by turn.
        """
        # Text-level render + explicit tokenization: tokenize=True returns a
        # BatchEncoding in transformers>=4.53, which broke naive id-slicing.
        # The template's <bos> is in the rendered text, so no special tokens.
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

    # gemma-4-31B is multimodal: dispatch on config, and confine LoRA to the
    # language model's attn/mlp projections (vision tower stays frozen —
    # matches the tinker arms, which adapted a text-only model).
    cfg = AutoConfig.from_pretrained(MODEL)
    multimodal = hasattr(cfg, "vision_config")
    loader = AutoModelForImageTextToText if multimodal else AutoModelForCausalLM
    model = loader.from_pretrained(
        MODEL, torch_dtype=torch.bfloat16, device_map="auto",
        quantization_config=BitsAndBytesConfig(
            load_in_4bit=True, bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=torch.bfloat16,
        ),
        # sdpa, not eager: eager materializes ~seq^2 attention probs per layer
        # (~5GB/layer at 8.6k tokens) — the OOM driver on attempts 2-3.
        attn_implementation="sdpa",
    )
    model.config.use_cache = False
    # Canonical QLoRA order: k-bit prep (incl. checkpointing) BEFORE the LoRA
    # wrap — enabling checkpointing on the wrapped model didn't take.
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
    # Checkpointing only fires when BOTH the flag is set AND the module is in
    # training mode — transformers guards with `if self.gradient_checkpointing
    # and self.training`. Eval mode made it a silent no-op (the whole OOM saga).
    model.train()
    n_ckpt = sum(1 for m in model.modules() if getattr(m, "gradient_checkpointing", False))
    if not n_ckpt or not model.training:
        raise RuntimeError("gradient checkpointing did not engage (flag or training mode)")
    print(f"gradient checkpointing active on {n_ckpt} modules (training mode: {model.training})")
    model.print_trainable_parameters()
    opt = torch.optim.AdamW((p for p in model.parameters() if p.requires_grad), lr=lr)

    # Selective logp head: run the trunk over the full sequence but apply the
    # 262k-vocab lm_head ONLY at scored (masked assistant) positions, chunked,
    # via gather - logsumexp. Full-position fp32 log-softmax retained ~40GB on
    # an 8.6k sitting — the step-2 OOM driver; this caps the head at ~6GB.
    base = model.get_base_model()
    trunk, head = base.model, base.lm_head
    # gemma-4 reintroduced final logit softcapping — the wrapper applies it
    # after lm_head, so the selective head must too (parity check caught this).
    softcap = base.config.get_text_config().final_logit_softcapping

    def seq_logp(ids, mask, use_adapter, grad=False):
        t = torch.tensor([ids], device="cuda:0")
        pos = [i for i in range(len(ids) - 1) if mask[i + 1]]
        tgt = torch.tensor([ids[i + 1] for i in pos])
        pos = torch.tensor(pos)
        with torch.enable_grad() if grad else torch.no_grad():
            if use_adapter:
                h = trunk(input_ids=t).last_hidden_state
            else:
                with model.disable_adapter():
                    h = trunk(input_ids=t).last_hidden_state
            # device_map=auto: hidden states land on the last shard; index
            # tensors must follow (the lm_head hook moves its own inputs).
            pos, tgt = pos.to(h.device), tgt.to(h.device)
            hs = h[0, pos].to(head.weight.dtype)
            parts = []
            for s in range(0, len(tgt), 256):
                lg = head(hs[s:s + 256])
                if softcap is not None:
                    lg = torch.tanh(lg / softcap) * softcap
                idx = tgt[s:s + 256, None].to(lg.device)
                parts.append(lg.gather(1, idx)[:, 0] - lg.logsumexp(-1))
            return torch.cat(parts).float().sum()

    # Fail-fast parity check: selective head vs the model's own full forward
    # on a short window of the first pair (catches un-normed hidden states,
    # dtype drift, or off-by-one position mapping).
    ci0, cm0 = data[0][0], data[0][1]
    w = cm0.index(True) + 128
    with torch.no_grad():
        sel = seq_logp(ci0[:w], cm0[:w], use_adapter=False).cpu()
        t0 = torch.tensor([ci0[:w]], device="cuda:0")
        with model.disable_adapter():
            full = base(input_ids=t0).logits
        lp = torch.log_softmax(full[0, :-1].float(), -1)
        m0 = torch.tensor(cm0[1:w], dtype=torch.bool, device=lp.device)
        ref = lp[torch.arange(w - 1, device=lp.device),
                 t0[0, 1:].to(lp.device)][m0].sum().cpu()
    if not torch.allclose(sel, ref, rtol=1e-3, atol=0.5):
        raise RuntimeError(f"selective-head logp mismatch: {sel.item()} vs {ref.item()}")
    print(f"selective-head parity check ok: {sel.item():.3f} vs {ref.item():.3f}")

    if probe:
        # Memory probe: the 3 longest pairs through the full grad machinery,
        # per-pair peak/live readouts, then exit. No optimizer, no save.
        worst = sorted(range(len(data)), key=lambda i: -(len(data[i][0]) + len(data[i][2])))[:3]
        for idx in worst:
            ci, cm, ri, rm = data[idx]
            for d in range(torch.cuda.device_count()):
                torch.cuda.reset_peak_memory_stats(d)
            pol_c_v = seq_logp(ci, cm, True)
            pol_r_v = seq_logp(ri, rm, True)
            ref_c = seq_logp(ci, cm, False)
            ref_r = seq_logp(ri, rm, False)
            margin = beta * ((pol_c_v - ref_c) - (pol_r_v - ref_r))
            coef = beta * torch.sigmoid(-margin)
            (-(coef / batch) * seq_logp(ci, cm, True, grad=True)).backward()
            ((coef / batch) * seq_logp(ri, rm, True, grad=True)).backward()
            print({"probe_pair": idx, "len_c": len(ci), "len_r": len(ri),
                   "pair_peak_gb": [round(torch.cuda.max_memory_allocated(d) / 2**30, 1)
                                    for d in range(torch.cuda.device_count())],
                   "live_after_gb": [round(torch.cuda.memory_allocated(d) / 2**30, 1)
                                     for d in range(torch.cuda.device_count())]}, flush=True)
        return

    rng = random.Random(seed)
    order = list(range(len(data)))
    rng.shuffle(order)
    step, acc_loss, acc_correct, log = 0, 0.0, 0, []
    opt.zero_grad()
    for n, idx in enumerate(order, 1):
        ci, cm, ri, rm = data[idx]
        # Memory-efficient DPO: value pass grad-free for the margin, then one
        # policy forward+backward per sequence with the precomputed scalar
        # coefficient — never two autograd graphs alive at once.
        # d(-logsigmoid(m))/d(pol_c) = -beta*sigmoid(-m); w.r.t. pol_r: +.
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
                               for d in range(torch.cuda.device_count())],
                   "live_gb": [round(torch.cuda.memory_allocated(d) / 2**30, 1)
                               for d in range(torch.cuda.device_count())]}
            for d in range(torch.cuda.device_count()):
                torch.cuda.reset_peak_memory_stats(d)
            log.append(rec)
            print(rec, flush=True)
            acc_loss, acc_correct = 0.0, 0
            vol.commit()

    model.save_pretrained(out / "adapter")
    (out / "train_log.jsonl").write_text("\n".join(json.dumps(r) for r in log) + "\n")
    (out / "config.json").write_text(json.dumps({
        "model": MODEL, "pairs": pairs_path, "n_pairs": len(data), "batch": batch,
        "beta": beta, "lr": lr, "epochs": 1, "lora_r": 32, "seed": seed,
        "quant": "nf4-4bit bf16-compute", "masking": "assistant-tokens-only (tml_v0 parity)",
    }, indent=2))
    vol.commit()
    print(f"done: {step} steps; adapter at /vol/runs/{run_name}/adapter")


@app.function(
    image=image, gpu="H200", timeout=45 * 60, volumes={"/vol": vol},
    secrets=[modal.Secret.from_name("huggingface")],
)
def sample(run_name: str, pairs_path: str, n: int = 3, max_new: int = 400):
    """Generate base-vs-adapter responses for the first n probe openings —
    qualitative sanity gate before spending on the full eval."""
    import json

    import torch
    from peft import PeftModel
    from transformers import (
        AutoConfig, AutoModelForCausalLM, AutoModelForImageTextToText,
        AutoTokenizer, BitsAndBytesConfig,
    )

    tok = AutoTokenizer.from_pretrained(MODEL)
    cfg = AutoConfig.from_pretrained(MODEL)
    loader = AutoModelForImageTextToText if hasattr(cfg, "vision_config") else AutoModelForCausalLM
    model = loader.from_pretrained(
        MODEL, torch_dtype=torch.bfloat16, device_map="cuda",
        quantization_config=BitsAndBytesConfig(
            load_in_4bit=True, bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=torch.bfloat16,
        ),
    )
    model = PeftModel.from_pretrained(model, f"/vol/runs/{run_name}/adapter")
    model.eval()

    seen, prompts = set(), []
    for line in open(f"/vol{pairs_path}"):
        p = json.loads(line)
        q = p["chosen_turns"][0]["content"]
        if q not in seen:
            seen.add(q)
            prompts.append(q)
        if len(prompts) >= n:
            break

    for q in prompts:
        ids = tok.apply_chat_template(
            [{"role": "user", "content": q}], tokenize=False, add_generation_prompt=True)
        t = tok(ids, add_special_tokens=False, return_tensors="pt").input_ids.cuda()
        for label, ctx in (("ADAPTER", None), ("BASE", model.disable_adapter)):
            with torch.no_grad():
                if ctx is None:
                    out = model.generate(t, max_new_tokens=max_new, do_sample=False)
                else:
                    with ctx():
                        out = model.generate(t, max_new_tokens=max_new, do_sample=False)
            text = tok.decode(out[0, t.shape[1]:], skip_special_tokens=True)
            print(f"\n===== [{label}] {q[:90]}...\n{text}", flush=True)


@app.local_entrypoint()
def main(pairs: str, run_name: str, batch: int = 4, beta: float = 0.1,
         lr: float = 1e-5, seed: int = 3446, probe: bool = False,
         do_sample_check: bool = False):
    if do_sample_check:
        sample.remote(run_name, pairs)
    else:
        train.remote(pairs, run_name, batch, beta, lr, seed, probe)
