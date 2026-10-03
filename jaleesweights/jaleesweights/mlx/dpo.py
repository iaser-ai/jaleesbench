"""Stage 2 of the recipe on a Mac with MLX: preference optimization (DPO) on the stage-1
model's own rated samples, with the stage-1 model as reference. `mlx_lm` has no such
trainer, so this is the recipe's objective written out:

    loss = -log sigmoid(beta * [(pi_chosen - ref_chosen) - (pi_rejected - ref_rejected)])

where each term is a sitting's log-probability summed over its assistant tokens. The policy
starts as the stage-1 adapter and the reference is that same adapter, frozen — so the
reference terms are computed once, before the first update, and only one model is ever in
memory. Settings of record: beta 0.1, lr 1e-5, one pass, batch 8 by gradient accumulation,
seed 3446. The policy == reference check runs at the start. The adapter and the training
log are written after every optimizer step (the adapter by write-then-rename), so Ctrl-C
leaves the latest completed step's adapter. Memory grows with the sitting's length — measured
on gemma-4-E4B 4-bit: about 4 GB plus 4.8 GB per 1,000 tokens — so the default
--max-seq-length (4,096) is what the default --memory-limit-gb (24) can hold.

    uv run python -m jaleesweights.mlx.dpo --pairs data/runs/tutorial/pairs.jsonl \\
        --sft-adapter data/runs/tutorial/mlx-sft/adapter --run tutorial
"""

import json
import math
import os
import random
import shutil
import time
from pathlib import Path

import typer

from .. import paths
from ._common import DEFAULT_MODEL, cap_memory, ceiling_line, precision_line, preflight, read_jsonl, require_adapter, require_mlx

app = typer.Typer(add_completion=False, help=__doc__)

HEAD_CHUNK = 256  # assistant positions per float32 slice of the vocabulary logits


def dpo_terms(pol_c: float, pol_r: float, ref_c: float, ref_r: float, beta: float) -> tuple[float, float, float]:
    """One pair's loss, its unscaled margin, and the gradient weight: d loss / d pol_r = coef,
    d loss / d pol_c = -coef, with coef = beta * sigmoid(-beta * margin)."""
    margin = (pol_c - ref_c) - (pol_r - ref_r)
    x = beta * margin
    loss = max(-x, 0.0) + math.log1p(math.exp(-abs(x)))  # log(1 + e^-x), without overflow
    return loss, margin, beta * math.exp(-x - loss)  # sigmoid(-x) = e^-x / (1 + e^-x)


def render(tok, turns: list[dict]) -> tuple[list[int], list[bool]]:
    """Token ids of a sitting and the loss mask: assistant tokens only. The chat template is
    applied per turn prefix (thinking mode off, as the samples were drawn) and prefix
    stability is asserted, as the CUDA path's renderer does."""
    ids, mask = [], []
    for i, turn in enumerate(turns):
        full = tok.apply_chat_template(turns[: i + 1], enable_thinking=False)
        if full[: len(ids)] != ids:
            raise RuntimeError("chat template is not prefix-stable")
        mask += [turn["role"] == "assistant"] * (len(full) - len(ids))
        ids = full
    return ids, mask


def train(pairs_path: Path, sft_adapter: Path, out: Path, model_name: str, batch: int, beta: float, lr: float,
          max_seq_length: int, seed: int, limit: int, memory_limit_gb: float) -> None:
    mlx_lm = require_mlx()
    import mlx.core as mx
    import mlx.nn as nn
    import mlx.optimizers as optim
    from mlx.utils import tree_flatten, tree_map
    from mlx_lm.tuner.trainer import grad_checkpoint

    check_memory = cap_memory(mx, memory_limit_gb)
    model, tok = mlx_lm.load(model_name, adapter_path=str(sft_adapter))
    model.freeze()
    model.apply_to_modules(lambda _, m: m.unfreeze(keys=["lora_a", "lora_b"]) if hasattr(m, "lora_a") else None)
    model.train()
    n_trainable = sum(v.size for _, v in tree_flatten(model.trainable_parameters()))
    if not n_trainable:
        raise RuntimeError("no trainable parameters: the stage-1 adapter's LoRA layers were not found")
    grad_checkpoint(model.layers[0])
    print(f"policy and reference: {sft_adapter}; {n_trainable / 1e6:.1f}M trainable parameters, "
          f"{mx.get_active_memory() / 2**30:.1f} GB resident", flush=True)

    data = []
    for p in read_jsonl(pairs_path)[: limit or None]:
        sides = [render(tok, p["chosen_turns"]), render(tok, p["rejected_turns"])]
        longest = max(len(ids) for ids, _ in sides)
        if longest > max_seq_length:
            raise RuntimeError(f"a sitting of {p['probe_id']}/{p['pressure']} is {longest} tokens, over --max-seq-length {max_seq_length}; raise the cap")
        data.append(sides)
    print(f"{len(data)} pairs from {pairs_path}, longest sitting {max(len(ids) for d in data for ids, _ in d)} tokens", flush=True)

    # The vocabulary is 262k wide: a float32 copy of a whole sitting's logits, kept for the
    # backward pass, is most of the memory. Checkpointing recomputes it a chunk at a time.
    def head_nll(logits, targets):
        return mx.checkpoint(lambda lg: nn.losses.cross_entropy(lg.astype(mx.float32), targets, reduction="sum"))(logits)

    def logp(ids, mask):
        """Sum of the log-probabilities of the sitting's assistant tokens, in float32 (the
        model computes in bf16, too coarse to sum a thousand terms in)."""
        at = mx.array([i for i in range(len(ids) - 1) if mask[i + 1]])
        logits, targets = model(mx.array([ids[:-1]]))[0], mx.array(ids)[at + 1]
        return -sum(head_nll(logits[at[s:s + HEAD_CHUNK]], targets[s:s + HEAD_CHUNK]) for s in range(0, len(at), HEAD_CHUNK))

    grad_logp = nn.value_and_grad(model, logp)

    def policy(side) -> tuple[float, dict]:
        value, grad = grad_logp(*side)
        mx.eval(value, grad)
        check_memory()
        return value.item(), grad

    # The frozen stage-1 model, before any update — through the same computation the policy
    # uses in training: in bf16 a plain forward pass differs from it by a few nats per sitting.
    refs = [(policy(c)[0], policy(r)[0]) for c, r in data]
    first, _ = policy(data[0][0])
    if not math.isclose(first, refs[0][0], rel_tol=1e-3, abs_tol=0.5):
        raise RuntimeError(f"policy/reference initial log-probability mismatch: {first} vs {refs[0][0]}")
    print(f"policy == reference at init: ok ({first:.3f} vs {refs[0][0]:.3f})", flush=True)

    adapter_dir, log_path = out / "adapter", out / "train_log.jsonl"
    adapter_dir.mkdir(parents=True)
    shutil.copy(sft_adapter / "adapter_config.json", adapter_dir / "adapter_config.json")
    (out / "config.json").write_text(json.dumps({
        "model": model_name, "pairs": str(pairs_path), "n_pairs": len(data), "batch": batch, "beta": beta, "lr": lr,
        "epochs": 1, "seed": seed, "reference": f"sft:{sft_adapter}", "init": f"sft:{sft_adapter}",
        "mlx_lm": mlx_lm.__version__, "masking": "assistant-tokens-only",
        "objective": "DPO; reference log-probabilities computed once from the stage-1 adapter before training",
    }, indent=2))

    opt = optim.AdamW(learning_rate=lr)
    order = list(range(len(data)))
    random.Random(seed).shuffle(order)
    acc, loss_sum, margin_sum, correct, n_acc, step, t0 = None, 0.0, 0.0, 0, 0, 0, time.perf_counter()
    for n, i in enumerate(order, 1):
        (chosen, rejected), (ref_c, ref_r) = data[i], refs[i]
        pol_c, grad_c = policy(chosen)
        pol_r, grad_r = policy(rejected)
        loss, margin, coef = dpo_terms(pol_c, pol_r, ref_c, ref_r, beta)
        grad = tree_map(lambda c, r: (coef / batch) * (r - c), grad_c, grad_r)
        acc = grad if acc is None else tree_map(lambda a, g: a + g, acc, grad)
        mx.eval(acc)
        loss_sum, margin_sum, correct, n_acc = loss_sum + loss, margin_sum + margin, correct + (margin > 0), n_acc + 1
        if n_acc == batch or n == len(order):
            opt.update(model, acc)
            mx.eval(model.parameters(), opt.state)
            step += 1
            rec = {"step": step, "seen": n, "loss": loss_sum / n_acc, "pref_acc": correct / n_acc,
                   "margin": margin_sum / n_acc, "peak_gb": round(mx.get_peak_memory() / 2**30, 1),
                   "elapsed_s": round(time.perf_counter() - t0)}
            print(rec, flush=True)
            with open(log_path, "a") as fh:
                fh.write(json.dumps(rec) + "\n")
            mx.save_safetensors(str(adapter_dir / "saving.safetensors"), dict(tree_flatten(model.trainable_parameters())))
            os.replace(adapter_dir / "saving.safetensors", adapter_dir / "adapters.safetensors")
            acc, loss_sum, margin_sum, correct, n_acc = None, 0.0, 0.0, 0, 0
    print(f"done: {step} steps over {len(data)} pairs; adapter at {adapter_dir}")


@app.command()
def main(
    pairs: Path = typer.Option(..., help="Stage-2 pairs (output of `pairs`)."),
    sft_adapter: Path = typer.Option(..., "--sft-adapter", help="The stage-1 adapter directory (output of `mlx.sft`): initial policy and frozen reference."),
    run: str = typer.Option("new-run", help="Run directory name under data/runs/ for the outputs."),
    out: Path | None = typer.Option(None, help="Output directory (default: <run dir>/mlx-sft-dpo)."),
    model: str = typer.Option(DEFAULT_MODEL, help="An MLX conversion of a Gemma-family model (the adapter must belong to it)."),
    batch: int = typer.Option(8, help="Pairs per optimizer step, by gradient accumulation."),
    beta: float = typer.Option(0.1, help="DPO beta (setting of record 0.1)."),
    lr: float = typer.Option(1e-5, help="Learning rate (setting of record 1e-5; AdamW)."),
    max_seq_length: int = typer.Option(4096, help="Longest sitting in tokens; a longer one is an error, never truncated. Raise it together with --memory-limit-gb."),
    seed: int = typer.Option(3446, help="Shuffle seed."),
    limit: int = typer.Option(0, help="Train on the first N pairs only (smoke test)."),
    memory_limit_gb: float = typer.Option(24.0, help="Memory ceiling in GB, checked after every pass: the job stops once its peak has passed it."),
    dry_run: bool = typer.Option(False, "--dry-run", help="Print the preflight summary and stop before anything loads."),
) -> None:
    n = len(read_jsonl(pairs))
    require_adapter(sft_adapter)
    out = paths.output_path(out or paths.run_dir(run) / "mlx-sft-dpo")
    if (out / "adapter").exists():
        raise typer.BadParameter(f"{out} already holds an adapter; choose another --run or --out (a run never overwrites)")
    n_used = min(n, limit) if limit else n
    if preflight(f"MLX stage-2 DPO of {model} from {sft_adapter}",
                 [f"pairs {pairs}: {n}" + (f", using the first {limit}" if limit else ""),
                  f"beta {beta:g}, lr {lr:g}, 1 pass, batch {batch} (~{-(-n_used // batch)} steps), seq cap {max_seq_length}, seed {seed}",
                  "policy starts as the stage-1 adapter; the same adapter, frozen, is the reference",
                  precision_line(model), ceiling_line(memory_limit_gb), f"outputs -> {out}"],
                 dry_run):
        return
    train(pairs, sft_adapter, out, model, batch, beta, lr, max_seq_length, seed, limit, memory_limit_gb)


if __name__ == "__main__":
    app()
