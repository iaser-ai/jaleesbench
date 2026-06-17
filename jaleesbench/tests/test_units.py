"""Pure / deterministic units: keys, prompt blocks, parsing, scoring overlay."""

import json

import pytest

from jaleesbench import collect, judge, prompts, score


# --- collect: keys, context block, probe loading ---------------------------

def test_sitting_key():
    r = {"subject": "gpt-5.5", "probe_id": "JLS-001",
         "pressure": "flattery", "framing": "guided"}
    assert collect.sitting_key(r) == "gpt-5.5|JLS-001|flattery|guided"


def test_ctx_block():
    assert collect.ctx_block("be kind") == "[Context for this conversation: be kind]"


def test_load_probes_reads_from_data(tmp_path, monkeypatch):
    """load_probes resolves `path` against DATA, never the cwd."""
    payload = {"version": 9, "probes": [{"id": "X-1"}]}
    (tmp_path / "probes.json").write_text(json.dumps(payload))
    monkeypatch.setattr(collect, "DATA", tmp_path)
    assert collect.load_probes() == payload
    # an explicit relative name is still resolved under DATA
    (tmp_path / "mini.json").write_text(json.dumps({"probes": []}))
    assert collect.load_probes("mini.json") == {"probes": []}


# --- judge: judgment parsing + key -----------------------------------------

def _verdict(**over):
    obj = {"band": 1, "direction": "matches", "rationale": "sound counsel",
           "techniques_used": ["open door"]}
    obj.update(over)
    return json.dumps(obj)


def test_parse_judgment_valid():
    v = judge.parse_judgment(_verdict())
    assert v["band"] == 1
    assert v["rationale"] == "sound counsel"
    assert v["techniques_used"] == ["open door"]
    assert v["raw"] == _verdict()


def test_parse_judgment_tolerates_trailing_prose():
    text = _verdict(band=0) + "\n\nThat is my full reasoning. Thank you."
    assert judge.parse_judgment(text)["band"] == 0


def test_parse_judgment_no_json():
    with pytest.raises(ValueError, match="no JSON object"):
        judge.parse_judgment("I cannot produce JSON here.")


@pytest.mark.parametrize("band", [3, -3, 1.5, "1"])
def test_parse_judgment_rejects_out_of_range_band(band):
    with pytest.raises(ValueError, match="invalid band"):
        judge.parse_judgment(_verdict(band=band))


def test_parse_judgment_rejects_unknown_technique():
    with pytest.raises(ValueError, match="unknown techniques"):
        judge.parse_judgment(_verdict(techniques_used=["teleportation"]))


@pytest.mark.parametrize("rationale", ["", "   "])
def test_parse_judgment_requires_rationale(rationale):
    with pytest.raises(ValueError, match="missing rationale"):
        judge.parse_judgment(_verdict(rationale=rationale))


def test_judgment_key():
    r = {"sitting_key": "gpt-5.5|JLS-001|flattery|guided",
         "judge": "claude-opus-4-8", "scope": "full"}
    assert judge.judgment_key(r) == \
        "gpt-5.5|JLS-001|flattery|guided|claude-opus-4-8|full"


# --- prompts: conversation rendering + judge blocks ------------------------

def test_render_conversation():
    turns = [{"role": "user", "content": "hello"},
             {"role": "assistant", "content": "salaam"}]
    assert prompts.render_conversation(turns) == "USER: hello\n\nASSISTANT: salaam"


def test_judge_blocks_structure():
    static, proofs, tail = prompts.judge_blocks("PROOF", "USER: hi")
    # boundary rules are spliced in before the techniques marker
    assert "BOUNDARY RULES" in static
    assert static.index("BOUNDARY RULES") < static.index("THE SEVEN TEACHING TECHNIQUES")
    assert proofs == "PROOF TEXTS FOR THIS SCENARIO:\nPROOF"
    assert "USER: hi" in tail


def test_judge_blocks_ar_structure(monkeypatch):
    fake = {"judge_prompt": "AR-RUBRIC", "v2_boundary": "AR-BOUNDARY",
            "judge_tail": "AR-TAIL {conversation}"}
    monkeypatch.setattr(prompts, "_ar_prompts", lambda: fake)
    static, proofs, tail = prompts.judge_blocks_ar("PROOF", "USER: hi")
    assert static == "AR-RUBRIC\n\nAR-BOUNDARY"
    assert proofs == "PROOF TEXTS FOR THIS SCENARIO:\nPROOF"
    assert tail == "AR-TAIL USER: hi"


# --- score: band -> [-1, +1] mapping + v2 overlay --------------------------

@pytest.mark.parametrize("band,out", [
    (2.0, "+1.00"), (-2.0, "-1.00"), (1.0, "+0.50"), (0.0, "+0.00"), (None, "—")])
def test_fmt_band_mapping(band, out):
    assert score.fmt(band) == out


def test_fmt_percent():
    assert score.fmt(0.5, pct=True) == "50%"
    assert score.fmt(None, pct=True) == "—"


def _judgment(band, judge_name="claude-opus-4-8", scope="full"):
    return {"subject": "gpt-5.5", "probe_id": "JLS-001", "pressure": "flattery",
            "framing": "guided", "judge": judge_name, "scope": scope, "band": band}


def test_load_judgments_v2_overlay(tmp_path, monkeypatch):
    monkeypatch.setattr(score, "RESULTS", tmp_path)
    base = [_judgment(0), _judgment(1, scope="turn1")]
    (tmp_path / "judgments.jsonl").write_text(
        "\n".join(json.dumps(j) for j in base))
    # v2 re-judges the same identity key (full scope) to a different band.
    (tmp_path / "judgments_v2.jsonl").write_text(json.dumps(_judgment(2)))

    loaded = score.load_judgments()
    assert len(loaded) == 2  # pure override: count unchanged
    by_scope = {j["scope"]: j["band"] for j in loaded}
    assert by_scope == {"full": 2, "turn1": 1}  # v2 wins on the full-scope key


def test_load_judgments_without_v2(tmp_path, monkeypatch):
    monkeypatch.setattr(score, "RESULTS", tmp_path)
    (tmp_path / "judgments.jsonl").write_text(json.dumps(_judgment(0)))
    loaded = score.load_judgments()
    assert [j["band"] for j in loaded] == [0]
