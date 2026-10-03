"""Shared pieces of the MLX path: the lazy `mlx_lm` import with a plain message when the
`mlx` group is not installed, the memory estimate and the preflight. Nothing here imports
`mlx` at module import time, so `--help` and `--dry-run` work on any machine.
"""

import importlib
import json
import os
from pathlib import Path

import typer

DEFAULT_MODEL = "mlx-community/gemma-4-E4B-it-4bit"  # TUTORIAL.md's model
PAPER_MODEL = "mlx-community/gemma-4-31B-it-qat-4bit"  # the paper's model, 4-bit
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


def cap_memory(mx, gb: float):
    """Hold an MLX job under `gb` of memory. MLX's own limit is a guideline — past it MLX
    reclaims its buffer cache, but it still allocates into swap — and its cache of freed
    buffers may by default grow as large as that limit, which on its own can push a Mac into
    swap when every sitting has a different length. So: set the limit, cap the cache at an
    eighth of it, and return a check to call after each evaluation, which stops the job if
    the peak has passed the ceiling and otherwise empties the cache. The check runs after a
    pass, so one pass can overshoot before it is caught; on a shared machine, also run long
    jobs under something that watches swap."""
    limit = int(gb * 2**30)
    mx.set_memory_limit(limit)
    mx.set_cache_limit(limit // 8)

    def check() -> None:
        peak = mx.get_peak_memory()
        if peak > limit:
            raise RuntimeError(f"peak memory {peak / 2**30:.1f} GB passed the {gb:g} GB ceiling (--memory-limit-gb); stopping")
        mx.clear_cache()
    return check


def ceiling_line(gb: float) -> str:
    return f"memory ceiling {gb:g} GB: MLX's limit is set, and the peak is checked after every pass (one pass can overshoot)"


def require_adapter(adapter: Path) -> None:
    """An `mlx_lm` adapter directory holds the weights and the config `mlx_lm.load` reads."""
    missing = [n for n in ("adapters.safetensors", "adapter_config.json") if not (adapter / n).exists()]
    if missing:
        raise typer.BadParameter(f"{adapter} is not an mlx_lm adapter directory (no {' or '.join(missing)})")


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
