"""The Modal drivers, without a Modal account: settings resolve from the environment, the
preflight prints what would be rented and launches nothing."""

import importlib
import subprocess
import sys
from pathlib import Path

import pytest

DRIVERS = ["gemma_sft_bf16", "gemma_dpo2_bf16", "gemma_eval", "gemma_sample", "gemma_capability"]
PROJECT = Path(__file__).resolve().parents[1]
NO_ACCOUNT = {"HOME": "/tmp/jw-no-modal-account", "PATH": "/usr/bin:/bin"}


def test_settings_resolve_from_environment(monkeypatch):
    monkeypatch.setenv("JW_MODAL_VOLUME", "team-vol")
    monkeypatch.setenv("JW_MODAL_HF_SECRET", "team-hf")
    from jaleesweights.modal import _config
    cfg = importlib.reload(_config)
    assert cfg.VOLUME == "team-vol" and cfg.HF_SECRET == "team-hf" and cfg.MODEL == "google/gemma-4-31B-it"
    monkeypatch.delenv("JW_MODAL_VOLUME")
    monkeypatch.delenv("JW_MODAL_HF_SECRET")
    cfg = importlib.reload(_config)
    assert cfg.VOLUME == "gemma-dpo" and cfg.HF_SECRET == "huggingface"
    # three distinct images, as the runs of record had them
    assert cfg.TRAIN_IMAGE is not cfg.SERVE_IMAGE is not cfg.CAPABILITY_IMAGE


@pytest.mark.parametrize("driver", DRIVERS)
def test_driver_imports_and_prints_usage_without_an_account(driver):
    out = subprocess.run([sys.executable, "-m", f"jaleesweights.modal.{driver}", "--help"],
                         cwd=PROJECT, capture_output=True, text=True, env={**NO_ACCOUNT, "PYTHONPATH": str(PROJECT)})
    assert out.returncode == 0, out.stderr
    assert "Preflight only" in out.stdout


@pytest.mark.parametrize("driver,args,expect", [
    ("gemma_sft_bf16", ["--data", "/pairs/sft_guided.jsonl", "--run-name", "r"], ["GPU B200", "/vol/pairs/sft_guided.jsonl", "/vol/runs/r/adapter"]),
    ("gemma_dpo2_bf16", ["--pairs", "/pairs/p.jsonl", "--run-name", "r2", "--sft-run", "s1"], ["GPU B200", "/vol/runs/s1/adapter", "/vol/runs/r2/adapter"]),
    ("gemma_eval", ["--run-name", "base", "--subject", "gemma-base-vllm"], ["GPU H200", "base model, no adapter", "/vol/pairs/eval_inputs.jsonl"]),
    ("gemma_sample", ["--adapter-run", "s1", "--out-run", "o", "--lane-prefix", "x-s"], ["GPU H200", "lanes x-s0..3", "/vol/runs/o/collect_train_samples.jsonl"]),
    ("gemma_capability", ["--chat"], ["chat mode", "/vol/runs/capability/sft-dpo-bf16-chat"]),
])
def test_preflight_prints_and_stops(driver, args, expect):
    out = subprocess.run([sys.executable, "-m", f"jaleesweights.modal.{driver}", *args],
                         cwd=PROJECT, capture_output=True, text=True,
                         env={**NO_ACCOUNT, "PYTHONPATH": str(PROJECT), "JW_MODAL_VOLUME": "team-vol"})
    assert out.returncode == 0, out.stderr
    for e in expect + ["Modal volume 'team-vol'", "dry run: stopping before launch"]:
        assert e in out.stdout, (e, out.stdout)


def test_capability_rejects_unknown_checkpoint():
    out = subprocess.run([sys.executable, "-m", "jaleesweights.modal.gemma_capability", "--only", "nf4"],
                         cwd=PROJECT, capture_output=True, text=True, env={**NO_ACCOUNT, "PYTHONPATH": str(PROJECT)})
    assert out.returncode != 0 and "unknown checkpoint" in out.stderr


def test_preflight_validates_local_sources(tmp_path):
    good = tmp_path / "eval_inputs.jsonl"
    good.write_text("{}\n" * 420)
    short = tmp_path / "short.jsonl"
    short.write_text("{}\n" * 7)
    base = [sys.executable, "-m", "jaleesweights.modal.gemma_eval", "--run-name", "base"]
    env = {**NO_ACCOUNT, "PYTHONPATH": str(PROJECT)}
    ok = subprocess.run(base + ["--local-inputs", str(good)], cwd=PROJECT, capture_output=True, text=True, env=env)
    assert ok.returncode == 0 and "420 rows ok" in ok.stdout and f"modal volume put gemma-dpo {good}" in ok.stdout
    bad = subprocess.run(base + ["--local-inputs", str(short)], cwd=PROJECT, capture_output=True, text=True, env=env)
    assert bad.returncode != 0 and "has 7 rows" in bad.stderr and "dry run" not in bad.stdout
    missing = subprocess.run(base + ["--local-inputs", str(tmp_path / "nope.jsonl")], cwd=PROJECT, capture_output=True, text=True, env=env)
    assert missing.returncode != 0 and "does not exist" in missing.stderr
    unchecked = subprocess.run(base, cwd=PROJECT, capture_output=True, text=True, env=env)
    assert unchecked.returncode == 0 and "local source not given: not checked" in unchecked.stdout


def test_sample_defaults_to_the_stage_1_model():
    out = subprocess.run([sys.executable, "-m", "jaleesweights.modal.gemma_sample"],
                         cwd=PROJECT, capture_output=True, text=True, env={**NO_ACCOUNT, "PYTHONPATH": str(PROJECT)})
    assert out.returncode == 0
    assert "from gemma-sft-guided-bf16" in out.stdout and "lanes gemma-sftbf16-s0..3" in out.stdout
    assert "/vol/runs/gemma-sftbf16-sample/collect_train_samples.jsonl" in out.stdout


@pytest.mark.parametrize("driver,args,opt", [
    ("gemma_sft_bf16", ["--data", "/pairs/sft_guided.jsonl", "--run-name", "r"], "--local-data"),
    ("gemma_dpo2_bf16", ["--pairs", "/pairs/p.jsonl", "--run-name", "r"], "--local-pairs"),
    ("gemma_sample", [], "--local-inputs"),
    ("gemma_eval", ["--run-name", "base"], "--local-inputs"),
])
def test_real_launch_needs_a_checked_local_source(tmp_path, driver, args, opt):
    """Without --dry-run (the plain-module entry always sets it), the entrypoint refuses to
    launch when the input's local source was not given; empty files are refused too."""
    from jaleesweights.modal import _config
    import importlib
    mod = importlib.import_module(f"jaleesweights.modal.{driver}")
    raw = mod.main.info.raw_f
    import inspect
    kwargs = {}
    it = iter(args)
    for a in it:
        kwargs[a.lstrip("-").replace("-", "_")] = next(it)
    with pytest.raises(SystemExit, match="give the local source"):
        raw(**kwargs, dry_run=False)
    empty = tmp_path / "empty.jsonl"
    empty.write_text("")
    with pytest.raises(SystemExit, match="is empty"):
        raw(**kwargs, **{opt.lstrip("-").replace("-", "_"): str(empty)}, dry_run=False)


@pytest.mark.parametrize("driver,args,opt", [
    ("gemma_sft_bf16", ["--data", "/pairs/sft_guided.jsonl", "--run-name", "r"], "--local-data"),
    ("gemma_dpo2_bf16", ["--pairs", "/pairs/p.jsonl", "--run-name", "r"], "--local-pairs"),
])
def test_trainers_report_local_source_row_counts(tmp_path, driver, args, opt):
    f = tmp_path / "set.jsonl"
    f.write_text("{}\n" * 12)
    out = subprocess.run([sys.executable, "-m", f"jaleesweights.modal.{driver}", *args, opt, str(f)],
                         cwd=PROJECT, capture_output=True, text=True, env={**NO_ACCOUNT, "PYTHONPATH": str(PROJECT)})
    assert out.returncode == 0, out.stderr
    assert f"local {f}: 12 rows ok" in out.stdout and f"modal volume put gemma-dpo {f}" in out.stdout


def test_check_resume_refuses_partial_checkpoints(tmp_path):
    from jaleesweights.modal._config import check_resume
    assert check_resume(None, ("adapter", "train_state.pt")) is False
    assert check_resume("", ("adapter", "train_state.pt")) is False
    with pytest.raises(RuntimeError, match="not a complete checkpoint"):
        check_resume(tmp_path / "nowhere", ("adapter", "train_state.pt"))
    (tmp_path / "adapter").mkdir()
    with pytest.raises(RuntimeError, match="train_state.pt"):
        check_resume(tmp_path, ("adapter", "train_state.pt"))
    (tmp_path / "train_state.pt").write_bytes(b"")
    assert check_resume(tmp_path, ("adapter", "train_state.pt")) is True
    with pytest.raises(RuntimeError, match="ckpt_adapter/policy"):
        check_resume(tmp_path, ("ckpt_adapter/policy", "train_state.pt"))
