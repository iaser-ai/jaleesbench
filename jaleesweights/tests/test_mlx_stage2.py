"""Stage 2 of the MLX path on a machine without mlx: usage, preflight and guards of the
sampling and DPO commands, the loss on a toy example, the assistant-token mask, the evenly
spaced subset and the memory ceiling."""

import hashlib
import json
import math
import py_compile
import re
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
from typer.testing import CliRunner

from jaleesweights import paths
from jaleesweights.mlx import _common, dpo, sample

runner = CliRunner()
PROJECT = Path(__file__).resolve().parents[1]


def plain(res):
    """Typer's boxed, wrapped error text as one line."""
    return " ".join(re.sub(r"[│╭╮╰╯─]", " ", res.output).split())


def write_jsonl(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(r) + "\n" for r in rows))
    return path


def cells(n):
    return [{"probe_id": f"JLS-{i:03d}", "pressure": "flattery", "turn1": "opening", "pressure_text": "push"} for i in range(n)]


@pytest.fixture
def isolated(tmp_path, monkeypatch):
    monkeypatch.setattr(paths, "RUNS", tmp_path / "runs")
    monkeypatch.setattr(paths, "REFERENCE", tmp_path / "reference")
    adapter = tmp_path / "adapter"
    adapter.mkdir()
    (adapter / "adapters.safetensors").write_bytes(b"")
    (adapter / "adapter_config.json").write_text("{}")
    return tmp_path


@pytest.mark.parametrize("name", ["sample", "dpo"])
def test_compiles_and_prints_usage(name):
    py_compile.compile(str(PROJECT / "jaleesweights" / "mlx" / f"{name}.py"), doraise=True)
    out = subprocess.run([sys.executable, "-m", f"jaleesweights.mlx.{name}", "--help"],
                         cwd=PROJECT, capture_output=True, text=True)
    assert out.returncode == 0 and "--dry-run" in out.stdout and "--memory-limit-gb" in out.stdout


def test_dpo_loss_is_log2_at_init_and_falls_as_the_policy_improves():
    loss, margin, coef = dpo.dpo_terms(-100.0, -120.0, -100.0, -120.0, beta=0.1)
    assert loss == pytest.approx(math.log(2)) and margin == 0 and coef == pytest.approx(0.05)
    better, m_better, c_better = dpo.dpo_terms(-95.0, -125.0, -100.0, -120.0, beta=0.1)
    worse, m_worse, _ = dpo.dpo_terms(-105.0, -115.0, -100.0, -120.0, beta=0.1)
    assert better < loss < worse and m_better == 10 and m_worse == -10 and c_better < coef
    assert better == pytest.approx(-math.log(1 / (1 + math.exp(-1.0))))  # -log sigmoid(beta * margin)
    far, _, c_far = dpo.dpo_terms(-1e5, 0.0, 0.0, 0.0, beta=0.1)  # no overflow far from the reference
    assert far == pytest.approx(1e4) and c_far == pytest.approx(0.1)


def test_render_masks_assistant_tokens_and_requires_a_prefix_stable_template():
    class Tok:
        def apply_chat_template(self, turns, enable_thinking):
            assert enable_thinking is False
            return [t for turn in turns for t in [0] + [1 if turn["role"] == "assistant" else 2] * len(turn["content"])]
    turns = [{"role": "user", "content": "uu"}, {"role": "assistant", "content": "aaa"},
             {"role": "user", "content": "u"}, {"role": "assistant", "content": "a"}]
    ids, mask = dpo.render(Tok(), turns)
    assert ids == [0, 2, 2, 0, 1, 1, 1, 0, 2, 0, 1]
    assert mask == [False] * 3 + [True] * 4 + [False] * 2 + [True] * 2

    class Unstable(Tok):
        def apply_chat_template(self, turns, enable_thinking):
            return [len(turns)] * len(turns)
    with pytest.raises(RuntimeError, match="not prefix-stable"):
        dpo.render(Unstable(), turns)


def test_spread_takes_evenly_spaced_cells():
    rows = cells(420)
    picked = sample.spread(rows, 40)
    assert len(picked) == 40 and picked[0] is rows[0] and picked[1] is rows[10] and picked[-1] is rows[390]
    assert sample.spread(rows, 0) is rows and sample.spread(rows, 999) is rows
    assert len(sample.spread(cells(7), 3)) == 3


def test_cap_memory_sets_the_limits_and_stops_past_the_ceiling():
    calls = SimpleNamespace(peak=2**30, cleared=0, limits={})
    mx = SimpleNamespace(set_memory_limit=lambda n: calls.limits.update(memory=n),
                         set_cache_limit=lambda n: calls.limits.update(cache=n),
                         get_peak_memory=lambda: calls.peak,
                         clear_cache=lambda: setattr(calls, "cleared", calls.cleared + 1))
    check = _common.cap_memory(mx, 2)
    assert calls.limits == {"memory": 2 * 2**30, "cache": 2**28}
    check()
    assert calls.cleared == 1
    calls.peak = 3 * 2**30
    with pytest.raises(RuntimeError, match="peak memory 3.0 GB passed the 2 GB ceiling"):
        check()


def test_sample_preflight_resume_and_guards(isolated):
    inputs = write_jsonl(isolated / "train_inputs.jsonl", cells(20))
    args = ["--adapter", str(isolated / "adapter"), "--inputs", str(inputs), "--run", "d", "--limit", "5"]
    res = runner.invoke(sample.app, args + ["--dry-run"])
    assert res.exit_code == 0, res.output
    assert "20 cells, 5 evenly spaced" in res.output
    assert "5 cells x 4 chains = 20 sittings of two turns; temperature 1.3, top-p 0.95, top-k 64" in res.output
    assert "estimated time: about 6 minutes" in res.output and "memory ceiling 24 GB" in res.output
    assert "collect_mlx-sft_train_unstated_k4.jsonl" in res.output and "dry run" in res.output
    out = isolated / "runs" / "d" / "collect_mlx-sft_train_unstated_k4.jsonl"
    write_jsonl(out, cells(20)[:1])
    res = runner.invoke(sample.app, args + ["--dry-run"])  # rows, but nothing says what made them
    assert res.exit_code != 0 and "has samples but no" in plain(res)
    settings = {"model": _common.DEFAULT_MODEL, "adapter": str(isolated / "adapter"), "inputs": str(inputs),
                "subject": "mlx-sft", "k": 4, "adapter_sha256": hashlib.sha256(b"").hexdigest(),
                "temperature": 1.3, "top_p": 0.95, "top_k": 64, "max_tokens": 2048, "seed": 3446}
    sample.state_path(out).write_text(json.dumps({"settings": settings, "done": [["JLS-000", "flattery"]]}))
    res = runner.invoke(sample.app, args + ["--dry-run"])
    assert "1 already sampled" in res.output and "4 cells x 4 chains = 16 sittings" in res.output
    res = runner.invoke(sample.app, args + ["--temperature", "1.0", "--dry-run"])  # another policy into the same file
    assert res.exit_code != 0 and "different settings (temperature)" in plain(res)
    (isolated / "adapter" / "adapters.safetensors").write_bytes(b"retrained")
    res = runner.invoke(sample.app, args + ["--dry-run"])
    assert res.exit_code != 0 and "different settings (adapter_sha256)" in plain(res)
    (isolated / "adapter" / "adapters.safetensors").write_bytes(b"")
    res = runner.invoke(sample.app, args + ["--k", "1", "--dry-run"])
    assert res.exit_code != 0 and "at least two chains" in plain(res)
    res = runner.invoke(sample.app, ["--adapter", str(isolated), "--inputs", str(inputs), "--dry-run"])
    assert res.exit_code != 0 and "not an mlx_lm adapter directory" in plain(res)
    bad = write_jsonl(isolated / "bad.jsonl", [{"probe_id": "JLS-001"}])
    res = runner.invoke(sample.app, ["--adapter", str(isolated / "adapter"), "--inputs", str(bad), "--dry-run"])
    assert res.exit_code != 0 and "not a conversation-inputs file" in plain(res)


def test_dpo_preflight_and_guards(isolated):
    pairs = write_jsonl(isolated / "pairs.jsonl", [{"probe_id": "JLS-001"}] * 20)
    args = ["--pairs", str(pairs), "--sft-adapter", str(isolated / "adapter"), "--run", "d"]
    res = runner.invoke(dpo.app, args + ["--dry-run"])
    assert res.exit_code == 0, res.output
    assert "beta 0.1, lr 1e-05, 1 pass, batch 8 (~3 steps), seq cap 4096, seed 3446" in res.output
    assert "the same adapter, frozen, is the reference" in res.output and "memory ceiling 24 GB" in res.output
    assert not (isolated / "runs" / "d" / "mlx-sft-dpo").exists()  # the dry run writes nothing
    res = runner.invoke(dpo.app, ["--pairs", str(pairs), "--sft-adapter", str(isolated), "--dry-run"])
    assert res.exit_code != 0 and "not an mlx_lm adapter directory" in plain(res)
    (isolated / "adapter" / "adapter_config.json").unlink()  # weights without the config mlx_lm.load reads
    res = runner.invoke(dpo.app, args + ["--dry-run"])
    assert res.exit_code != 0 and "no adapter_config.json" in plain(res)
    (isolated / "adapter" / "adapter_config.json").write_text("{}")
    res = runner.invoke(dpo.app, ["--pairs", str(isolated / "none.jsonl"), "--sft-adapter", str(isolated / "adapter"), "--dry-run"])
    assert res.exit_code != 0 and "does not exist" in res.output
    (isolated / "runs" / "d" / "mlx-sft-dpo" / "adapter").mkdir(parents=True)
    res = runner.invoke(dpo.app, args + ["--dry-run"])
    assert res.exit_code != 0 and "already holds an adapter" in plain(res)
