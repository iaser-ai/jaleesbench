"""Web-export contract: index.json + per-probe shards (spec 3 §5).

Drives the exporter against a tiny synthetic results dir (never the 190 MB real
data) so the suite runs in CI. Covers shape, the −2…+2 → −1…+1 band rescale, the
judgments_v2 missing-rationale path, --limit, and idempotency.
"""

import gzip
import json

import pytest

from jaleesbench import export_web as ew
from jaleesbench import score


def _read_shard(out, pid):
    """Shards are gzip-compressed JSON on disk."""
    raw = (out / "probes" / f"{pid}.json.gz").read_bytes()
    return json.loads(gzip.decompress(raw))


# --- synthetic fixtures -----------------------------------------------------

def _sitting(subject, pid, pressure, framing):
    return {
        "subject": subject, "probe_id": pid, "pressure": pressure,
        "framing": framing, "model": subject, "context_prefix": None,
        "ts": "t", "attempts": [1, 1], "usage": [{"in": 1, "out": 1}],
        "turns": [
            {"role": "user", "content": f"Q-{pid}"},
            {"role": "assistant", "content": f"A1-{subject}"},
            {"role": "user", "content": f"PUSH-{pressure}"},
            {"role": "assistant", "content": f"A2-{subject}"},
        ],
    }


def _judgment(subject, pid, pressure, framing, judge, scope, band, rationale="sound"):
    j = {
        "sitting_key": f"{subject}|{pid}|{pressure}|{framing}",
        "subject": subject, "probe_id": pid, "pressure": pressure,
        "framing": framing, "judge": judge, "scope": scope, "ts": "t",
        "band": band, "direction": "verdict summary",
        "techniques_used": ["open door"], "usage": {"in": 1, "out": 1},
    }
    if rationale is not None:
        j["rationale"] = rationale
    return j


def _probe(pid, title):
    return {
        "id": pid, "title": title, "chapter": "Some chapter",
        "pillars": ["restraint"], "hearts": ["patience"], "islamic": "clean",
        "proof_texts": "PROOF", "turn1": "Q", "pressure_turns": {},
    }


JUDGES = ("claude-opus-4-8", "gemini-3.1-pro-preview")
PROBES = (("JLS-001", "The team message"), ("JLS-002", "Another probe"))


@pytest.fixture
def results_dir(tmp_path):
    """2 probes × 2 subjects × 1 pressure × 1 framing, judged by 2 judges at 2
    scopes. ansari scores Perfume (+2 native) after pressure, gpt-5.5 Burns (−2)."""
    sittings, judgments = [], []
    for pid, _ in PROBES:
        for subj in ("ansari", "gpt-5.5"):
            sittings.append(_sitting(subj, pid, "insistence", "unstated"))
            full_band = 2 if subj == "ansari" else -2
            for judge in JUDGES:
                judgments.append(_judgment(subj, pid, "insistence", "unstated",
                                           judge, "full", full_band))
                judgments.append(_judgment(subj, pid, "insistence", "unstated",
                                           judge, "turn1", 1))
    (tmp_path / "collect.jsonl").write_text(
        "\n".join(json.dumps(s) for s in sittings))
    (tmp_path / "judgments.jsonl").write_text(
        "\n".join(json.dumps(j) for j in judgments))
    return tmp_path


@pytest.fixture(autouse=True)
def fake_probes(monkeypatch):
    bank = {"version": 1, "pressures": ew.PRESSURES,
            "probes": [_probe(pid, title) for pid, title in PROBES]}
    monkeypatch.setattr(ew, "load_probes", lambda *a, **k: bank)


def _full_verdict(cell, judge):
    return next(v for v in cell["verdicts"]
                if v["scope"] == "full" and v["judge"] == judge)


# --- tests ------------------------------------------------------------------

def test_export_produces_index_and_shards(results_dir, tmp_path):
    out = tmp_path / "out"
    summary = ew.export_web(results_dir, out)

    index = json.loads((out / "index.json").read_text())
    assert index["contractVersion"] == "1.0"
    assert index["producer"]["name"] == "jaleesbench"
    assert index["dataset"]["language"] == "en"
    assert {s["id"] for s in index["subjects"]} == {"ansari", "gpt-5.5"}
    assert [a["key"] for a in index["conditionAxes"]] == ["pressure", "framing"]
    assert {j["id"] for j in index["judges"]} == set(JUDGES)
    assert index["scopes"][0] == {"id": "full", "label": "After pressure",
                                  "default": True}
    assert {it["id"] for it in index["items"]} == {"JLS-001", "JLS-002"}
    assert index["shards"]["JLS-001"] == "probes/JLS-001.json.gz"
    assert summary["probes"] == 2

    shard = _read_shard(out, "JLS-001")
    assert shard["item"]["id"] == "JLS-001"
    assert shard["item"]["tags"]["islamic"] == "clean"
    assert shard["item"]["context"] == "PROOF"
    assert len(shard["cells"]) == 2  # 2 subjects
    cell = next(c for c in shard["cells"] if c["subject"] == "ansari")
    assert cell["conditions"] == {"pressure": "insistence", "framing": "unstated"}
    assert [t["role"] for t in cell["transcript"]] == \
        ["user", "assistant", "user", "assistant"]
    assert len(cell["verdicts"]) == 4  # 2 judges × 2 scopes


def test_band_rescale_and_label(results_dir, tmp_path):
    out = tmp_path / "out"
    ew.export_web(results_dir, out)

    index = json.loads((out / "index.json").read_text())
    assert [b["value"] for b in index["bands"]] == [-1.0, -0.5, 0.0, 0.5, 1.0]
    assert index["bands"][-1] == {"value": 1.0, "label": "Perfume",
                                  "color": "#1a6840"}

    shard = _read_shard(out, "JLS-001")
    ansari = next(c for c in shard["cells"] if c["subject"] == "ansari")
    gpt = next(c for c in shard["cells"] if c["subject"] == "gpt-5.5")
    v_ansari = _full_verdict(ansari, "claude-opus-4-8")
    v_gpt = _full_verdict(gpt, "claude-opus-4-8")
    assert (v_ansari["band"], v_ansari["bandLabel"]) == (1.0, "Perfume")
    assert (v_gpt["band"], v_gpt["bandLabel"]) == (-1.0, "Burns")
    assert v_ansari["tags"]["techniques"] == ["open door"]
    assert v_ansari["summary"] == "verdict summary"


def test_v2_overlay_missing_rationale_tolerated(results_dir, tmp_path):
    # v2 re-judges one cell (full scope) with NO rationale — the override wins
    # and the exported verdict must simply omit `rationale`, not error.
    v2 = _judgment("ansari", "JLS-001", "insistence", "unstated",
                   "claude-opus-4-8", "full", 2, rationale=None)
    (results_dir / "judgments_v2.jsonl").write_text(json.dumps(v2))

    out = tmp_path / "out"
    ew.export_web(results_dir, out)
    shard = _read_shard(out, "JLS-001")
    ansari = next(c for c in shard["cells"] if c["subject"] == "ansari")
    verdict = _full_verdict(ansari, "claude-opus-4-8")
    assert "rationale" not in verdict
    assert verdict["summary"] == "verdict summary"  # still has direction


def test_limit_exports_first_n_probes(results_dir, tmp_path):
    out = tmp_path / "out"
    summary = ew.export_web(results_dir, out, limit=1)
    assert summary["probes"] == 1
    index = json.loads((out / "index.json").read_text())
    assert [it["id"] for it in index["items"]] == ["JLS-001"]
    assert (out / "probes" / "JLS-001.json.gz").exists()
    assert not (out / "probes" / "JLS-002.json.gz").exists()


def test_export_is_idempotent(results_dir, tmp_path):
    # gzip mtime=0 keeps the compressed bytes byte-identical across runs.
    a, b = tmp_path / "a", tmp_path / "b"
    ew.export_web(results_dir, a)
    ew.export_web(results_dir, b)
    assert (a / "index.json").read_bytes() == (b / "index.json").read_bytes()
    assert (a / "probes" / "JLS-001.json.gz").read_bytes() == \
        (b / "probes" / "JLS-001.json.gz").read_bytes()


def test_unexpected_band_fails_loud(results_dir, tmp_path):
    bad = _judgment("ansari", "JLS-001", "insistence", "unstated",
                    "claude-opus-4-8", "full", 5)
    (results_dir / "judgments_v2.jsonl").write_text(json.dumps(bad))
    with pytest.raises(ValueError, match="unexpected band"):
        ew.export_web(results_dir, tmp_path / "out")


# --- loader refactor: the new results_path param ----------------------------

def test_load_judgments_accepts_results_path(tmp_path):
    j = _judgment("gpt-5.5", "JLS-001", "flattery", "guided",
                  "claude-opus-4-8", "full", 1)
    (tmp_path / "judgments.jsonl").write_text(json.dumps(j))
    loaded = score.load_judgments(results_path=tmp_path)
    assert [r["band"] for r in loaded] == [1]
