"""Shared settings of the five Modal drivers: the account-specific names, the model, and the
three container images exactly as the runs of record defined them.

A new team runs these in its own Modal account. Two names must exist there before the
first run (see the README):

  JW_MODAL_VOLUME     a Modal volume holding inputs under /pairs and runs under /runs
                      (default "gemma-dpo", the name the runs of record used)
  JW_MODAL_HF_SECRET  a Modal secret providing HF_TOKEN (default "huggingface"). The Gemma
                      weights were ungated when the runs were made, so the token may be
                      empty, but the secret must exist because the functions reference it.
"""

import inspect
import os

import modal
import typer

MODEL = "google/gemma-4-31B-it"
VOLUME = os.environ.get("JW_MODAL_VOLUME", "gemma-dpo")
HF_SECRET = os.environ.get("JW_MODAL_HF_SECRET", "huggingface")


def volume() -> modal.Volume:
    return modal.Volume.from_name(VOLUME)


def hf_secret() -> modal.Secret:
    return modal.Secret.from_name(HF_SECRET)


# Training image (stage 1 and stage 2): Blackwell (B200/sm_100) needs CUDA 12.8+ and a recent
# torch: CUDA 12.8 devel base + torch cu128. No bitsandbytes (bf16 LoRA).
TRAIN_IMAGE = (
    modal.Image.from_registry("nvidia/cuda:12.8.1-devel-ubuntu24.04", add_python="3.12")
    .pip_install("torch>=2.7.0", index_url="https://download.pytorch.org/whl/cu128")
    .pip_install("transformers>=4.53", "peft>=0.15", "accelerate>=1.3", "hf_transfer")
    .env({"HF_HUB_ENABLE_HF_TRANSFER": "1", "HF_HOME": "/vol/hf-cache",
          "PYTORCH_CUDA_ALLOC_CONF": "expandable_segments:True"})
)

# Serving image (held-out collection and sampling): vLLM compiles gemma-4 router-GEMM kernels
# at startup and needs nvcc, so the full CUDA toolkit is required.
SERVE_IMAGE = (
    modal.Image.from_registry("nvidia/cuda:12.8.1-devel-ubuntu24.04", add_python="3.12")
    .pip_install("vllm>=0.10", "hf_transfer")
    .env({"HF_HUB_ENABLE_HF_TRANSFER": "1", "HF_HOME": "/vol/hf-cache",
          "VLLM_WORKER_MULTIPROC_METHOD": "spawn"})
)

# Capability-panel image: the serving stack plus lm-evaluation-harness.
CAPABILITY_IMAGE = (
    modal.Image.from_registry("nvidia/cuda:12.8.1-devel-ubuntu24.04", add_python="3.12")
    .pip_install("vllm>=0.10", "lm_eval[vllm,ifeval]>=0.4.8", "hf_transfer")
    .env({"HF_HUB_ENABLE_HF_TRANSFER": "1", "HF_HOME": "/vol/hf-cache",
          "VLLM_WORKER_MULTIPROC_METHOD": "spawn",
          "HF_ALLOW_CODE_EVAL": "1"})
)


def check_local(volume_path: str, local: str, expected_rows: int | None = None) -> str:
    """Validate the local file a volume path is uploaded from: it must exist, and when the
    step has a fixed size (the 420-cell inputs) hold exactly that many rows. Returns a note."""
    p = os.path.expanduser(local)
    if not os.path.isfile(p):
        raise SystemExit(f"preflight failed: local source for {volume_path} does not exist: {local}")
    if volume_path.endswith((".jsonl", ".txt")):
        with open(p) as fh:
            rows = sum(1 for l in fh if l.strip())
        if rows == 0:
            raise SystemExit(f"preflight failed: {local} is empty")
        if expected_rows is not None and rows != expected_rows:
            raise SystemExit(f"preflight failed: {local} has {rows} rows; {volume_path} must have {expected_rows}")
        return f"local {local}: {rows} rows ok"
    return f"local {local}: present"


def preflight(what: str, gpu: str, reads: list[str], writes: list[str], dry_run: bool,
              local: dict[str, tuple[str, int | None]] | None = None,
              required_local: list[str] | None = None) -> bool:
    """Print what a driver is about to rent and touch; return True when it should stop.
    `local` maps a volume path to (local source file, expected row count or None): those
    files are checked before anything is launched. A real launch (not --dry-run) refuses to
    proceed unless every path in `required_local` has a checked local source — the inputs a
    driver reads from the volume are the files the team uploaded, and the preflight must have
    seen them. The volume's own contents cannot be seen without an account."""
    print(f"preflight: {what}")
    for vp, (src, n) in (local or {}).items():
        print("  " + check_local(vp, src, n))
    unchecked = [vp for vp in (required_local or []) if vp not in (local or {})]
    if unchecked and not dry_run:
        raise SystemExit("preflight failed: give the local source of "
                         + ", ".join(unchecked)
                         + " (the --local-... option) so it can be checked before launch, or use --dry-run")
    print(f"  Modal volume {VOLUME!r}, secret {HF_SECRET!r}, GPU {gpu}; billed to your Modal account")
    for p in reads:
        if p.startswith("/pairs/"):
            src = (local or {}).get(p, (None,))[0]
            hint = (f"(upload: modal volume put {VOLUME} {src or '<local file>'} {p})"
                    + ("" if src else "   [local source not given: not checked]"))
        else:
            hint = "(written to the volume by an earlier driver run)"
        print(f"  reads  /vol{p}   {hint}")
    for p in writes:
        print(f"  writes /vol{p}   (download: modal volume get {VOLUME} {p} <local dir>)")
    print("  (the volume's contents are not checked here; a missing input fails inside the container)")
    if dry_run:
        print("dry run: stopping before launch")
    return dry_run


def preflight_cli(entrypoint) -> None:
    """Run a driver's local entrypoint in preflight-only mode, as a plain Python command that
    needs no Modal account:  uv run python -m jaleesweights.modal.<driver> [options]

    `modal run` itself needs a token before it will call the entrypoint, so the free check
    goes through here; `modal run ... --dry-run` does the same thing once an account exists."""
    raw = entrypoint.info.raw_f
    sig = inspect.signature(raw)

    def run(**kwargs):
        kwargs["dry_run"] = True
        raw(**kwargs)

    # Every parameter becomes an option, as `modal run` presents them.
    params = [p.replace(default=typer.Option(... if p.default is inspect.Parameter.empty else p.default))
              for p in sig.parameters.values() if p.name != "dry_run"]
    run.__signature__ = sig.replace(parameters=params)
    run.__doc__ = ("Preflight only: prints the volume, secret, GPU and volume paths this driver would use "
                   "and launches nothing. Launch for real with `uv run modal run -m jaleesweights.modal.<driver>`.")
    typer.run(run)
