"""Recompute every reported JaleesBench number with a probe-cluster bootstrap
95% CI, and dump to results/paper_stats.json for the paper's tables + figures.

Run: uv run python -m jaleesbench.paper_stats
Requires the collected results files (judgments.jsonl, judgments_v2.jsonl,
judgments_ansari_mod.jsonl, judgments_thinking.jsonl, citations_turn1.jsonl)
in results/ — these are not shipped; the emitted paper_stats.json is.

Resampling unit: the PROBE (140 clusters).
One draw resamples 140 probes with replacement; for the chosen probes we carry
ALL their bands for the selected slice together, pool, take the mean band, then
x0.5 to the reported -1..+1 scale. Paired quantities (recognition gap,
instruction gap, steadfastness) are computed on the SAME resampled probe set
per draw so the CI accounts for correlation.

Judgments are loaded via score.load_judgments() so the v2 re-judge overlay is
applied (matches the published scorecard). Seed fixed for reproducibility.
"""
import json
from collections import defaultdict
from itertools import combinations
from pathlib import Path

import numpy as np

from jaleesbench import score
from jaleesbench.collect import RESULTS, load_probes

SCORE_SCALE = 0.5
N_BOOT = 5000
SEED = 12345

SUBJECTS = ["ansari", "gpt-5.5", "claude-sonnet-5", "inkling",
            "claude-sonnet-4-6", "glm-5.1",
            "nemotron-3-ultra", "gemini-3.5-flash", "gemma-4-31b", "qwen3-235b"]
PRESSURES = ["secularize", "insistence", "false_authority", "good_cause",
             "flattery", "personal_appeal"]
FRAMINGS = ["unstated", "stated", "guided"]
CLASSES = ["clean", "leaky", "intrinsic"]  # not-Islamic / names-Islam / intrinsic

rng = np.random.default_rng(SEED)


# ---- load judgments (v2 overlay) -> per (subject, slice) probe->bands ----
judgments = score.load_judgments()
probes_meta = {p["id"]: p for p in load_probes()["probes"]}
ALL_PROBES = sorted(probes_meta)
N = len(ALL_PROBES)
pidx = {p: i for i, p in enumerate(ALL_PROBES)}

# bands[(subject, framing, scope, pressure)] -> per-probe sum/count arrays
def empty():
    return [np.zeros(N), np.zeros(N)]  # sum, count

agg = defaultdict(empty)
for j in judgments:
    s, p, pr, f, sc = j["subject"], j["probe_id"], j["pressure"], j["framing"], j["scope"]
    i = pidx[p]
    for key in [(s, f, sc, None), (s, f, sc, pr)]:  # pooled-over-pressure and per-pressure
        a = agg[key]
        a[0][i] += j["band"]
        a[1][i] += 1


# Fold in the two follow-up tracks (same schema, distinct subject names) so the
# case-study (ansari-steadfast) and reasoning (*-thinking) numbers get CIs too.
for fname in ["judgments_ansari_mod.jsonl", "judgments_thinking.jsonl"]:
    for l in (RESULTS / fname).read_text().splitlines():
        j = json.loads(l)
        i = pidx[j["probe_id"]]
        for key in [(j["subject"], j["framing"], j["scope"], None),
                    (j["subject"], j["framing"], j["scope"], j["pressure"])]:
            a = agg[key]
            a[0][i] += j["band"]
            a[1][i] += 1


def draws():
    """Yield N_BOOT index arrays (each a resample of probe indices)."""
    for _ in range(N_BOOT):
        yield rng.integers(0, N, N)


# Pre-generate one shared set of resample index arrays so paired quantities use
# identical probe draws within a single pass.
RESAMPLES = [rng.integers(0, N, N) for _ in range(N_BOOT)]


def point_and_ci(sumc):
    """(point, lo, hi) on the reported scale for a (sum,count) per-probe pair."""
    s, c = sumc
    tot_c = c.sum()
    if tot_c == 0:
        return None
    point = s.sum() / tot_c * SCORE_SCALE
    boots = np.array([s[idx].sum() / c[idx].sum() * SCORE_SCALE for idx in RESAMPLES])
    lo, hi = np.percentile(boots, [2.5, 97.5])
    return [round(point, 3), round(lo, 3), round(hi, 3)]


def diff_ci(sumc_a, sumc_b):
    """CI on (mean_a - mean_b), paired on the same resampled probes."""
    sa, ca = sumc_a
    sb, cb = sumc_b
    if ca.sum() == 0 or cb.sum() == 0:
        return None
    point = (sa.sum() / ca.sum() - sb.sum() / cb.sum()) * SCORE_SCALE
    boots = np.array([(sa[idx].sum() / ca[idx].sum()
                       - sb[idx].sum() / cb[idx].sum()) * SCORE_SCALE
                      for idx in RESAMPLES])
    lo, hi = np.percentile(boots, [2.5, 97.5])
    return [round(point, 3), round(lo, 3), round(hi, 3)]


out = {"meta": {"n_boot": N_BOOT, "seed": SEED, "n_probes": N,
                "n_judgments": len(judgments), "scale": "-1..+1"}}

# ---- Jalees Score by framing (scorecard = unstated/full; staircase = all) ----
out["jalees_by_framing"] = {
    s: {f: point_and_ci(agg[(s, f, "full", None)]) for f in FRAMINGS}
    for s in SUBJECTS
}

# ---- recognition gap (stated - unstated), instruction gap (guided - stated) ----
out["recognition_gap"] = {
    s: diff_ci(agg[(s, "stated", "full", None)], agg[(s, "unstated", "full", None)])
    for s in SUBJECTS
}
out["instruction_gap"] = {
    s: diff_ci(agg[(s, "guided", "full", None)], agg[(s, "stated", "full", None)])
    for s in SUBJECTS
}

# ---- steadfastness (full - turn1, unstated): pooled and per-pressure ----
out["steadfastness_pooled"] = {
    s: diff_ci(agg[(s, "unstated", "full", None)], agg[(s, "unstated", "turn1", None)])
    for s in SUBJECTS
}
out["steadfastness_by_pressure"] = {
    s: {pr: diff_ci(agg[(s, "unstated", "full", pr)], agg[(s, "unstated", "turn1", pr)])
        for pr in PRESSURES}
    for s in SUBJECTS
}

# ---- Ansari layer contrast (Ansari unstated full - Gemini 3.5 Flash) ----
out["ansari_layer_gap"] = diff_ci(agg[("ansari", "unstated", "full", None)],
                                   agg[("gemini-3.5-flash", "unstated", "full", None)])

# ---- citation rate by class x framing (turn-1; cite = quran OR hadith) ----
cit_rows = [json.loads(l) for l in (RESULTS / "citations_turn1.jsonl").read_text().splitlines()]
# per (subject, framing): per-probe (sum cites, count sittings)
cit_agg = defaultdict(empty)
for r in cit_rows:
    i = pidx[r["probe_id"]]
    cited = 1.0 if (r["quran"] or r["hadith"]) else 0.0
    a = cit_agg[(r["subject"], r["framing"])]
    a[0][i] += cited
    a[1][i] += 1

CLASS_PROBES = {c: np.array([pidx[p] for p, m in probes_meta.items() if m["islamic"] == c])
                for c in CLASSES}


def cit_point_ci(subject, framing, klass):
    s, c = cit_agg[(subject, framing)]
    sel = CLASS_PROBES[klass]
    tot = c[sel].sum()
    if tot == 0:
        return None
    point = s[sel].sum() / tot
    # bootstrap resampling probes WITHIN the class
    k = len(sel)
    boots = []
    for _ in range(N_BOOT):
        idx = sel[rng.integers(0, k, k)]
        boots.append(s[idx].sum() / c[idx].sum())
    lo, hi = np.percentile(boots, [2.5, 97.5])
    return [round(point, 3), round(lo, 3), round(hi, 3)]


out["citation_by_class"] = {
    s: {f: {c: cit_point_ci(s, f, c) for c in CLASSES} for f in ["unstated", "stated"]}
    for s in SUBJECTS
}

# ---- judge agreement (exact / within-one), bootstrap over probes ----
# per-probe: counts of (pairs, exact, within1) over all dual-judged cells
by_cell = defaultdict(list)
for j in judgments:
    by_cell[(j["subject"], j["probe_id"], j["pressure"], j["framing"], j["scope"])].append(j)
pp = np.zeros(N)
pe = np.zeros(N)
pw = np.zeros(N)
for (s, p, pr, f, sc), js in by_cell.items():
    i = pidx[p]
    for a, b in combinations(js, 2):
        d = abs(a["band"] - b["band"])
        pp[i] += 1
        pe[i] += (d == 0)
        pw[i] += (d <= 1)
exact_pt = pe.sum() / pp.sum()
within_pt = pw.sum() / pp.sum()
be, bw = [], []
for idx in RESAMPLES:
    be.append(pe[idx].sum() / pp[idx].sum())
    bw.append(pw[idx].sum() / pp[idx].sum())
out["judge_agreement"] = {
    "exact": [round(exact_pt, 3), *[round(x, 3) for x in np.percentile(be, [2.5, 97.5])]],
    "within1": [round(within_pt, 3), *[round(x, 3) for x in np.percentile(bw, [2.5, 97.5])]],
    "n_pairs": int(pp.sum()),
}

# ---- case study: amended Ansari (ansari-steadfast), full bank ----
WEAK = ["secularize", "insistence", "personal_appeal"]  # the pressures it was tuned for
out["casestudy"] = {
    "weak_pressures": WEAK,
    "baseline_jalees_unstated": out["jalees_by_framing"]["ansari"]["unstated"],
    "amended_jalees_unstated": point_and_ci(agg[("ansari-steadfast", "unstated", "full", None)]),
    "baseline_steadfastness_pooled": out["steadfastness_pooled"]["ansari"],
    "amended_steadfastness_pooled": diff_ci(agg[("ansari-steadfast", "unstated", "full", None)],
                                            agg[("ansari-steadfast", "unstated", "turn1", None)]),
    "baseline_steadfastness_by_pressure": {
        pr: out["steadfastness_by_pressure"]["ansari"][pr] for pr in PRESSURES},
    "amended_steadfastness_by_pressure": {
        pr: diff_ci(agg[("ansari-steadfast", "unstated", "full", pr)],
                    agg[("ansari-steadfast", "unstated", "turn1", pr)]) for pr in PRESSURES},
}

# ---- reasoning-mode robustness: thinking variants vs baselines ----
THINK = {"claude-sonnet-thinking": "claude-sonnet-4-6",
         "gemma-4-thinking": "gemma-4-31b", "glm-thinking": "glm-5.1"}
out["reasoning"] = {
    t: {"thinking": point_and_ci(agg[(t, "unstated", "full", None)]),
        "baseline": out["jalees_by_framing"][base]["unstated"]}
    for t, base in THINK.items()
}

(RESULTS / "paper_stats.json").write_text(json.dumps(out, indent=2))
print(f"wrote {RESULTS / 'paper_stats.json'}")

# ---- console sanity check vs the paper's published point estimates ----
print("\nJalees Score (Unstated, full) — should match scorecard:")
for s in SUBJECTS:
    pt, lo, hi = out["jalees_by_framing"][s]["unstated"]
    print(f"  {s:<20} {pt:+.2f}  [{lo:+.2f}, {hi:+.2f}]")
print(f"\nAnsari-layer gap (vs Gemini 3.5 Flash): {out['ansari_layer_gap']}")
print(f"Judge agreement exact={out['judge_agreement']['exact']} "
      f"within1={out['judge_agreement']['within1']}")
print("\nCitation (Unstated) Ansari/GPT — should match Table 2 (97/96/96, 3/12/42):")
for s in ["ansari", "gpt-5.5"]:
    row = out["citation_by_class"][s]["unstated"]
    print(f"  {s:<10} " + "  ".join(f"{c}={row[c][0]:.0%}" for c in CLASSES))
