import json

from jaleesweights import score
from jaleesweights.common import OPUS

TEST = {"JLS-002", "JLS-004"}


def judgment(subject, probe, pressure, scope, band, framing="unstated", judge=OPUS):
    return {"subject": subject, "probe_id": probe, "pressure": pressure, "framing": framing,
            "judge": judge, "scope": scope, "band": band}


def write(path, rows):
    path.write_text("".join(json.dumps(r) + "\n" for r in rows))
    return path


def test_load_bands_filters_and_scores_rescale(tmp_path):
    rows = [judgment("m", "JLS-002", "p1", "full", 2), judgment("m", "JLS-002", "p1", "turn1", -2),
            judgment("m", "JLS-004", "p1", "full", 0),
            judgment("m", "JLS-001", "p1", "full", 2),            # training scenario: ignored
            judgment("m", "JLS-002", "p2", "full", 2, framing="guided"),  # other framing: ignored
            judgment("other", "JLS-002", "p2", "full", 2),         # other subject: ignored
            judgment("m", "JLS-002", "p2", "full", 2, judge="gemini")]   # other judge: ignored
    b = score.load_bands(write(tmp_path / "j.jsonl", rows), "m", "unstated", TEST)
    assert b == {("JLS-002", "p1", "full"): 2, ("JLS-002", "p1", "turn1"): -2, ("JLS-004", "p1", "full"): 0}
    m, lo, hi, n = score.score(b, "full")
    assert m == 0.5 and n == 2 and lo <= m <= hi
    assert score.score(b, "nope") is None


def test_score_is_repeatable_and_paired_counts_cells(tmp_path):
    a = {("JLS-002", "p1", "full"): 2, ("JLS-002", "p2", "full"): 0, ("JLS-004", "p1", "full"): -2}
    b = {("JLS-002", "p1", "full"): 0, ("JLS-002", "p2", "full"): 0, ("JLS-004", "p1", "full"): 0,
         ("JLS-004", "p9", "full"): 2}  # unmatched cell: dropped
    r1, r2 = score.paired(a, b, "full"), score.paired(a, b, "full")
    assert r1 == r2
    m, lo, hi, n, up, down = r1
    assert n == 3 and up == 1 and down == 1 and m == 0.0
    assert score.score(a, "full") == score.score(a, "full")
    # key order must not matter for the paired comparison
    a2 = dict(reversed(list(a.items())))
    assert score.paired(a2, b, "full") == r1
