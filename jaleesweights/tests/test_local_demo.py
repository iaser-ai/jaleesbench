"""The local demonstration on a machine without a GPU: usage, preflight, the named
missing-dependency message, and the tokenizer-only loss-mask check."""

import importlib.util
import json
import py_compile
import subprocess
import sys
from pathlib import Path

import pytest
from typer.testing import CliRunner

from jaleesweights import paths
from jaleesweights.local import _common, gemma_collect, gemma_dpo, gemma_sft

runner = CliRunner()
PROJECT = Path(__file__).resolve().parents[1]
COMMANDS = {"gemma_sft": gemma_sft, "gemma_dpo": gemma_dpo, "gemma_collect": gemma_collect}


def write_jsonl(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(r) + "\n" for r in rows))
    return path


def turns():
    return [{"role": "user", "content": "u"}, {"role": "assistant", "content": "a"},
            {"role": "user", "content": "p"}, {"role": "assistant", "content": "b"}]


@pytest.fixture
def isolated(tmp_path, monkeypatch):
    monkeypatch.setattr(paths, "RUNS", tmp_path / "runs")
    monkeypatch.setattr(paths, "REFERENCE", tmp_path / "reference")
    return tmp_path


@pytest.mark.parametrize("name", list(COMMANDS))
def test_compiles_and_prints_usage(name):
    py_compile.compile(str(PROJECT / "jaleesweights" / "local" / f"{name}.py"), doraise=True)
    out = subprocess.run([sys.executable, "-m", f"jaleesweights.local.{name}", "--help"],
                         cwd=PROJECT, capture_output=True, text=True)
    assert out.returncode == 0 and "--dry-run" in out.stdout


def test_sft_preflight_and_dry_run(isolated):
    data = write_jsonl(isolated / "sft.jsonl", [{"probe_id": "p", "pressure": "q", "turns": turns()}] * 10)
    res = runner.invoke(gemma_sft.app, ["--data", str(data), "--run", "d", "--limit", "4", "--dry-run"])
    assert res.exit_code == 0, res.output
    assert "10 conversations, using the first 4" in res.output
    assert "bf16, LoRA rank 32, lr 5e-05, 2 epoch(s), batch 8 (~1 steps)" in res.output
    assert "GPU: none" in res.output and "dry run" in res.output
    res = runner.invoke(gemma_sft.app, ["--data", str(isolated / "missing.jsonl"), "--run", "d", "--dry-run"])
    assert res.exit_code != 0 and "does not exist" in res.output


def test_dpo_preflight_requires_an_adapter_directory(isolated):
    pairs = write_jsonl(isolated / "pairs.jsonl", [{"probe_id": "p", "pressure": "q",
                                                    "chosen_turns": turns(), "rejected_turns": turns()}] * 16)
    res = runner.invoke(gemma_dpo.app, ["--pairs", str(pairs), "--sft-adapter", str(isolated / "nope"), "--dry-run"])
    assert res.exit_code != 0 and "not a PEFT adapter directory" in res.output
    adapter = isolated / "adapter"
    adapter.mkdir()
    (adapter / "adapter_config.json").write_text("{}")
    res = runner.invoke(gemma_dpo.app, ["--pairs", str(pairs), "--sft-adapter", str(adapter), "--run", "d", "--dry-run"])
    assert res.exit_code == 0, res.output
    assert "pairs" in res.output and ": 16" in res.output and "beta 0.1, lr 1e-05, 1 epoch, batch 8 (~2 steps)" in res.output
    assert "GPU: none" in res.output


def test_collect_preflight_names_pass_and_output(isolated, monkeypatch):
    monkeypatch.setattr(paths, "GUIDED_PREFIX", write_jsonl(isolated / "guide.txt", []))
    inputs = write_jsonl(isolated / "in.jsonl", [{"probe_id": "p", "pressure": f"q{i}", "turn1": "t", "pressure_text": "x"} for i in range(6)])
    res = runner.invoke(gemma_collect.app, ["--inputs", str(inputs), "--run", "d", "--subject", "gemma-demo", "--dry-run"])
    assert res.exit_code == 0, res.output
    assert "6 cells; unstated; k=1; model-default sampling" in res.output and "collect_gemma-demo_in_unstated.jsonl" in res.output
    res = runner.invoke(gemma_collect.app, ["--inputs", str(inputs), "--run", "d", "--guide", "--k", "4",
                                            "--temperature", "1.3", "--limit", "5", "--dry-run"])
    assert res.exit_code != 0 and "stage-2 sampling is bare" in res.output
    res = runner.invoke(gemma_collect.app, ["--inputs", str(inputs), "--run", "d", "--k", "4",
                                            "--temperature", "1.3", "--limit", "5", "--dry-run"])
    assert res.exit_code == 0, res.output
    assert "using the first 5; unstated; k=4; temperature 1.3" in res.output and "_in_unstated_k4.jsonl" in res.output
    res = runner.invoke(gemma_collect.app, ["--inputs", str(inputs), "--run", "d", "--dtype", "int4", "--dry-run"])
    assert res.exit_code != 0 and "unknown dtype" in res.output
    res = runner.invoke(gemma_collect.app, ["--inputs", str(inputs), "--run", "d", "--k", "4", "--dry-run"])
    assert res.exit_code != 0 and "explicit --temperature" in res.output
    bad = write_jsonl(isolated / "bad.jsonl", [{"probe_id": "p", "turns": []}])
    res = runner.invoke(gemma_collect.app, ["--inputs", str(bad), "--run", "d", "--dry-run"])
    assert res.exit_code != 0 and "not a conversation-inputs file" in res.output


def test_outputs_cannot_land_in_reference(isolated):
    (isolated / "reference").mkdir()
    data = write_jsonl(isolated / "sft.jsonl", [{"probe_id": "p", "pressure": "q", "turns": turns()}])
    res = runner.invoke(gemma_sft.app, ["--data", str(data), "--out", str(isolated / "reference" / "x"), "--dry-run"])
    assert res.exit_code != 0 and "read-only" in str(res.exception)


@pytest.mark.skipif(importlib.util.find_spec("peft") is not None and importlib.util.find_spec("vllm") is not None,
                    reason="GPU group installed; the real run would start loading the model")
def test_real_run_names_the_missing_gpu_dependency(isolated, monkeypatch):
    data = write_jsonl(isolated / "sft.jsonl", [{"probe_id": "p", "pressure": "q", "turns": turns()}])
    res = runner.invoke(gemma_sft.app, ["--data", str(data), "--run", "d", "--limit", "1"])
    assert res.exit_code != 0
    msg = str(res.exception)
    assert msg.startswith("missing GPU dependency:") and "uv sync --group gpu" in msg
    inputs = write_jsonl(isolated / "in.jsonl", [{"probe_id": "p", "pressure": "q", "turn1": "t", "pressure_text": "x"}])
    res = runner.invoke(gemma_collect.app, ["--inputs", str(inputs), "--run", "d"])
    assert res.exit_code != 0 and "missing GPU dependency:" in str(res.exception)


def test_render_masks_exactly_the_assistant_turns_with_the_real_tokenizer():
    """Needs the model's tokenizer from the Hugging Face Hub (a few MB, ungated); skipped offline."""
    try:
        from transformers import AutoTokenizer
        tok = AutoTokenizer.from_pretrained(_common.DEFAULT_MODEL)
    except Exception as e:  # noqa: BLE001 — offline, or the hub unreachable
        pytest.skip(f"tokenizer unavailable: {e}")
    conv = [{"role": "user", "content": "Hello there"}, {"role": "assistant", "content": "Peace be upon you."},
            {"role": "user", "content": "Push back"}, {"role": "assistant", "content": "I stay."}]
    ids, mask = _common.make_render(tok)(conv)
    assert len(ids) == len(mask) and any(mask) and not all(mask)
    masked = tok.decode([i for i, m in zip(ids, mask) if m])
    assert "Peace be upon you." in masked and "I stay." in masked
    assert "Hello there" not in masked and "Push back" not in masked


def test_resume_from_must_be_a_complete_checkpoint(isolated):
    data = write_jsonl(isolated / "sft.jsonl", [{"probe_id": "p", "pressure": "q", "turns": turns()}])
    partial = isolated / "partial"
    (partial / "adapter").mkdir(parents=True)  # adapter but no train_state.pt
    for bad in (isolated / "nowhere", partial):
        res = runner.invoke(gemma_sft.app, ["--data", str(data), "--run", "d", "--resume-from", str(bad), "--dry-run"])
        assert res.exit_code != 0 and "not a complete checkpoint" in res.output
    (partial / "train_state.pt").write_bytes(b"")
    res = runner.invoke(gemma_sft.app, ["--data", str(data), "--run", "d", "--resume-from", str(partial), "--dry-run"])
    assert res.exit_code == 0 and f"resuming from {partial}" in res.output
    pairs = write_jsonl(isolated / "pairs.jsonl", [{"probe_id": "p", "pressure": "q", "chosen_turns": turns(), "rejected_turns": turns()}])
    adapter = isolated / "adapter"
    adapter.mkdir()
    (adapter / "adapter_config.json").write_text("{}")
    res = runner.invoke(gemma_dpo.app, ["--pairs", str(pairs), "--sft-adapter", str(adapter), "--resume-from", str(partial), "--dry-run"])
    assert res.exit_code != 0 and "ckpt_adapter/policy" in res.output


def test_collect_prepares_the_output_path_before_loading(isolated, monkeypatch):
    monkeypatch.setattr(paths, "GUIDED_PREFIX", write_jsonl(isolated / "guide.txt", []))
    inputs = write_jsonl(isolated / "in.jsonl", [{"probe_id": "p", "pressure": "q", "turn1": "t", "pressure_text": "x"}])
    out = isolated / "deep" / "er" / "c.jsonl"
    res = runner.invoke(gemma_collect.app, ["--inputs", str(inputs), "--out", str(out), "--dry-run"])
    assert res.exit_code == 0, res.output
    assert out.parent.is_dir() and not out.exists()
    out.write_text("")
    res = runner.invoke(gemma_collect.app, ["--inputs", str(inputs), "--out", str(out), "--dry-run"])
    assert res.exit_code != 0 and "already exists" in res.output
