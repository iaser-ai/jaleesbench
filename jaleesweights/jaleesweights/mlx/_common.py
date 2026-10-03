"""Shared pieces of the MLX path: the lazy `mlx_lm` import with a plain message when the
`mlx` group is not installed, the memory estimate and the preflight. Nothing here imports
`mlx` at module import time, so `--help` and `--dry-run` work on any machine.
"""

import importlib
import json
import os
from pathlib import Path

import typer

DEFAULT_MODEL = "mlx-community/gemma-4-E4B-it-4bit"  # TUTORIAL.md's model; see its "Which model" section
PAPER_MODEL = "mlx-community/gemma-4-31B-it-qat-4bit"  # the paper's model, 4-bit; TUTORIAL.md gives its measured figures
MLX_GROUP_HINT = "install the MLX stack on an Apple Silicon Mac with `uv sync --group mlx`"
PRECISIONS = ("4bit", "5bit", "6bit", "8bit", "bf16")


def require_mlx():
    """Import `mlx_lm`, or stop with a message naming the dependency group."""
    try:
        return importlib.import_module("mlx_lm")
    except ImportError as e:
        raise SystemExit(f"missing MLX dependency: mlx_lm ({e}); {MLX_GROUP_HINT}") from None


def memory_summary() -> str:
    """The machine's unified memory, for the preflight ('unknown' off macOS)."""
    try:
        return f"{os.sysconf('SC_PAGE_SIZE') * os.sysconf('SC_PHYS_PAGES') / 2**30:.0f} GB unified"
    except (ValueError, OSError, AttributeError):
        return "unknown"


def weights_on_disk(model: str) -> float | None:
    """Size in GB of the model's files, from a local directory or the Hugging Face cache;
    None when the model has not been downloaded yet (the first run fetches it)."""
    from huggingface_hub import snapshot_download  # in the default install, through transformers
    from huggingface_hub.errors import LocalEntryNotFoundError
    path = Path(model)
    if not path.is_dir():
        try:
            path = Path(snapshot_download(model, local_files_only=True))
        except LocalEntryNotFoundError:
            return None
    return sum(f.stat().st_size for f in path.rglob("*") if f.is_file()) / 2**30


def precision_line(model: str) -> str:
    """The precision read off the model id (`...-4bit`) and what the weights take on disk,
    which is close to what they take in memory once loaded (measured: a little less)."""
    bits = next((b for b in PRECISIONS if b in model.lower()), "unknown from the model id")
    size = weights_on_disk(model)
    where = (f"weights on disk {size:.1f} GB (resident at load is a little less; training adds activations)"
             if size is not None else "not downloaded yet: the first run fetches the weights from Hugging Face")
    return f"precision: {bits} as converted; {where}"


def preflight(what: str, lines: list[str], dry_run: bool) -> bool:
    """Print the summary and the memory seen; return True to stop."""
    typer.echo(f"preflight: {what}")
    for l in lines:
        typer.echo(f"  {l}")
    typer.echo(f"  memory: {memory_summary()}")
    if dry_run:
        typer.echo("dry run: stopping before anything loads")
    return dry_run


def read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        raise typer.BadParameter(f"{path} does not exist")
    rows = [json.loads(l) for l in path.read_text().splitlines() if l.strip()]
    if not rows:
        raise typer.BadParameter(f"{path} is empty")
    return rows
