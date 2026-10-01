"""Install the data release: the JaleesWeights reference data and the JaleesBench main run.

    uv run python -m jaleesweights.fetch_data                 # download the published release
    uv run python -m jaleesweights.fetch_data --from-dir DIR  # install from archives on disk

Each archive is checked against `release/checksums.sha256` before it is extracted, so a
corrupt or tampered download stops here with the archive named. The reference data lands
in `jaleesweights/data/reference/`, the main run in `jaleesbench/results/` (both ignored by
git). Existing files are never overwritten unless `--force` is given.
"""

import hashlib
import shutil
import sys
import tarfile
import urllib.error
import urllib.request
from pathlib import Path

import typer

from . import paths

REPO = "iaser-ai/jaleesbench"
TAG = "jaleesweights-data-v1"
ARCHIVES = {
    # asset name -> (destination, what it holds)
    "jaleesweights-data.tar.gz": ("reference", "reference data of the recipe of record and the archived arms"),
    "jaleesbench-main-run.tar.gz": ("main-run", "the benchmark main run the training-set builders read"),
}

app = typer.Typer(add_completion=False, help=__doc__)


def expected_checksums(path: Path | None = None) -> dict[str, str]:
    path = path or paths.CHECKSUMS
    out = {}
    for line in path.read_text().splitlines():
        digest, _, name = line.strip().partition("  ")
        out[name] = digest
    missing = set(ARCHIVES) - set(out)
    if missing:
        raise RuntimeError(f"{path} lacks checksums for: {', '.join(sorted(missing))}")
    return out


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def release_url(asset: str, tag: str = TAG) -> str:
    return f"https://github.com/{REPO}/releases/download/{tag}/{asset}"


def download(asset: str, dest: Path, tag: str = TAG, opener=urllib.request.urlopen) -> Path:
    """Fetch one release asset to `dest`. A 404 means the release (or asset) is not
    published yet, and says so; any other HTTP error is reported as it is."""
    url = release_url(asset, tag)
    dest.parent.mkdir(parents=True, exist_ok=True)
    try:
        with opener(url) as resp, open(dest, "wb") as fh:
            shutil.copyfileobj(resp, fh)
    except urllib.error.HTTPError as e:
        if e.code == 404:
            raise RuntimeError(
                f"the data release {tag} has not been published yet ({url} returned 404). "
                f"Until it is, install from archives on disk with --from-dir.") from None
        raise
    return dest


def verify(archive: Path, expected: str) -> None:
    actual = sha256(archive)
    if actual != expected:
        raise RuntimeError(
            f"checksum mismatch for {archive.name}: expected {expected}, got {actual}. "
            f"The archive is corrupt or is not the released one; nothing was extracted.")


def destination(kind: str) -> Path:
    return paths.REFERENCE if kind == "reference" else paths.BENCH_RESULTS


def extract(archive: Path, dest: Path, force: bool = False) -> list[str]:
    """Extract into `dest`, refusing to overwrite anything already there unless `force`.
    Returns the member names extracted."""
    with tarfile.open(archive, "r:gz") as tar:
        members = [m for m in tar.getmembers() if m.isfile()]
        names = [m.name for m in members]
        clashes = [n for n in names if (dest / n).exists()]
        if clashes and not force:
            raise RuntimeError(
                f"{dest} already has {len(clashes)} of the files in {archive.name} "
                f"(for example {clashes[0]}); pass --force to overwrite.")
        dest.mkdir(parents=True, exist_ok=True)
        tar.extractall(dest, members=members, filter="data")
    return names


@app.command()
def main(
    from_dir: Path | None = typer.Option(None, "--from-dir", help="Directory holding the archives, instead of downloading."),
    tag: str = typer.Option(TAG, help="Release tag to download from."),
    force: bool = typer.Option(False, "--force", help="Overwrite files already present at the destinations."),
    only: str | None = typer.Option(None, help="Install just one: 'reference' or 'main-run'."),
) -> None:
    sums = expected_checksums()
    for asset, (kind, what) in ARCHIVES.items():
        if only and kind != only:
            continue
        if from_dir is not None:
            archive = from_dir / asset
            if not archive.exists():
                raise typer.BadParameter(f"{archive} does not exist")
        else:
            archive = download(asset, paths.PROJECT / "data" / "downloads" / asset, tag)
        verify(archive, sums[asset])
        dest = destination(kind)
        names = extract(archive, dest, force=force)
        typer.echo(f"{asset}: checksum ok; {len(names)} files -> {dest}  ({what})")


if __name__ == "__main__":
    app()
