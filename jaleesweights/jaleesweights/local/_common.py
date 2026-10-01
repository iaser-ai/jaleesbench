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


def torch_dtype(name: str):
    torch = require("torch")
    try:
        return {"bf16": torch.bfloat16, "bfloat16": torch.bfloat16, "fp16": torch.float16,
                "float16": torch.float16, "fp32": torch.float32, "float32": torch.float32}[name]
    except KeyError:
        raise typer.BadParameter(f"unknown dtype {name!r}; use bf16, fp16 or fp32") from None


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
