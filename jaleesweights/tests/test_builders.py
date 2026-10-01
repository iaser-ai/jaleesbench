"""Offline tests of the free steps on small made-up data."""

import json

import pytest
from typer.testing import CliRunner

from jaleesweights import comparisons, inputs, pairs, paths, sft_small
from jaleesweights.common import GEMINI

PROBES = ["JLS-001", "JLS-002"]
PRESSURES = ["secularize", "insistence"]
SPLIT = {"train": ["JLS-001"], "test": ["JLS-002"], "seed": 3446}


def turns(a1="a1", a2="a2", u1="u1", u2="u2"):
    return [{"role": "user", "content": u1}, {"role": "assistant", "content": a1},
            {"role": "user", "content": u2}, {"role": "assistant", "content": a2}]


def write_jsonl(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(r) + "\n" for r in rows))
    return path


def judgment(subject, probe, pressure, band, scope="full", framing="unstated", judge=GEMINI):
    return {"subject": subject, "probe_id": probe, "pressure": pressure, "framing": framing,
            "judge": judge, "scope": scope, "band": band,
            "sitting_key": f"{subject}|{probe}|{pressure}|{framing}"}


# --- pairs: max-gap, both directions, dedup, gap floor, dangling screen, chain naming ----

def test_pairs_max_gap_both_directions(tmp_path):
    # one training cell, four draws rated +2, +2, 0, -2
    bands = {"s0": 2, "s1": 2, "s2": 0, "s3": -2}
    samples = [{"subject": s, "probe_id": "JLS-001", "pressure": "secularize", "framing": "unstated",
                "turns": turns(a1=f"answer {s}")} for s in bands]
    judgments = [judgment(s, "JLS-001", "secularize", b) for s, b in bands.items()]
    # a held-out cell must be ignored even if rated
    judgments.append(judgment("s0", "JLS-002", "secularize", 2))
    built, stats, hist, n_cells = pairs.build(
        write_jsonl(tmp_path / "samples.jsonl", samples),
        write_jsonl(tmp_path / "judg.jsonl", judgments), SPLIT)
    got = {(p["chosen_subject"], p["rejected_subject"]) for p in built}
    # anchors: s0 -> (s0, s3); s1 -> (s1, s3); s2 -> above (s0, s2), below (s2, s3); s3 -> (s0, s3) dup
    assert got == {("s0", "s3"), ("s1", "s3"), ("s0", "s2"), ("s2", "s3")}
    assert all(p["chosen_band"] - p["rejected_band"] >= 2 for p in built)
    assert stats["pair"] == 4 and stats["cells_covered"] == 1 and n_cells == 1
    assert hist == {2: 2, 0: 1, -2: 1}


def test_pairs_dangling_screen_and_no_spread(tmp_path):
    samples = [
        {"subject": "s0", "probe_id": "JLS-001", "pressure": "secularize", "framing": "unstated",
         "turns": turns(a2="see [3]")},  # +2 but dangling marker -> screened as chosen
        {"subject": "s1", "probe_id": "JLS-001", "pressure": "secularize", "framing": "unstated", "turns": turns()},
        {"subject": "s0", "probe_id": "JLS-001", "pressure": "insistence", "framing": "unstated", "turns": turns()},
        {"subject": "s1", "probe_id": "JLS-001", "pressure": "insistence", "framing": "unstated", "turns": turns()},
    ]
    judgments = [judgment("s0", "JLS-001", "secularize", 2), judgment("s1", "JLS-001", "secularize", -2),
                 judgment("s0", "JLS-001", "insistence", 1), judgment("s1", "JLS-001", "insistence", 0)]  # gap 1
    built, stats, _, _ = pairs.build(write_jsonl(tmp_path / "s.jsonl", samples),
                                     write_jsonl(tmp_path / "j.jsonl", judgments), SPLIT)
    assert built == [] and stats["chosen_screened_dangling"] == 1 and stats["cells_no_spread"] == 2


def test_pairs_chain_records_are_keyed_like_their_ratings(tmp_path):
    samples = [{"subject": "m-sft", "chain": c, "probe_id": "JLS-001", "pressure": "secularize",
                "framing": "unstated", "turns": turns(a1=f"c{c}")} for c in range(2)]
    judgments = [judgment("m-sft-c0", "JLS-001", "secularize", 2), judgment("m-sft-c1", "JLS-001", "secularize", -2)]
    built, *_ = pairs.build(write_jsonl(tmp_path / "s.jsonl", samples), write_jsonl(tmp_path / "j.jsonl", judgments), SPLIT)
    assert [(p["chosen_subject"], p["rejected_subject"]) for p in built] == [("m-sft-c0", "m-sft-c1")]
    assert built[0]["chosen_turns"][1]["content"] == "c0"


# --- comparisons -------------------------------------------------------------------------

def test_comparisons_export_is_seeded_and_masks_nothing_but_roles(tmp_path):
    rows = [{"probe_id": "JLS-001", "pressure": "secularize",
             "chosen_turns": turns(a1=f"good {i}"), "rejected_turns": turns(a1=f"bad {i}")} for i in range(20)]
    src = write_jsonl(tmp_path / "pairs_train70_x.jsonl", rows)
    out1, n_a1 = comparisons.build(src)
    out2, n_a2 = comparisons.build(src)
    assert out1 == out2 and 0 < n_a1 < 20  # seeded coin flips, both sides used
    for r, p in zip(out1, rows):
        c = r["comparison"]
        assert c["prompt_conversation"] == [p["chosen_turns"][0]]
        good = c["completion_A"] if r["label"] == "A" else c["completion_B"]
        assert good == p["chosen_turns"][1:]
    bad = write_jsonl(tmp_path / "bad.jsonl", [{"probe_id": "x", "pressure": "y",
                                                "chosen_turns": turns(u1="A"), "rejected_turns": turns(u1="B")}])
    with pytest.raises(RuntimeError, match="prompt mismatch"):
        comparisons.build(bad)


# --- inputs ------------------------------------------------------------------------------

def test_inputs_fail_fast_on_inconsistent_cells(tmp_path, monkeypatch):
    from jaleesbench.collect import load_probes
    bank_pressures = [p["id"] if isinstance(p, dict) else p for p in load_probes()["pressures"]]
    monkeypatch.setattr(inputs, "CELLS_PER_HALF", len(bank_pressures))
    rows = [{"subject": s, "probe_id": p, "pressure": pr, "framing": "unstated",
             "turns": turns(u1=f"open {p}", u2=f"push {pr}")}
            for p in PROBES for pr in bank_pressures for s in ("a", "b")]
    halves = inputs.build(write_jsonl(tmp_path / "c.jsonl", rows), SPLIT)
    assert {r["probe_id"] for r in halves["train"]} == {"JLS-001"}
    assert [r["pressure"] for r in halves["train"]] == sorted(bank_pressures)   # training half sorted
    assert [r["pressure"] for r in halves["test"]] == bank_pressures            # held-out half in bank order
    assert halves["test"][0]["turn1"] == "open JLS-002"
    rows[1]["turns"][2]["content"] = "a different pressure turn"
    with pytest.raises(RuntimeError, match="differs across subjects"):
        inputs.build(write_jsonl(tmp_path / "c.jsonl", rows), SPLIT)


# --- a new run chains: sft_small writes into the run dir, the next step reads from there --

def test_new_run_chains_through_the_run_directory(tmp_path, monkeypatch):
    monkeypatch.setattr(paths, "RUNS", tmp_path / "runs")
    monkeypatch.setattr(paths, "REFERENCE", tmp_path / "reference-must-not-be-touched")
    collect = write_jsonl(tmp_path / "in" / "collect.jsonl", [
        {"subject": "demo", "probe_id": "JLS-001", "pressure": pr, "framing": "guided", "turns": turns(a1=f"g {pr}")}
        for pr in PRESSURES])
    judg = write_jsonl(tmp_path / "in" / "sel.jsonl",
                       [judgment("demo", "JLS-001", pr, 2, scope=sc, framing="guided") for pr in PRESSURES for sc in ("turn1", "full")])
    res = CliRunner().invoke(sft_small.app, ["--collect", str(collect), "--judgments", str(judg),
                                             "--subject", "demo", "--run", "demo-run"])
    assert res.exit_code == 0, res.output
    out = tmp_path / "runs" / "demo-run" / "sft_train_small.jsonl"
    msgs = tmp_path / "runs" / "demo-run" / "sft_train_small_messages.jsonl"
    assert out.exists() and msgs.exists()
    assert [json.loads(l)["messages"][1]["content"] for l in msgs.read_text().splitlines()] == ["g insistence", "g secularize"]
    assert not (tmp_path / "reference-must-not-be-touched").exists()
