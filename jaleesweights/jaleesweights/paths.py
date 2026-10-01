"""Where things are, settled by the clone's layout — never by where a package
happens to be installed.

Every location can be overridden by an environment variable, which is how a
team keeps the reference data or the main run somewhere else:

  JW_BENCH_RESULTS  the benchmark main run (collect.jsonl, judgments.jsonl, ...)
  JW_REFERENCE      the downloaded reference data (what the original runs produced)
  JW_RUNS           parent directory of new-run directories
"""

import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
PROJECT = REPO_ROOT / "jaleesweights"
if not (REPO_ROOT / "jaleesbench" / "pyproject.toml").exists():
    # Only true when this package runs from the clone (the editable install).
    # A copy installed elsewhere would otherwise point every path at nothing.
    raise RuntimeError(
        f"jaleesweights must run from its clone; {REPO_ROOT} is not the repository root "
        "(run `uv sync` inside jaleesweights/ and launch with `uv run` from there).")


def _dir(env: str, default: Path) -> Path:
    override = os.environ.get(env)
    return Path(override).expanduser().resolve() if override else default


BENCH_RESULTS = _dir("JW_BENCH_RESULTS", REPO_ROOT / "jaleesbench" / "results")
REFERENCE = _dir("JW_REFERENCE", PROJECT / "data" / "reference")
RUNS = _dir("JW_RUNS", PROJECT / "data" / "runs")

SPLIT = PROJECT / "split_70_70.json"
GUIDED_PREFIX = PROJECT / "guided_prefix.txt"
CHECKSUMS = PROJECT / "release" / "checksums.sha256"

# Main-run files the recipe reads.
MAIN_RUN_FILES = ("collect.jsonl", "judgments.jsonl", "citations_llm.jsonl")


def main_run_file(name: str) -> Path:
    """A main-run file, or a clear error naming what is missing and how to get it."""
    if name not in MAIN_RUN_FILES:
        raise ValueError(f"not a main-run file: {name}")
    p = BENCH_RESULTS / name
    if not p.exists():
        raise FileNotFoundError(
            f"benchmark main run not installed: {p} is missing. "
            f"Run `uv run python -m jaleesweights.fetch_data` (see README).")
    return p


def main_run_files() -> dict[str, Path]:
    """All three main-run files, checked at once — the preflight every step that
    reads the main run runs first."""
    return {name: main_run_file(name) for name in MAIN_RUN_FILES}


def reference_file(name: str) -> Path:
    """A reference-data file, or a clear error."""
    p = REFERENCE / name
    if not p.exists():
        raise FileNotFoundError(
            f"reference data not installed: {p} is missing. "
            f"Run `uv run python -m jaleesweights.fetch_data` (see README).")
    return p


def run_dir(name: str) -> Path:
    """The directory a new run writes to (created on first use). Reference data
    is never written; everything a run produces lands here."""
    d = RUNS / name
    d.mkdir(parents=True, exist_ok=True)
    return d
