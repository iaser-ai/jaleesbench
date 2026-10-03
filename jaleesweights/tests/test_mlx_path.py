"""The MLX path on a machine without mlx: usage, preflight, the named missing-dependency
message, the free-text question, the two-prefixes-per-conversation data preparation and the length guard."""

import builtins
import json
import py_compile
import re
import subprocess
import sys
import types
from pathlib import Path

import pytest
import typer
from typer.testing import CliRunner

from jaleesweights import paths
from jaleesweights.mlx import _common, ask, scenario, sft

runner = CliRunner()
PROJECT = Path(__file__).resolve().parents[1]


def plain(res):
    """Typer's boxed, wrapped error text as one line."""
    return " ".join(re.sub(r"[│╭╮╰╯─]", " ", res.output).split())


def write_jsonl(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(r) + "\n" for r in rows))
    return path


def conversation(n=1):
    return {"messages": [{"role": "user", "content": "u" * n}, {"role": "assistant", "content": "a"},
                         {"role": "user", "content": "p"}, {"role": "assistant", "content": "b"}]}


def cell(probe="JLS-001", pressure="flattery"):
    return {"probe_id": probe, "pressure": pressure, "turn1": "opening", "pressure_text": "push"}


@pytest.fixture
def isolated(tmp_path, monkeypatch):
    monkeypatch.setattr(paths, "RUNS", tmp_path / "runs")
    monkeypatch.setattr(paths, "REFERENCE", tmp_path / "reference")
    return tmp_path


@pytest.mark.parametrize("name", ["sft", "scenario", "ask"])
def test_compiles_and_prints_usage(name):
    py_compile.compile(str(PROJECT / "jaleesweights" / "mlx" / f"{name}.py"), doraise=True)
    out = subprocess.run([sys.executable, "-m", f"jaleesweights.mlx.{name}", "--help"],
                         cwd=PROJECT, capture_output=True, text=True)
    assert out.returncode == 0 and "--dry-run" in out.stdout


def test_sft_preflight_and_dry_run(isolated):
    data = write_jsonl(isolated / "sft_messages.jsonl", [conversation()] * 10)
    res = runner.invoke(sft.app, ["--data", str(data), "--run", "d", "--limit", "4", "--iters", "8", "--dry-run"])
    assert res.exit_code == 0, res.output
    assert "10 conversations, using the first 4 -> 8 rows" in res.output
    assert "LoRA rank 8, scale 20, top 16 layers; lr 1e-05, batch 1, 8 iterations (~1.0 passes), seq cap 4096" in res.output
    assert "precision: 4bit as converted" in res.output and "dry run" in res.output
    assert not (isolated / "runs" / "d" / "mlx-sft" / "data").exists()  # the dry run writes nothing
    res = runner.invoke(sft.app, ["--data", str(isolated / "missing.jsonl"), "--run", "d", "--dry-run"])
    assert res.exit_code != 0 and "does not exist" in res.output


def test_sft_refuses_to_overwrite_or_write_reference(isolated):
    data = write_jsonl(isolated / "sft_messages.jsonl", [conversation()])
    adapter = isolated / "runs" / "d" / "mlx-sft" / "adapter" / "adapters.safetensors"
    adapter.parent.mkdir(parents=True)
    adapter.write_bytes(b"")
    res = runner.invoke(sft.app, ["--data", str(data), "--run", "d", "--dry-run"])
    assert res.exit_code != 0 and "already holds an adapter" in plain(res)
    res = runner.invoke(sft.app, ["--data", str(data), "--out", str(isolated / "reference" / "x"), "--dry-run"])
    assert res.exit_code != 0 and "read-only" in str(res.exception)


def test_prefixes_two_rows_per_conversation_and_role_check():
    rows = sft.prefixes([conversation(), conversation(2)])
    assert len(rows) == 4
    assert [m["role"] for m in rows[0]["messages"]] == ["user", "assistant"]
    assert [m["role"] for m in rows[1]["messages"]] == ["user", "assistant", "user", "assistant"]
    assert rows[1]["messages"] == conversation()["messages"]
    with pytest.raises(typer.BadParameter, match="not a two-exchange"):
        sft.prefixes([{"messages": conversation()["messages"][:3]}])


def test_check_lengths_refuses_rows_over_the_cap():
    class Tok:
        def apply_chat_template(self, messages):
            return [0] * sum(len(m["content"]) for m in messages)
    rows = sft.prefixes([conversation(), conversation(50)])
    assert sft.check_lengths(Tok(), rows, 100) == 53
    with pytest.raises(RuntimeError, match="1 of 4 rows exceed --max-seq-length 52"):
        sft.check_lengths(Tok(), rows, 52)


def test_scenario_preflight_dry_run_and_guards(isolated):
    inputs = write_jsonl(isolated / "eval_inputs.jsonl", [cell(), cell(pressure="insistence")])
    args = ["--probe", "JLS-001", "--pressure", "flattery", "--inputs", str(inputs), "--run", "d"]
    res = runner.invoke(scenario.app, args + ["--dry-run"])
    assert res.exit_code == 0, res.output
    assert "cell JLS-001/flattery" in res.output and "greedy decoding" in res.output
    assert "scenario_JLS-001_flattery_mlx-base.jsonl" in res.output and "dry run" in res.output
    res = runner.invoke(scenario.app, args[:-2] + ["--pressure", "nope", "--inputs", str(inputs), "--dry-run"])
    assert res.exit_code != 0 and "JLS-001 has pressures flattery, insistence" in plain(res)
    res = runner.invoke(scenario.app, args + ["--adapter", str(isolated), "--dry-run"])
    assert res.exit_code != 0 and "not an mlx_lm adapter directory" in plain(res)
    out = isolated / "runs" / "d" / "scenario_JLS-001_flattery_mlx-base.jsonl"
    out.write_text("")  # the run directory exists from the dry run above
    res = runner.invoke(scenario.app, args + ["--dry-run"])
    assert res.exit_code != 0 and "already exists" in plain(res)


def test_ask_preflight_dry_run_and_guards(tmp_path):
    res = runner.invoke(ask.app, ["Should I take the job?", "--dry-run"])
    assert res.exit_code == 0, res.output
    assert "one question with MLX from mlx-community/gemma-4-E4B-it-4bit (base)" in res.output
    assert "question: Should I take the job?" in res.output
    assert "thinking off, greedy decoding, up to 2048 tokens" in res.output and "dry run" in res.output
    res = runner.invoke(ask.app, ["Should I take the job?", "--adapter", str(tmp_path), "--dry-run"])
    assert res.exit_code != 0 and "not an mlx_lm adapter directory" in plain(res)
    (tmp_path / "adapters.safetensors").write_bytes(b"")
    res = runner.invoke(ask.app, ["Should I take the job?", "--adapter", str(tmp_path), "--dry-run"])
    assert res.exit_code == 0 and f"+ adapter {tmp_path}" in plain(res)
    res = runner.invoke(ask.app, ["  ", "--dry-run"])
    assert res.exit_code != 0 and "the question is empty" in plain(res)
    assert runner.invoke(ask.app, ["--dry-run"]).exit_code != 0  # the question is required


def test_ask_prints_a_reply_that_hits_the_cap_then_fails(monkeypatch, capsys):
    class Tok:
        def apply_chat_template(self, turns, add_generation_prompt, enable_thinking):
            assert enable_thinking is False and [t["role"] for t in turns] == ["user"]
            return [0]

        def encode(self, text, add_special_tokens):
            return text.split()
    fake = types.SimpleNamespace(load=lambda name, adapter_path: (None, Tok()),
                                 generate=lambda model, tok, prompt, max_tokens: "he said " * (max_tokens // 2))
    core = types.SimpleNamespace(get_active_memory=lambda: 0, get_peak_memory=lambda: 0)
    monkeypatch.setattr(ask, "require_mlx", lambda: fake)
    monkeypatch.setitem(sys.modules, "mlx", types.SimpleNamespace(core=core))
    monkeypatch.setitem(sys.modules, "mlx.core", core)
    with pytest.raises(SystemExit, match="reply hit --max-tokens 8 and is cut off above"):
        ask.ask("m", None, "q", 8)
    assert "he said he said" in capsys.readouterr().out  # shown, not hidden
    ask.ask("m", None, "q", 9)  # a reply under the cap ends normally


def no_mlx(monkeypatch):
    real_import = builtins.__import__

    def refuse(name, *a, **k):
        if name.startswith("mlx"):
            raise ImportError("No module named 'mlx_lm'")
        return real_import(name, *a, **k)
    monkeypatch.setattr(builtins, "__import__", refuse)


def test_missing_mlx_is_named(monkeypatch):
    no_mlx(monkeypatch)
    with pytest.raises(SystemExit, match="missing MLX dependency: mlx_lm .*uv sync --group mlx"):
        _common.require_mlx()


def test_ask_without_mlx_stops_with_the_named_message(monkeypatch):
    no_mlx(monkeypatch)
    monkeypatch.delitem(sys.modules, "mlx_lm", raising=False)
    res = runner.invoke(ask.app, ["Should I take the job?"])
    assert res.exit_code != 0 and "missing MLX dependency: mlx_lm" in str(res.exception)


def test_precision_line_reads_the_id_and_sizes_local_weights(tmp_path):
    (tmp_path / "model.safetensors").write_bytes(b"\0" * 2**20)
    assert _common.precision_line(str(tmp_path)) == (
        "precision: unknown from the model id as converted; weights on disk 0.0 GB "
        "(resident at load is a little less; training adds activations)")
    line = _common.precision_line("mlx-community/no-such-model-4bit")
    assert line.startswith("precision: 4bit as converted; not downloaded yet")
