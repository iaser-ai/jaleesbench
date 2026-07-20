"""CLI flag wiring (no providers touched) + judge_all failure exit code."""

import json

import pytest
from typer.testing import CliRunner

from jaleesbench import batching, citation, judge as judge_mod
from jaleesbench.cli import app

runner = CliRunner()


def test_detect_citations_turn1_flag(monkeypatch):
    seen = {}

    async def fake_detect_all(limit=None, turn1=False):
        seen.update(limit=limit, turn1=turn1)

    monkeypatch.setattr(citation, "detect_all", fake_detect_all)
    result = runner.invoke(app, ["detect-citations", "--turn1"])
    assert result.exit_code == 0
    assert seen == {"limit": None, "turn1": True}


def test_judge_lang_ar_routes_to_ar_files(monkeypatch):
    seen = {}

    async def fake_judge_all(**kwargs):
        seen.update(kwargs)

    monkeypatch.setattr(judge_mod, "judge_all", fake_judge_all)
    result = runner.invoke(app, ["judge", "--lang", "ar"])
    assert result.exit_code == 0
    assert seen["lang"] == "ar"
    assert seen["collect_path"].name == "collect_ar.jsonl"
    assert seen["out_path"].name == "judgments_ar.jsonl"


def test_judge_default_lang_en_default_files(monkeypatch):
    seen = {}

    async def fake_judge_all(**kwargs):
        seen.update(kwargs)

    monkeypatch.setattr(judge_mod, "judge_all", fake_judge_all)
    result = runner.invoke(app, ["judge"])
    assert result.exit_code == 0
    assert seen["lang"] == "en"
    assert "collect_path" not in seen and "out_path" not in seen


def test_batch_judge_lang_passthrough(monkeypatch):
    calls = []
    monkeypatch.setattr(batching, "submit",
                        lambda limit=None, lang="en": calls.append(("submit", lang)))
    monkeypatch.setattr(batching, "collect",
                        lambda lang="en": calls.append(("collect", lang)))
    assert runner.invoke(app, ["batch-judge", "submit", "--lang", "ar"]).exit_code == 0
    assert runner.invoke(app, ["batch-judge", "collect", "--lang", "ar"]).exit_code == 0
    assert calls == [("submit", "ar"), ("collect", "ar")]


async def test_judge_all_exits_nonzero_when_judgments_fail(tmp_path, monkeypatch):
    """Partial judging must be visible: failed > 0 -> SystemExit(1), mirroring
    collect."""
    sitting = {"subject": "s", "probe_id": "JLS-001", "pressure": "flattery",
               "framing": "unstated",
               "turns": [{"role": "user", "content": "q"},
                         {"role": "assistant", "content": "a"}]}
    collect_path = tmp_path / "collect.jsonl"
    collect_path.write_text(json.dumps(sitting) + "\n")

    monkeypatch.setattr(judge_mod, "load_env", lambda: None)
    monkeypatch.setattr(judge_mod, "load_probes",
                        lambda: {"probes": [{"id": "JLS-001", "proof_texts": "P"}]})
    monkeypatch.setattr(judge_mod, "make_clients", lambda *_a, **_k: {})

    async def failing_judge(*_a, **_k):
        raise RuntimeError("boom")

    monkeypatch.setattr(judge_mod, "call_judge", failing_judge)
    with pytest.raises(SystemExit) as e:
        await judge_mod.judge_all(collect_path=collect_path,
                                  out_path=tmp_path / "judgments.jsonl")
    assert e.value.code == 1
