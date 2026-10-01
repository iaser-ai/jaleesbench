"""The judging, collection and Tinker-training commands, offline: option parsing, key
requirements, resume logic and preflight — with every network client stubbed out."""

import json

import pytest
from typer.testing import CliRunner

from jaleesweights import collect_small, judge, paths, train_dpo_small, train_sft_small
from jaleesweights.common import GEMINI, OPUS

runner = CliRunner()


def write_jsonl(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(r) + "\n" for r in rows))
    return path


def sitting(subject, probe, pressure, framing="unstated", chain=None):
    r = {"subject": subject, "probe_id": probe, "pressure": pressure, "framing": framing,
         "turns": [{"role": "user", "content": "u"}, {"role": "assistant", "content": "a"},
                   {"role": "user", "content": "p"}, {"role": "assistant", "content": "b"}]}
    if chain is not None:
        r["chain"] = chain
    return r


def judgment(subject, probe, pressure, judge_id, scope, framing="unstated"):
    return {"sitting_key": f"{subject}|{probe}|{pressure}|{framing}", "subject": subject, "probe_id": probe,
            "pressure": pressure, "framing": framing, "judge": judge_id, "scope": scope, "band": 1}


@pytest.fixture
def isolated(tmp_path, monkeypatch):
    monkeypatch.setattr(paths, "RUNS", tmp_path / "runs")
    monkeypatch.setattr(paths, "REFERENCE", tmp_path / "reference")
    monkeypatch.setattr(paths, "BENCH_RESULTS", tmp_path / "results")
    from jaleesweights import env
    monkeypatch.setattr(env, "ENV_PATH", tmp_path / "no.env")
    monkeypatch.setattr(env, "VERTEX_SA", tmp_path / "no-sa.json")
    for k in ("ANTHROPIC_API_KEY", "GEMINI_API_KEY", "TINKER_API_KEY"):
        monkeypatch.delenv(k, raising=False)
    return tmp_path


def no_clients(*a, **k):
    raise AssertionError("a network client was built")


# --- judge -------------------------------------------------------------------------------

def test_opus_finds_nothing_to_do_and_builds_no_client(isolated, monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "placeholder")
    monkeypatch.setattr("jaleesbench.judge.make_clients", no_clients)
    c = write_jsonl(isolated / "c.jsonl", [sitting("m", "JLS-002", "p1")])
    out = write_jsonl(isolated / "runs" / "r" / "j.jsonl",
                      [judgment("m", "JLS-002", "p1", OPUS, sc) for sc in ("turn1", "full")])
    res = runner.invoke(judge.app, ["opus", "--collect", str(c), "--out", str(out)])
    assert res.exit_code == 0, res.output
    assert "0 judgments to make" in res.output and "Anthropic" in res.output


def test_opus_counts_pending_and_dry_run_stops(isolated, monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "placeholder")
    monkeypatch.setattr("jaleesbench.judge.make_clients", no_clients)
    c = write_jsonl(isolated / "c.jsonl", [sitting("m", "JLS-002", "p1"), sitting("m", "JLS-002", "p2")])
    out = write_jsonl(isolated / "runs" / "r" / "j.jsonl", [judgment("m", "JLS-002", "p1", OPUS, "turn1")])
    res = runner.invoke(judge.app, ["opus", "--collect", str(c), "--out", str(out), "--dry-run"])
    assert res.exit_code == 0, res.output
    assert "3 judgments to make" in res.output


def test_opus_needs_only_the_anthropic_key(isolated):
    c = write_jsonl(isolated / "c.jsonl", [sitting("m", "JLS-002", "p1")])
    res = runner.invoke(judge.app, ["opus", "--collect", str(c), "--run", "r"])
    assert res.exit_code != 0
    msg = str(res.exception)
    assert msg.endswith("ANTHROPIC_API_KEY") and "GEMINI" not in msg and "TINKER" not in msg


def test_gemini_select_needs_only_a_gemini_credential(isolated, monkeypatch):
    c = write_jsonl(isolated / "c.jsonl", [sitting("m", "JLS-001", "p1", framing="guided")])
    res = runner.invoke(judge.app, ["gemini-select", "--collect", str(c), "--run", "r"])
    assert res.exit_code != 0 and "Gemini" in str(res.exception) and "ANTHROPIC" not in str(res.exception)
    monkeypatch.setenv("GEMINI_API_KEY", "placeholder")
    monkeypatch.setattr("jaleesbench.judge.make_clients", no_clients)
    out = write_jsonl(isolated / "runs" / "r" / "sel.jsonl",
                      [judgment("m", "JLS-001", "p1", GEMINI, sc, framing="guided") for sc in ("turn1", "full")])
    res = runner.invoke(judge.app, ["gemini-select", "--collect", str(c), "--out", str(out)])
    assert res.exit_code == 0 and "0 judgments to make" in res.output


def test_rate_samples_is_chain_aware_and_single_scope(isolated, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "placeholder")
    monkeypatch.setattr(judge, "make_clients", no_clients)
    c = write_jsonl(isolated / "s.jsonl", [sitting("m-sft", "JLS-001", "p1", chain=k) for k in range(2)])
    out = write_jsonl(isolated / "runs" / "r" / "rat.jsonl", [judgment("m-sft-c0", "JLS-001", "p1", GEMINI, "full")])
    res = runner.invoke(judge.app, ["rate-samples", "--collect", str(c), "--out", str(out), "--dry-run"])
    assert res.exit_code == 0, res.output
    assert "1 judgments to make" in res.output and "after-pushback scope only" in res.output
    out.write_text(out.read_text() + json.dumps(judgment("m-sft-c1", "JLS-001", "p1", GEMINI, "full")) + "\n")
    res = runner.invoke(judge.app, ["rate-samples", "--collect", str(c), "--out", str(out)])
    assert res.exit_code == 0 and "0 judgments to make" in res.output


def test_judge_refuses_to_write_into_reference(isolated, monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "placeholder")
    (isolated / "reference").mkdir()
    c = write_jsonl(isolated / "c.jsonl", [sitting("m", "JLS-002", "p1")])
    res = runner.invoke(judge.app, ["opus", "--collect", str(c), "--out", str(isolated / "reference" / "j.jsonl")])
    assert res.exit_code != 0 and "read-only" in str(res.exception)


# --- collect_small -----------------------------------------------------------------------

def test_collect_small_resume_and_preflight(isolated, monkeypatch):
    monkeypatch.setenv("TINKER_API_KEY", "placeholder")
    monkeypatch.setattr(collect_small, "AsyncOpenAI", no_clients)
    monkeypatch.setattr(paths, "GUIDED_PREFIX", write_jsonl(isolated / "g.txt", []) )
    inputs = write_jsonl(isolated / "in.jsonl", [{"probe_id": "JLS-001", "pressure": p, "turn1": "t", "pressure_text": "p"} for p in ("a", "b")])
    out = write_jsonl(isolated / "runs" / "r" / "c.jsonl", [dict(sitting("inkling-small", "JLS-001", "a"), chain=0)])
    res = runner.invoke(collect_small.app, ["train-unstated", "--inputs", str(inputs), "--out", str(out), "--dry-run"])
    assert res.exit_code == 0, res.output
    assert "2 units (1 chain/cell), 1 done, 1 to collect" in res.output and "Tinker" in res.output
    res = runner.invoke(collect_small.app, ["train-unstated", "--inputs", str(inputs), "--out", str(out), "--k", "2", "--dry-run"])
    assert "4 units (2 chains/cell), 1 done, 3 to collect" in res.output
    # complete output: nothing to do, no client, no --dry-run needed
    write_jsonl(out, [dict(sitting("inkling-small", "JLS-001", p), chain=0) for p in ("a", "b")])
    res = runner.invoke(collect_small.app, ["train-unstated", "--inputs", str(inputs), "--out", str(out)])
    assert res.exit_code == 0 and "0 to collect" in res.output


def test_collect_small_default_names_and_key(isolated, monkeypatch):
    inputs = write_jsonl(isolated / "reference" / "train_inputs_gemma.jsonl", [])
    res = runner.invoke(collect_small.app, ["train-guided", "--run", "r"])
    assert res.exit_code != 0 and str(res.exception).endswith("TINKER_API_KEY")
    monkeypatch.setenv("TINKER_API_KEY", "placeholder")
    monkeypatch.setattr(paths, "GUIDED_PREFIX", write_jsonl(isolated / "g.txt", []))
    res = runner.invoke(collect_small.app, ["train-unstated", "--run", "r", "--subject", "inkling-small-sft", "--k", "4", "--dry-run"])
    assert res.exit_code == 0, res.output
    assert "collect_small_train_unstated_sft_k4.jsonl" in res.output


# --- Tinker trainers ---------------------------------------------------------------------

def test_sft_trainer_preflight_and_dry_run(isolated, monkeypatch):
    monkeypatch.setenv("TINKER_API_KEY", "placeholder")
    called = []

    async def fake_main(cfg):
        called.append(cfg)
    monkeypatch.setattr(train_sft_small.train, "main", fake_main)
    data = write_jsonl(isolated / "reference" / "sft_train_small_messages.jsonl", [{"messages": []}] * 10)
    res = runner.invoke(train_sft_small.app, ["--run", "r", "--dry-run"])
    assert res.exit_code == 0, res.output
    assert "10 conversations" in res.output and "lr 5e-05, 2 epoch(s), batch 8 (~3 steps)" in res.output and called == []
    res = runner.invoke(train_sft_small.app, ["--run", "r"])
    assert res.exit_code == 0, res.output
    assert len(called) == 1 and called[0].learning_rate == 5e-5 and called[0].num_epochs == 2 and called[0].lora_rank == 32
    assert called[0].dataset_builder.file_path == str(data)


def test_dpo_trainer_requires_checkpoint_and_passes_settings(isolated, monkeypatch):
    monkeypatch.setenv("TINKER_API_KEY", "placeholder")
    called = []
    monkeypatch.setattr(train_dpo_small.train_dpo, "main", lambda cfg: called.append(cfg))
    comps = write_jsonl(isolated / "reference" / "comparisons_train_small_sft2.jsonl", [{"comparison": {}, "label": "A"}] * 16)
    res = runner.invoke(train_dpo_small.app, ["--run", "r"])
    assert res.exit_code != 0 and "--sft-checkpoint" in res.output
    res = runner.invoke(train_dpo_small.app, ["--run", "r", "--sft-checkpoint", "not-an-address"])
    assert res.exit_code != 0 and "tinker://" in res.output
    res = runner.invoke(train_dpo_small.app, ["--run", "r", "--sft-checkpoint", "tinker://abc/weights/final", "--dry-run"])
    assert res.exit_code == 0, res.output
    assert "from tinker://abc/weights/final on 16 pairs" in res.output and "beta 0.1, lr 1e-05, 1 epoch(s), batch 8" in res.output
    assert called == []
    res = runner.invoke(train_dpo_small.app, ["--run", "r", "--sft-checkpoint", "tinker://abc/weights/final"])
    assert res.exit_code == 0, res.output
    cfg = called[0]
    assert cfg.load_checkpoint_path == "tinker://abc/weights/final" and cfg.dpo_beta == 0.1 and cfg.learning_rate == 1e-5
    assert cfg.num_epochs == 1 and cfg.lora_rank == 32 and cfg.num_replicas == 1
    assert cfg.dataset_builder.comparison_builder.train_path == str(comps)


def test_trainers_need_only_the_tinker_key(isolated):
    write_jsonl(isolated / "reference" / "sft_train_small_messages.jsonl", [{"messages": []}])
    res = runner.invoke(train_sft_small.app, ["--run", "r", "--dry-run"])
    assert res.exit_code != 0 and str(res.exception).endswith("TINKER_API_KEY") and "ANTHROPIC" not in str(res.exception)
