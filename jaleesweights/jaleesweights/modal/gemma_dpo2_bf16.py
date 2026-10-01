"""SL-CAI stage 2 (DPO-on-SFT, SFT-as-reference), bf16/B200 RECIPE OF RECORD
(Waleed 2026-08-05). Same two-adapter machinery as modal_gemma_dpo2.py
(policy init = SFT, ref = frozen SFT, selective softcapped head, parity +
policy==ref-at-init checks), with the recipe-of-record deviations:

  0. bf16 LoRA, NO bitsandbytes/nf4 anywhere; B200 + CUDA 12.8/cu128 image.
  1. FULL-STATE CHECKPOINTING every CKPT_EVERY optimizer steps: policy adapter
     + AdamW state + (data order, position, seen) + py/torch/cuda RNG →
     volume + vol.commit; clean completion removes train_state.pt.
  2. --resume-from <run_name> restores all of it.
  3. Full runs launch spawn-detached (survive client/network death).

NOTE: the SFT reference must itself be a bf16-recipe checkpoint (pass
--sft-run gemma-sft-guided-bf16) — mixing an nf4-trained adapter as ref would
reintroduce the confound this recipe exists to remove.

Smoke:  uv run modal run -m jaleesweights.modal.gemma_dpo2_bf16 --pairs /pairs/pairs_sftbf16.jsonl --sft-run gemma-sft-guided-bf16 --run-name smoke --limit 4
Full:   uv run modal run --detach -m jaleesweights.modal.gemma_dpo2_bf16 --pairs /pairs/pairs_sftbf16.jsonl --sft-run gemma-sft-guided-bf16 --run-name gemma-sft-dpo-bf16
Preflight only: add --dry-run.
"""

import modal

from jaleesweights.modal._config import preflight_cli, MODEL, TRAIN_IMAGE, hf_secret, preflight, volume

CKPT_EVERY = 25  # optimizer steps between full-state checkpoints (~84-step runs)
app = modal.App("jaleesbench-gemma-dpo2-bf16")
vol = volume()


@app.function(
    image=TRAIN_IMAGE, gpu="B200", timeout=8 * 60 * 60, volumes={"/vol": vol},
    secrets=[hf_secret()],
)
def train(pairs_path: str, sft_run: str, run_name: str, batch: int, beta: float,
          lr: float, seed: int, limit: int, resume_from: str):
    import json
    import pathlib
    import random
    import shutil

    import torch
    import torch.nn.functional as F
    from peft import PeftModel
    from transformers import (
        AutoConfig, AutoModelForCausalLM, AutoModelForImageTextToText, AutoTokenizer,
    )

    out = pathlib.Path(f"/vol/runs/{run_name}")
    out.mkdir(parents=True, exist_ok=True)
    sft_path = f"/vol/runs/{sft_run}/adapter"
    ckpt_adapter = out / "ckpt_adapter"
    state_file = out / "train_state.pt"

    resume_dir = pathlib.Path(f"/vol/runs/{resume_from}") if resume_from else None
    resuming = bool(resume_from) and (resume_dir / "ckpt_adapter" / "policy").exists() \
        and (resume_dir / "train_state.pt").exists()

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
    if limit:
        pairs = pairs[:limit]
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
        MODEL, torch_dtype=torch.bfloat16, device_map="auto", attn_implementation="sdpa",
    )  # bf16, no quantization (recipe of record)
    base_model.config.use_cache = False
    base_model.gradient_checkpointing_enable(gradient_checkpointing_kwargs={"use_reentrant": False})
    base_model.enable_input_require_grads()
    policy_src = str(resume_dir / "ckpt_adapter" / "policy") if resuming else sft_path
    model = PeftModel.from_pretrained(base_model, policy_src,
                                      adapter_name="policy", is_trainable=True)
    model.load_adapter(sft_path, adapter_name="ref")  # frozen SFT reference
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
        vol.commit()

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
        "quant": "bf16 (no quantization; recipe of record 2026-08-05)",
        "masking": "assistant-tokens-only (tml_v0 parity)",
        "checkpoint_every_steps": CKPT_EVERY, "resumable": True,
    }, indent=2))
    if state_file.exists():
        state_file.unlink()  # clean completion marker
    shutil.rmtree(ckpt_adapter, ignore_errors=True)
    vol.commit()
    print(f"done: {step} steps; adapter at /vol/runs/{run_name}/adapter")


@app.local_entrypoint()
def main(pairs: str, run_name: str, sft_run: str = "gemma-sft-guided-bf16",
         batch: int = 8, beta: float = 0.1, lr: float = 1e-5, seed: int = 3446,
         limit: int = 0, resume_from: str = "", local_pairs: str = "", dry_run: bool = False):
    if preflight(f"stage-2 DPO of {MODEL} from stage-1 run {sft_run}: run {run_name}, batch {batch}, beta {beta}, "
                 f"lr {lr}, 1 epoch, seed {seed}" + (f", limit {limit}" if limit else ""),
                 "B200", [pairs, f"/runs/{sft_run}/adapter"],
                 [f"/runs/{run_name}/adapter", f"/runs/{run_name}/train_log.jsonl"], dry_run,
                 local={pairs: (local_pairs, None)} if local_pairs else None, required_local=[pairs]):
        return
    if limit:
        train.remote(pairs, sft_run, run_name, batch, beta, lr, seed, limit, resume_from)
    else:
        call = train.spawn(pairs, sft_run, run_name, batch, beta, lr, seed, limit, resume_from)
        print(f"spawned DPO: call_id={call.object_id}  run_name={run_name} "
              f"resume_from={resume_from or '(fresh)'}")


if __name__ == "__main__":
    preflight_cli(main)
