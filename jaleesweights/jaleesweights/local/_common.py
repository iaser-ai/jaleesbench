"""Shared pieces of the local demonstration: lazy GPU imports with a plain message when the
GPU group is not installed, the conversation renderer and loss mask (the same code the
Modal training functions run), and the preflight.

Nothing here imports torch, transformers, peft or vLLM at module import time, so every
demonstration command can print its usage and its preflight on a machine without a GPU.
"""

import importlib
import json
from pathlib import Path

import typer

DEFAULT_MODEL = "google/gemma-4-12B-it"   # the owner's default for the demonstration (spec question 9)
MAX_TOKENS_PER_CONVERSATION = 16384       # the recipe's hard cap; longer conversations are refused
GPU_GROUP_HINT = "install the GPU stack on a Linux + NVIDIA machine with `uv sync --group gpu`"

DTYPES = {"bf16": "bf16", "bfloat16": "bf16", "fp16": "fp16", "float16": "fp16", "fp32": "fp32", "float32": "fp32"}
WEIGHT_BYTES = {"nf4": 0.5, "bf16": 2.0, "fp16": 2.0, "fp32": 4.0}  # per parameter, weights alone
# Nominal parameter counts (billions) of the models the README's hardware table lists.
NOMINAL_B_PARAMS = {"google/gemma-4-12B-it": 12, "google/gemma-4-31B-it": 31, "google/gemma-4-E4B-it": 4}
# Measured training peaks of the paper's 31B runs, as a multiple of the weights alone: the
# bf16 stage-1 run of record (66.0 GB on a B200 over 62 GB of weights) and the archived 4-bit
# chain (33 GB on an H200 over 15.5 GB of nf4 weights; the unquantized embeddings and the
# fp32 casts of prepare_model_for_kbit_training are why the multiple is larger).
TRAIN_PEAK_MULTIPLE = {"bf16": 66.0 / 62, "nf4": 33.0 / 15.5}


def require(module: str):
    """Import a GPU-stack module, or stop with a message naming it."""
    try:
        return importlib.import_module(module)
    except ImportError as e:
        raise SystemExit(f"missing GPU dependency: {module} ({e}); {GPU_GROUP_HINT}") from None


def gpu_summary() -> str:
    """What the machine offers, for the preflight. 'none' when torch or CUDA is absent."""
    try:
        torch = importlib.import_module("torch")
    except ImportError:
        return "none (torch not installed)"
    if not torch.cuda.is_available():
        return "none"
    parts = []
    for i in range(torch.cuda.device_count()):
        p = torch.cuda.get_device_properties(i)
        parts.append(f"{p.name} {p.total_memory / 2**30:.0f} GB")
    return ", ".join(parts)


def count_rows(path: Path) -> int:
    if not path.exists():
        raise typer.BadParameter(f"{path} does not exist")
    n = sum(1 for l in path.read_text().splitlines() if l.strip())
    if n == 0:
        raise typer.BadParameter(f"{path} is empty")
    return n


def canonical_dtype(name: str) -> str:
    try:
        return DTYPES[name]
    except KeyError:
        raise typer.BadParameter(f"unknown dtype {name!r}; use bf16, fp16 or fp32") from None


def torch_dtype(name: str):
    torch = require("torch")
    return {"bf16": torch.bfloat16, "fp16": torch.float16, "fp32": torch.float32}[canonical_dtype(name)]


def bnb_4bit_config(compute_dtype_name: str):
    """The archived 4-bit chain's quantization: nf4 with bf16 compute (modal_gemma_sft.py).
    Stops naming bitsandbytes when it is absent — never a silent fall back to bf16."""
    require("bitsandbytes")
    torch = require("torch")
    BitsAndBytesConfig = require("transformers").BitsAndBytesConfig
    return BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_quant_type="nf4",
                              bnb_4bit_compute_dtype=torch_dtype(compute_dtype_name))


def precision_line(model_name: str, dtype_name: str, load_in_4bit: bool, training: bool) -> str:
    """The preflight's precision line with the derived memory estimate: weights alone from
    the bytes per parameter, the training peak scaled from the 31B runs' measured peaks."""
    dtype = canonical_dtype(dtype_name)
    kind = "nf4" if load_in_4bit else dtype
    how = "QLoRA" if training else "vLLM bitsandbytes, in flight"
    what = (f"nf4 4-bit base ({how}), {dtype} compute" if load_in_4bit else f"{dtype}, no quantization")
    b_params = NOMINAL_B_PARAMS.get(model_name)
    if b_params is None:
        return f"precision: {what}; derived: no estimate (unknown parameter count for {model_name})"
    weights = b_params * WEIGHT_BYTES[kind]
    est = f"weights ~{weights:.0f} GB"
    if training and kind in TRAIN_PEAK_MULTIPLE:
        est += f", training peak ~{weights * TRAIN_PEAK_MULTIPLE[kind]:.0f} GB (scaled from the 31B {kind} run)"
    elif not training:
        est += " plus the key-value cache"
    return f"precision: {what}; derived: {est}"


def preflight(what: str, lines: list[str], dry_run: bool) -> bool:
    """Print the summary (inputs, settings, the GPU seen); return True to stop."""
    typer.echo(f"preflight: {what}")
    for l in lines:
        typer.echo(f"  {l}")
    typer.echo(f"  GPU: {gpu_summary()}")
    if dry_run:
        typer.echo("dry run: stopping before anything loads")
    return dry_run


def make_render(tok):
    """The renderer the Modal training functions use: chat template per turn prefix,
    prefix-stability asserted, loss mask = assistant tokens only."""
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
    return render


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(l) for l in path.read_text().splitlines() if l.strip()]


def check_resume_dir(resume_from: Path | None, adapter_subdir: str) -> None:
    """A --resume-from directory must hold a complete checkpoint: the adapter and the
    training state. Anything less stops here — never a silent fresh (paid) run."""
    if resume_from is None:
        return
    missing = [p for p in (resume_from / adapter_subdir, resume_from / "train_state.pt") if not p.exists()]
    if missing:
        raise typer.BadParameter(
            f"--resume-from {resume_from} is not a complete checkpoint; missing: "
            + ", ".join(str(m) for m in missing)
            + ". A finished run deletes train_state.pt on completion; a run that never checkpointed has nothing to resume.")
