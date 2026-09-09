"""JaleesBench-Mini (experiment 24): estimands, criteria, coverage constraints,
selection methods, and validation plumbing on a small synthetic bank. One
real-data test checks the full-bench references against the published
paper_stats.json and skips when the judgment files are not present."""

import json
import os
from pathlib import Path

import numpy as np
import pytest

from jaleesbench import mini
from jaleesbench.collect import RESULTS

# --- synthetic bank ----------------------------------------------------------

N = 24
PROBE_IDS = [f"P-{i:03d}" for i in range(N)]
CLASSES = ["clean"] * 10 + ["leaky"] * 8 + ["intrinsic"] * 6
PILLAR_SETS = [
    ["restraint"], ["justice"], ["patience"], ["courage"], ["cross_cutting"],
    ["restraint", "justice"], ["patience", "courage"], ["cross_cutting", "restraint"],
] * 3
META = {p: {"id": p, "islamic": c, "pillars": ps}
        for p, c, ps in zip(PROBE_IDS, CLASSES, PILLAR_SETS)}
SUBJECTS = ["alpha", "beta", "gamma"]
JUDGES = ["j1", "j2"]
PRESSURES = mini.PRESSURES


def band_for(subject, i, framing, scope, judge):
    """Deterministic bands: subject offset + probe wave + framing/scope lift."""
    base = {"alpha": 1, "beta": 0, "gamma": -1}[subject]
    wave = 1 if i % 3 == 0 else (-1 if i % 3 == 1 else 0)
    lift = {"unstated": 0, "stated": 1, "guided": 1}[framing]
    turn = 0 if scope == "full" else (1 if i % 2 else 0)
    j = 0 if judge == "j1" else (1 if i % 5 == 0 else 0)
    return int(np.clip(base + wave + lift + turn + j, -2, 2))


def synth(subjects=SUBJECTS, framings=("unstated", "stated", "guided"), missing_stated_for=()):
    rows = []
    for s in subjects:
        for i, p in enumerate(PROBE_IDS):
            for pr in PRESSURES:
                for f in framings:
                    if s in missing_stated_for and f != "unstated":
                        continue
                    for sc in ("full", "turn1"):
                        for j in JUDGES:
                            rows.append({"subject": s, "probe_id": p, "pressure": pr,
                                         "framing": f, "scope": sc, "judge": j,
                                         "band": band_for(s, i, f, sc, j)})
    return rows


@pytest.fixture(scope="module")
def table():
    return mini.build_table(synth(missing_stated_for=("gamma",)), PROBE_IDS)


# --- table / estimands --------------------------------------------------------

def test_score_is_pooled_mean_band_times_scale(table):
    rows = [r for r in synth() if r["subject"] == "alpha" and r["framing"] == "unstated"
            and r["scope"] == "full"]
    expect = np.mean([r["band"] for r in rows]) * mini.SCORE_SCALE
    assert table.score("alpha", "unstated", "full") == pytest.approx(expect)
    # restricted to a probe subset
    sub = [0, 1, 2]
    rows_sub = [r for r in rows if r["probe_id"] in {PROBE_IDS[i] for i in sub}]
    expect_sub = np.mean([r["band"] for r in rows_sub]) * mini.SCORE_SCALE
    assert table.score("alpha", "unstated", "full", sub) == pytest.approx(expect_sub)


def test_score_by_judge_and_pressure(table):
    rows = [r for r in synth() if r["subject"] == "beta" and r["framing"] == "unstated"
            and r["scope"] == "full" and r["judge"] == "j2" and r["pressure"] == "flattery"]
    expect = np.mean([r["band"] for r in rows]) * mini.SCORE_SCALE
    assert table.score("beta", "unstated", "full", None, "j2", "flattery") == pytest.approx(expect)


def test_estimands_and_missing_framing(table):
    e = mini.estimands(table, "alpha")
    assert e["E3"] == pytest.approx(e["E1"] - table.score("alpha", "unstated", "turn1"))
    assert e["E4_stated"] > e["E1"]  # stated lift in the synthetic bands
    g = mini.estimands(table, "gamma")
    assert g["E1"] is not None and g["E3"] is not None
    assert g["E4_stated"] is None and g["E4_guided"] is None
    assert table.score("nobody", "unstated", "full") is None


def test_judges_listed(table):
    assert table.judges() == ["j1", "j2"]


# --- criteria -------------------------------------------------------------------

def test_ranking_check_separated_pairs_only():
    full = {"a": 0.40, "b": 0.35, "c": -0.20}
    # a/b are within 0.10: swapping them is allowed; c stays below both
    ok = mini.ranking_check(full, {"a": 0.34, "b": 0.36, "c": -0.10})
    assert ok["n_separated_pairs"] == 2 and ok["discordant_pairs"] == [] and ok["tau_separated"] == 1.0
    assert ok["sign_flips"] == []
    bad = mini.ranking_check(full, {"a": 0.40, "b": -0.05, "c": 0.02})
    assert bad["sign_flips"] == ["b", "c"]
    assert bad["discordant_pairs"] == [["b", "c"]]
    assert bad["tau_separated"] == pytest.approx(0.0)


def test_evaluate_threshold_boundary_and_missing():
    full = {"a": {"E1": 0.30, "E3": -0.10, "E4_stated": 0.5, "E4_guided": 0.7},
            "b": {"E1": -0.30, "E3": -0.20, "E4_stated": None, "E4_guided": None}}
    near = {"a": {"E1": 0.35, "E3": -0.10, "E4_stated": 0.5, "E4_guided": 0.7},
            "b": {"E1": -0.30, "E3": -0.25, "E4_stated": None, "E4_guided": None}}
    ev = mini.evaluate(full, near)
    assert ev["pass"] and ev["worst_abs_err"] == pytest.approx(0.05)
    assert ev["max_err"]["E4_stated"] == pytest.approx(0.0)
    assert ev["errors"]["b"]["E4_stated"] is None
    far = {**near, "a": {**near["a"], "E4_guided": 0.76}}
    assert not mini.evaluate(full, far)["pass"]


# --- coverage -------------------------------------------------------------------

def test_coverage_bounds_and_satisfied():
    cov = mini.Coverage(META, PROBE_IDS, k=12)
    # shares 10/24, 8/24, 6/24 -> +-10pp at k=12
    assert cov.lo.tolist() == [4, 3, 2] and cov.hi.tolist() == [6, 5, 4]
    good = [0, 1, 2, 3, 4, 10, 11, 12, 13, 18, 19, 20]  # 5 clean, 4 leaky, 3 intrinsic, all pillars
    ok, detail = cov.satisfied(good)
    assert ok and all(detail["pillars_covered"].values())
    too_many_clean = list(range(7)) + [10, 11, 12, 18, 19]
    assert not cov.satisfied(too_many_clean)[0]
    assert not cov.satisfied(good[:-1])[0]  # wrong size


def test_feasible_additions_respects_upper_bound_and_chosen():
    cov = mini.Coverage(META, PROBE_IDS, k=12)
    chosen = [0, 1, 2, 3, 4, 5]  # 6 clean = at the upper bound
    feas = cov.feasible_additions(chosen)
    assert not feas[6] and not feas[0]        # another clean, or an already-chosen probe
    assert feas[10] and feas[18]              # leaky / intrinsic still fine
    # k=6 -> bounds clean [2,3], leaky [2,2], intrinsic [1,2]. After four picks
    # covering restraint/patience/courage, two slots remain: justice and
    # cross_cutting must both still be reachable.
    cov2 = mini.Coverage(META, PROBE_IDS, k=6)
    assert cov2.lo.tolist() == [2, 2, 1] and cov2.hi.tolist() == [3, 2, 2]
    feas2 = cov2.feasible_additions([0, 10, 11, 18])
    assert not feas2[12]                      # third leaky: over the upper bound
    assert not feas2[3]                       # courage only: two pillars left, one slot after
    assert feas2[4] and feas2[5]              # cross_cutting / restraint+justice: fine
    feas3 = cov2.feasible_additions([0, 10, 11, 18, 4])
    assert feas3[1] and feas3[21]             # justice via clean or intrinsic
    assert not feas3[13]                      # justice via a third leaky: no


# --- selection ------------------------------------------------------------------

def test_greedy_is_deterministic_and_feasible(table):
    cov = mini.Coverage(META, PROBE_IDS, k=10)
    a = mini.greedy_select(table, SUBJECTS, 10, cov)
    b = mini.greedy_select(table, SUBJECTS, 10, cov)
    assert a == b and len(set(a)) == 10
    assert cov.satisfied(a)[0]
    full = {s: mini.estimands(table, s) for s in SUBJECTS}
    ev = mini.evaluate(full, {s: mini.estimands(table, s, a) for s in SUBJECTS})
    # greedy on a 24-probe bank must beat the median random draw
    rng = np.random.default_rng(0)
    rand = [mini.evaluate(full, {s: mini.estimands(table, s, mini.random_draw(rng, 10, N))
                                 for s in SUBJECTS})["worst_abs_err"] for _ in range(50)]
    assert ev["worst_abs_err"] <= np.median(rand)


def test_greedy_objective_uses_training_subjects_only(table):
    cov = mini.Coverage(META, PROBE_IDS, k=8)
    on_two = mini.greedy_select(table, ["alpha", "beta"], 8, cov)
    specs = mini._specs(table, ["alpha", "beta"])
    assert len(specs) == 8  # 2 subjects x 4 defined estimands
    assert mini.max_dev(specs, on_two) < 0.5
    gamma_specs = mini._specs(table, ["gamma"])
    assert len(gamma_specs) == 2  # stated/guided undefined -> skipped


def test_greedy_raises_when_constraints_impossible(table):
    cov = mini.Coverage(META, PROBE_IDS, k=2)   # lower bounds sum to 3 > 2
    with pytest.raises(RuntimeError):
        mini.greedy_select(table, SUBJECTS, 2, cov)


def test_stratified_draw_is_proportional():
    strata = mini.strata_of(META, PROBE_IDS)
    rng = np.random.default_rng(1)
    counts = np.zeros(3)
    for _ in range(300):
        idx = mini.stratified_draw(rng, strata, 12, N)
        assert len(idx) == 12 and len(set(idx.tolist())) == 12
        classes = [CLASSES[i] for i in idx]
        counts += [classes.count(c) for c in mini.CLASSES]
    # proportional in expectation (5 / 4 / 3 at k=12), ties broken at random
    assert np.allclose(counts / 300, [5, 4, 3], atol=0.5)


def test_random_draw_size_and_uniqueness():
    idx = mini.random_draw(np.random.default_rng(2), 7, N)
    assert len(idx) == 7 and len(set(idx.tolist())) == 7


def test_anneal_never_worse_than_start(table):
    cov = mini.Coverage(META, PROBE_IDS, k=10)
    start = mini.greedy_select(table, SUBJECTS, 10, cov)
    best, dev, trace = mini.anneal(table, SUBJECTS, 10, cov, start, np.random.default_rng(3), iters=300)
    assert dev <= trace["start_dev"] and cov.satisfied(best)[0] and len(best) == 10


def test_milp_matches_or_beats_greedy(table):
    pytest.importorskip("scipy")
    cov = mini.Coverage(META, PROBE_IDS, k=10)
    g = mini.greedy_select(table, SUBJECTS, 10, cov)
    specs = mini._specs(table, SUBJECTS)
    idx, t_opt, status, exact = mini.milp_select(table, SUBJECTS, 10, cov, time_limit=60)
    assert idx is not None and len(idx) == 10 and cov.satisfied(idx)[0]
    assert exact <= mini.max_dev(specs, g) + 1e-9   # equal counts -> linearization exact


# --- validation ----------------------------------------------------------------

def test_loo_folds_and_prediction_vector(table):
    cov = mini.Coverage(META, PROBE_IDS, k=10)
    ev, folds = mini.loo_greedy(table, SUBJECTS, 10, cov)
    assert set(folds) == set(SUBJECTS) and all(len(v) == 10 for v in folds.values())
    assert set(ev["errors"]) == set(SUBJECTS)
    assert ev["errors"]["gamma"]["E4_stated"] is None
    assert isinstance(ev["pass"], bool)


def test_draw_stats_fields(table):
    rng = np.random.default_rng(4)
    draws = [mini.random_draw(rng, 10, N) for _ in range(20)]
    st = mini.draw_stats(table, SUBJECTS, 10, draws)
    assert st["n_draws"] == 20 and 0 <= st["pass_rate"] <= 1
    assert st["worst_abs_err_p90"] >= st["worst_abs_err_median"]
    assert set(st["max_err_median"]) == set(mini.ESTIMANDS)


def test_bootstrap_ci_contains_point_and_widens_for_mini(table):
    rng = np.random.default_rng(5)
    b_full = mini.bootstrap(table, "alpha", None, rng, 300)
    b_mini = mini.bootstrap(table, "alpha", list(range(8)), rng, 300)
    for e in mini.ESTIMANDS:
        assert b_full[e]["lo"] <= b_full[e]["point"] <= b_full[e]["hi"]
    assert b_mini["E1"]["half_width"] >= b_full["E1"]["half_width"]
    assert mini.bootstrap(table, "gamma", None, rng, 50)["E4_stated"] is None


def test_spearman():
    assert mini.spearman([1, 2, 3, 4], [10, 20, 30, 40]) == pytest.approx(1.0)
    assert mini.spearman([1, 2, 3, 4], [4, 3, 2, 1]) == pytest.approx(-1.0)


# --- real data (skips without the judgment files) ------------------------------

REAL = Path(os.environ.get("JALEESBENCH_RESULTS", RESULTS))


@pytest.mark.skipif(not (REAL / "judgments.jsonl").exists(), reason="judgment files not present")
def test_full_bench_references_match_paper_stats():
    from jaleesbench import score as score_mod
    from jaleesbench.collect import load_probes
    probe_ids = [p["id"] for p in load_probes()["probes"]]
    table = mini.build_table(score_mod.load_judgments(REAL), probe_ids)
    ps = json.loads((REAL / "paper_stats.json").read_text())
    for s in mini.SELECTION_SUBJECTS:
        if s not in ps["jalees_by_framing"]:
            continue
        e = mini.estimands(table, s)
        assert round(e["E1"], 3) == ps["jalees_by_framing"][s]["unstated"][0]
        if ps["jalees_by_framing"][s]["stated"] is not None:
            assert round(e["E4_stated"], 3) == ps["jalees_by_framing"][s]["stated"][0]
        assert round(e["E3"], 3) == pytest.approx(ps["steadfastness_pooled"][s][0], abs=0.001)
