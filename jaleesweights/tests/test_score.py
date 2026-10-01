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


# --- against the released data (skipped until fetch_data has installed it) -------------

import re
import pytest
from typer.testing import CliRunner
from jaleesweights import paths


@pytest.mark.skipif(not (paths.REFERENCE / "judgments_eval_gemma.jsonl").exists()
                    or not (paths.BENCH_RESULTS / "judgments.jsonl").exists(),
                    reason="reference data not installed")
def test_score_reproduces_the_papers_main_table():
    """The paper's Table 1 as printed: scores and drops exact, Gemma after-pushback
    intervals exact (the paper prints them to two decimals; these are the three-decimal
    values they round from), paired point estimates exact and interval ends within 0.01."""
    out = CliRunner().invoke(score.app, []).output
    cells: dict[str, list] = {}
    for l in out.splitlines():
        m = re.match(r"  (.+?)\s{2,}([+-]\d\.\d{3}) \[([^\]]+)\]\s+([+-]\d\.\d{3}) \[([^\]]+)\]\s+([+-]\d\.\d{3})", l)
        if m:
            label, t1, t1_ci, full, full_ci, drop = m.groups()
            cells.setdefault(label.strip(), []).append({"t1": t1, "full": full, "full_ci": full_ci, "drop": drop})

    def row(label, i=0):
        c = cells[label][i]
        return c["t1"], c["full"], c["drop"]

    # Gemma (first occurrence of the shared labels), as the paper prints them
    assert row("Base, out of the box (same-stack control)") == ("-0.044", "-0.335", "-0.290")
    assert row("Stage 1: SFT") == ("+0.429", "+0.276", "-0.152")
    assert row("Stage 2: SFT + DPO") == ("+0.535", "+0.499", "-0.036")
    assert row("Base, with guide in context (main run)")[1:] == ("+0.569", "-0.167")
    assert row("Stage 1, with guide in context") == ("+0.829", "+0.802", "-0.026")
    # Inkling-Small (second occurrence)
    assert row("Base, out of the box") == ("+0.394", "+0.252", "-0.142")
    assert row("Stage 1: SFT", 1) == ("+0.524", "+0.550", "+0.026")
    assert row("Stage 2: SFT + DPO", 1)[1] == "+0.569"
    assert row("Base, with guide in context")[1:] == ("+0.817", "-0.004")
    assert row("Stage 1, with guide in context", 1)[1] == "+0.885"
    assert row("Inkling, best open base model bare (main run)") == ("+0.468", "+0.398", "-0.070")
    # the paper's Gemma after-pushback intervals: [-0.47,-0.20], [+0.12,+0.42], [+0.35,+0.63]
    assert cells["Base, out of the box (same-stack control)"][0]["full_ci"] == "-0.470,-0.199"
    assert cells["Stage 1: SFT"][0]["full_ci"] == "+0.124,+0.421"
    assert cells["Stage 2: SFT + DPO"][0]["full_ci"] == "+0.349,+0.632"

    def paired_line(title):
        i = out.index(title)
        return re.search(r"full\s+([+-]\d\.\d{3}) \[([+-]\d\.\d{3}),([+-]\d\.\d{3})\]\s+\(n=420; (\d+) cells up, (\d+) down\)", out[i:]).groups()

    g = paired_line("Gemma stage 2 vs stage 1")
    assert g[0] == "+0.223" and abs(float(g[1]) - 0.144) <= 0.01 and abs(float(g[2]) - 0.304) <= 0.01 and g[3:] == ("120", "34")
    s1 = paired_line("Inkling-Small stage 1 vs base")
    assert s1[0] == "+0.298" and abs(float(s1[1]) - 0.206) <= 0.01 and abs(float(s1[2]) - 0.392) <= 0.01 and s1[3:] == ("154", "37")
    s2 = paired_line("Inkling-Small stage 2 vs stage 1")
    assert s2[0] == "+0.019" and float(s2[1]) < 0 < float(s2[2])


def test_extra_arms_are_scored_from_their_own_file(tmp_path):
    rows = []
    for subj, band in (("demo-base", 0), ("demo-sft", 2)):
        for probe in ("JLS-002", "JLS-004"):
            for pr in ("p1", "p2"):
                for scope in ("turn1", "full"):
                    rows.append(judgment(subj, probe, pr, scope, band))
    extra = write(tmp_path / "extra.jsonl", rows)
    # the paper rows need the reference data; point them at the same small file so the command runs anywhere
    res = CliRunner().invoke(score.app, ["--gemma", str(extra), "--small", str(extra), "--main-run", str(extra),
                                         "--extra-judgments", str(extra), "--extra-subject", "demo-sft",
                                         "--extra-subject", "demo-base", "--extra-paired", "demo-sft:demo-base"])
    assert res.exit_code == 0, res.output
    assert "Your arms" in res.output and "demo-sft vs demo-base" in res.output
    assert "+1.000 [+1.000,+1.000]  (n=4; 4 cells up, 0 down)" in res.output
    res = CliRunner().invoke(score.app, ["--gemma", str(extra), "--small", str(extra), "--main-run", str(extra),
                                         "--extra-subject", "demo-sft"])
    assert res.exit_code != 0 and "need --extra-judgments" in res.output
