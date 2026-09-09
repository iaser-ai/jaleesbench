"""JaleesBench-Mini: select and validate a fixed probe subset that reproduces
the full-bench estimands for a subject it has never seen (experiment 24,
issue #24). Preregistered hypothesis and criteria:
codev/specs/24-jaleesbench-mini-disciplined-p.md.

Offline: reads existing judgment files, never calls a provider. Every number
in the experiment notes and the mini paper comes from the JSON `run` writes.

    uv run --directory jaleesbench python -m jaleesbench.mini run --results /abs/results
    uv run --directory jaleesbench python -m jaleesbench.mini score --results /abs/results --subject NAME

Estimands (reported -1..+1 scale; pooled mean band over the slice x 0.5, the
paper_stats convention):
    E1  headline           unstated/full
    E3  steadfastness      unstated/full - unstated/turn1
    E4  framing staircase  stated/full and guided/full
    E2  ranking/sign       sign of E1; pairwise order of E1 on pairs the full
                           bench separates by > SEPARATION
"""

import json
import math
import time
from collections import defaultdict
from itertools import combinations
from pathlib import Path

import numpy as np
import typer

from . import score as score_mod
from .collect import DATA, RESULTS, load_probes

SCORE_SCALE = 0.5
SEED = 20260909          # selection / random draws / annealing
BOOT_SEED = 12345        # bootstrap (same as paper_stats)
N_BOOT = 5000
N_DRAWS = 1000
THRESHOLD = 0.05         # max |mini - full| on every estimand
SEPARATION = 0.10        # pairs the full bench separates by more than this must keep order
CLASS_TOL = 0.10         # +-10 percentage points around the bank's class shares
K_GRID = [20, 25, 30, 35, 40, 45, 50, 55, 60, 65, 70, 75, 80, 85, 90, 95, 100, 110, 120]
H1_MAX_K = 70

PILLARS = ["restraint", "cross_cutting", "justice", "patience", "courage"]
CLASSES = ["clean", "leaky", "intrinsic"]
PRESSURES = ["secularize", "insistence", "false_authority", "good_cause",
             "flattery", "personal_appeal"]
ESTIMANDS = ["E1", "E3", "E4_stated", "E4_guided"]
SLICES = {"E1": ("unstated", "full"), "E4_stated": ("stated", "full"),
          "E4_guided": ("guided", "full")}
TURN1 = ("unstated", "turn1")

# The 12 subjects with unstated/full data in the main run (10 paper subjects +
# the Fanar pair). Selection and leave-one-subject-out use exactly these.
SELECTION_SUBJECTS = ["ansari", "gpt-5.5", "claude-sonnet-5", "inkling",
                      "claude-sonnet-4-6", "glm-5.1", "nemotron-3-ultra",
                      "gemini-3.5-flash", "gemma-4-31b", "qwen3-235b",
                      "fanar", "fanar-sadiq"]
# Follow-up-track variants with full 140-probe data, never used in selection.
VARIANT_FILES = ["judgments_ansari_mod.jsonl", "judgments_thinking.jsonl"]
# Subjects present in both the Arabic and English runs (paper: rho = 0.83).
AR_SHARED = ["ansari", "gpt-5.5", "claude-sonnet-4-6", "gemma-4-31b",
             "nemotron-3-ultra", "gemini-3.5-flash", "qwen3-235b", "glm-5.1"]

MINI_PATH = DATA / "mini_v1.json"


# --------------------------------------------------------------------------
# Aggregate table: per (subject, framing, scope, judge|None, pressure|None)
# a (2, n_probes) array of band sums and counts.
# --------------------------------------------------------------------------

class Table:
    def __init__(self, probe_ids):
        self.probes = list(probe_ids)
        self.n = len(self.probes)
        self.pidx = {p: i for i, p in enumerate(self.probes)}
        self.agg = {}
        self.subjects = []

    def add(self, j):
        i = self.pidx[j["probe_id"]]
        if j["subject"] not in self.subjects:
            self.subjects.append(j["subject"])
        for judge in (None, j["judge"]):
            for pr in (None, j["pressure"]):
                key = (j["subject"], j["framing"], j["scope"], judge, pr)
                a = self.agg.get(key)
                if a is None:
                    a = self.agg[key] = np.zeros((2, self.n))
                a[0, i] += j["band"]
                a[1, i] += 1

    def slice(self, subject, framing, scope, judge=None, pressure=None):
        return self.agg.get((subject, framing, scope, judge, pressure))

    def score(self, subject, framing, scope, idx=None, judge=None, pressure=None):
        """Pooled mean band over the slice restricted to probes `idx`
        (None = all), on the reported scale. None if the slice is empty."""
        a = self.slice(subject, framing, scope, judge, pressure)
        if a is None:
            return None
        s, c = (a[0], a[1]) if idx is None else (a[0][idx], a[1][idx])
        tot = c.sum()
        if tot == 0:
            return None
        return float(s.sum() / tot * SCORE_SCALE)

    def judges(self):
        return sorted({k[3] for k in self.agg if k[3] is not None})


def build_table(judgments, probe_ids):
    t = Table(probe_ids)
    for j in judgments:
        t.add(j)
    return t


def read_jsonl(path):
    return [json.loads(l) for l in Path(path).read_text().splitlines() if l.strip()]


def estimands(table, subject, idx=None, judge=None, pressure=None):
    e1 = table.score(subject, *SLICES["E1"], idx, judge, pressure)
    t1 = table.score(subject, *TURN1, idx, judge, pressure)
    return {"E1": e1,
            "E3": None if e1 is None or t1 is None else e1 - t1,
            "E4_stated": table.score(subject, *SLICES["E4_stated"], idx, judge, pressure),
            "E4_guided": table.score(subject, *SLICES["E4_guided"], idx, judge, pressure)}


# --------------------------------------------------------------------------
# Criteria
# --------------------------------------------------------------------------

def ranking_check(full_e1, mini_e1):
    """Sign flips and discordant pairs (E2). Both args: subject -> E1."""
    subs = [s for s in full_e1 if full_e1[s] is not None and mini_e1.get(s) is not None]
    flips = [s for s in subs if (full_e1[s] > 0) != (mini_e1[s] > 0)]
    discordant, n_sep = [], 0
    for a, b in combinations(subs, 2):
        d = full_e1[a] - full_e1[b]
        if abs(d) > SEPARATION:
            n_sep += 1
            if (mini_e1[a] - mini_e1[b]) * d <= 0:
                discordant.append([a, b])
    tau = None if n_sep == 0 else 1.0 - 2.0 * len(discordant) / n_sep
    return {"sign_flips": flips, "n_separated_pairs": n_sep,
            "discordant_pairs": discordant, "tau_separated": tau}


def evaluate(full, mini):
    """Score a set of mini estimates against full-bench references.
    full, mini: subject -> {estimand: value|None}. Undefined estimands are
    skipped (not scored as zero)."""
    errors = {}
    for s in full:
        errors[s] = {e: (None if full[s][e] is None or mini[s].get(e) is None
                         else abs(mini[s][e] - full[s][e])) for e in ESTIMANDS}
    max_err = {}
    for e in ESTIMANDS:
        vals = [v[e] for v in errors.values() if v[e] is not None]
        max_err[e] = max(vals) if vals else None
    worst = max(v for v in max_err.values() if v is not None)
    rk = ranking_check({s: full[s]["E1"] for s in full}, {s: mini[s]["E1"] for s in mini})
    ok = worst <= THRESHOLD and not rk["sign_flips"] and not rk["discordant_pairs"]
    return {"pass": bool(ok), "worst_abs_err": worst, "max_err": max_err,
            "errors": errors, **rk}


# --------------------------------------------------------------------------
# Coverage constraints
# --------------------------------------------------------------------------

class Coverage:
    """Pillar coverage (>= 1 probe per pillar) and class-share bounds
    (each islamic class within +-CLASS_TOL of its bank share) at size k."""

    def __init__(self, probes_meta, probe_ids, k):
        self.k = k
        self.n = len(probe_ids)
        self.cls = np.array([CLASSES.index(probes_meta[p]["islamic"]) for p in probe_ids])
        self.pil = np.array([[pl in probes_meta[p]["pillars"] for pl in PILLARS]
                             for p in probe_ids], dtype=bool)
        share = np.bincount(self.cls, minlength=len(CLASSES)) / self.n
        self.share = share
        self.lo = np.maximum(0, np.ceil((share - CLASS_TOL) * k - 1e-9)).astype(int)
        self.hi = np.floor((share + CLASS_TOL) * k + 1e-9).astype(int)
        self.onehot = np.eye(len(CLASSES), dtype=int)[self.cls]

    def _state(self, chosen):
        if len(chosen):
            counts = np.bincount(self.cls[chosen], minlength=len(CLASSES))
            covered = self.pil[chosen].any(axis=0)
        else:
            counts = np.zeros(len(CLASSES), dtype=int)
            covered = np.zeros(len(PILLARS), dtype=bool)
        return counts, covered

    def feasible_additions(self, chosen):
        """Bool mask over probes: adding this probe keeps the constraints
        satisfiable at k (necessary condition; `satisfied` is the final check)."""
        chosen = list(chosen)
        counts, covered = self._state(chosen)
        remaining_after = self.k - len(chosen) - 1
        new_counts = counts[None, :] + self.onehot
        ok = (new_counts <= self.hi[None, :]).all(axis=1)
        class_deficit = np.maximum(0, self.lo[None, :] - new_counts).sum(axis=1)
        pillar_deficit = (~(covered[None, :] | self.pil)).sum(axis=1)
        ok &= class_deficit <= remaining_after
        ok &= pillar_deficit <= remaining_after
        ok[chosen] = False
        return ok

    def satisfied(self, idx):
        idx = list(idx)
        counts, covered = self._state(idx)
        detail = {"k": len(idx),
                  "class_counts": {c: int(counts[i]) for i, c in enumerate(CLASSES)},
                  "class_bounds": {c: [int(self.lo[i]), int(self.hi[i])] for i, c in enumerate(CLASSES)},
                  "pillars_covered": {p: bool(covered[i]) for i, p in enumerate(PILLARS)}}
        ok = (len(idx) == self.k and (counts >= self.lo).all() and (counts <= self.hi).all()
              and covered.all())
        return bool(ok), detail


# --------------------------------------------------------------------------
# Objective helpers (training subjects x defined estimands)
# --------------------------------------------------------------------------

def _specs(table, subjects):
    """[(slice_a, slice_b|None, reference)] for every defined estimand."""
    specs = []
    for s in subjects:
        ref = estimands(table, s)
        for e in ESTIMANDS:
            if ref[e] is None:
                continue
            if e == "E3":
                specs.append((table.slice(s, *SLICES["E1"]), table.slice(s, *TURN1), ref[e]))
            else:
                specs.append((table.slice(s, *SLICES[e]), None, ref[e]))
    return specs


def _ratio(a, idx):
    s, c = a[0][idx].sum(), a[1][idx].sum()
    return math.nan if c == 0 else s / c


def max_dev(specs, idx):
    """Max |mini - full| over the specs for probe set idx (nan -> inf)."""
    idx = np.asarray(idx)
    worst = 0.0
    for a, b, ref in specs:
        v = _ratio(a, idx)
        if b is not None:
            v -= _ratio(b, idx)
        v *= SCORE_SCALE
        if math.isnan(v):
            return math.inf
        worst = max(worst, abs(v - ref))
    return worst


# --------------------------------------------------------------------------
# Selection methods
# --------------------------------------------------------------------------

def greedy_select(table, train, k, cov):
    """Constrained greedy forward selection minimizing max deviation over all
    defined estimands x training subjects. Deterministic; ties -> lowest
    probe index. Returns the probes in selection order."""
    specs = _specs(table, train)
    chosen = []
    with np.errstate(divide="ignore", invalid="ignore"):
        while len(chosen) < k:
            feas = cov.feasible_additions(chosen)
            if not feas.any():
                raise RuntimeError(f"no feasible candidate at step {len(chosen)} for k={k}")
            dev = np.zeros(table.n)
            for a, b, ref in specs:
                val = (a[0][chosen].sum() + a[0]) / (a[1][chosen].sum() + a[1])
                if b is not None:
                    val = val - (b[0][chosen].sum() + b[0]) / (b[1][chosen].sum() + b[1])
                dev = np.maximum(dev, np.abs(val * SCORE_SCALE - ref))
            dev = np.where(np.isnan(dev), np.inf, dev)
            dev[~feas] = np.inf
            chosen.append(int(np.argmin(dev)))
    ok, detail = cov.satisfied(chosen)
    if not ok:
        raise RuntimeError(f"greedy result violates coverage constraints: {detail}")
    return chosen


def strata_of(probes_meta, probe_ids):
    strata = defaultdict(list)
    for i, p in enumerate(probe_ids):
        m = probes_meta[p]
        strata[(m["islamic"], tuple(sorted(m["pillars"])))].append(i)
    return {s: np.array(strata[s]) for s in sorted(strata)}


def stratified_draw(rng, strata, k, n):
    """Proportional allocation over strata with largest-remainder rounding."""
    quotas = {s: k * len(ix) / n for s, ix in strata.items()}
    base = {s: int(q) for s, q in quotas.items()}
    rem = k - sum(base.values())
    # Largest remainder; ties broken at random (seeded) so no class is favored.
    jitter = {s: rng.random() for s in quotas}
    for s in sorted(quotas, key=lambda s: (-(quotas[s] - base[s]), jitter[s]))[:rem]:
        base[s] += 1
    take = []
    for s, m in base.items():
        if m:
            take += list(rng.choice(strata[s], m, replace=False))
    return np.array(sorted(take))


def random_draw(rng, k, n):
    return np.sort(rng.choice(n, k, replace=False))


def anneal(table, subjects, k, cov, start, rng, iters=20000, t0=0.02, t1=0.0005):
    """Simulated annealing (swap moves, constraint-respecting) from `start`
    on the in-sample objective. Returns (best_idx, best_dev, trace)."""
    specs = _specs(table, subjects)
    cur = list(start)
    cur_dev = max_dev(specs, cur)
    best, best_dev = list(cur), cur_dev
    outside = [i for i in range(table.n) if i not in set(cur)]
    accepted = 0
    for it in range(iters):
        temp = t0 * (t1 / t0) ** (it / max(1, iters - 1))
        i_out = int(rng.integers(len(cur)))
        i_in = int(rng.integers(len(outside)))
        cand = list(cur)
        cand[i_out] = outside[i_in]
        if not cov.satisfied(cand)[0]:
            continue
        d = max_dev(specs, cand)
        if d <= cur_dev or rng.random() < math.exp(-(d - cur_dev) / temp):
            outside[i_in], cur[i_out] = cur[i_out], outside[i_in]
            cur_dev = d
            accepted += 1
            if d < best_dev:
                best, best_dev = list(cur), d
    return sorted(best), best_dev, {"iters": iters, "accepted": accepted,
                                    "start_dev": max_dev(specs, start)}


def milp_select(table, subjects, k, cov, time_limit=300.0):
    """Exact min-max selection via MILP (HiGHS). Uses per-probe mean-band
    coefficients (linear in x); identical to the pooled mean where every
    probe has equal counts, off by < 0.001 where a few cells are missing.
    Returns (idx, t_opt, status, exact_dev)."""
    from scipy.optimize import Bounds, LinearConstraint, milp

    specs = _specs(table, subjects)
    n = table.n
    rows, lo, hi = [], [], []

    def per_probe_mean(a):
        with np.errstate(divide="ignore", invalid="ignore"):
            m = a[0] / a[1]
        fill = a[0].sum() / a[1].sum()
        return np.where(a[1] > 0, m, fill)

    for a, b, ref in specs:
        coef = per_probe_mean(a)
        if b is not None:
            coef = coef - per_probe_mean(b)
        coef = coef * SCORE_SCALE / k
        # sum(coef x) - t <= ref ; sum(coef x) + t >= ref
        rows.append(np.append(coef, -1.0)); lo.append(-np.inf); hi.append(ref)
        rows.append(np.append(coef, 1.0)); lo.append(ref); hi.append(np.inf)
    rows.append(np.append(np.ones(n), 0.0)); lo.append(k); hi.append(k)
    for ci in range(len(CLASSES)):
        rows.append(np.append((cov.cls == ci).astype(float), 0.0))
        lo.append(cov.lo[ci]); hi.append(cov.hi[ci])
    for pi in range(len(PILLARS)):
        rows.append(np.append(cov.pil[:, pi].astype(float), 0.0))
        lo.append(1); hi.append(np.inf)
    A = np.array(rows)
    c = np.zeros(n + 1); c[-1] = 1.0
    integrality = np.append(np.ones(n), 0)
    bounds = Bounds(np.zeros(n + 1), np.append(np.ones(n), np.inf))
    res = milp(c, constraints=LinearConstraint(A, lo, hi), integrality=integrality,
               bounds=bounds, options={"time_limit": time_limit})
    if res.x is None:
        return None, None, res.message, None
    idx = sorted(int(i) for i in np.flatnonzero(res.x[:n] > 0.5))
    return idx, float(res.x[-1]), res.message, max_dev(specs, idx)


# --------------------------------------------------------------------------
# Validation
# --------------------------------------------------------------------------

def loo_greedy(table, subjects, k, cov):
    """Leave-one-subject-out: select on 11, score the held-out subject,
    evaluate the criteria on the cross-validated prediction vector."""
    full = {s: estimands(table, s) for s in subjects}
    mini, folds = {}, {}
    for held in subjects:
        train = [s for s in subjects if s != held]
        idx = greedy_select(table, train, k, cov)
        folds[held] = idx
        mini[held] = estimands(table, held, idx)
    return evaluate(full, mini), folds


def draw_stats(table, subjects, k, draws):
    """Criteria over a set of subject-independent draws (random/stratified):
    pass rate and error distribution. Selection does not depend on the
    subjects, so leave-one-out equals in-sample here."""
    full = {s: estimands(table, s) for s in subjects}
    passes, worst, flips, taus = [], [], [], []
    per_est = {e: [] for e in ESTIMANDS}
    for idx in draws:
        ev = evaluate(full, {s: estimands(table, s, idx) for s in subjects})
        passes.append(ev["pass"])
        worst.append(ev["worst_abs_err"])
        flips.append(len(ev["sign_flips"]) > 0)
        taus.append(ev["tau_separated"] == 1.0)
        for e in ESTIMANDS:
            if ev["max_err"][e] is not None:
                per_est[e].append(ev["max_err"][e])
    worst = np.array(worst)
    return {"n_draws": len(draws), "pass_rate": float(np.mean(passes)),
            "worst_abs_err_median": float(np.median(worst)),
            "worst_abs_err_p90": float(np.percentile(worst, 90)),
            "p_sign_flip": float(np.mean(flips)), "p_tau1": float(np.mean(taus)),
            "max_err_median": {e: float(np.median(v)) for e, v in per_est.items() if v},
            "max_err_p90": {e: float(np.percentile(v, 90)) for e, v in per_est.items() if v}}


def bootstrap(table, subject, idx, rng, n_boot):
    """Bootstrap over probes (resample the probe set with replacement) for
    every estimand; paired draws for E3. idx None = full bank."""
    base = np.arange(table.n) if idx is None else np.asarray(idx)
    k = len(base)
    draws = base[rng.integers(0, k, (n_boot, k))]

    def ratio(a):
        s = a[0][draws].sum(axis=1)
        c = a[1][draws].sum(axis=1)
        with np.errstate(divide="ignore", invalid="ignore"):
            return s / c

    out = {}
    pt = estimands(table, subject, base)
    for e in ESTIMANDS:
        if pt[e] is None:
            out[e] = None
            continue
        if e == "E3":
            boots = (ratio(table.slice(subject, *SLICES["E1"]))
                     - ratio(table.slice(subject, *TURN1))) * SCORE_SCALE
        else:
            boots = ratio(table.slice(subject, *SLICES[e])) * SCORE_SCALE
        boots = boots[np.isfinite(boots)]
        lo, hi = np.percentile(boots, [2.5, 97.5])
        out[e] = {"point": round(pt[e], 4), "lo": round(float(lo), 4), "hi": round(float(hi), 4),
                  "half_width": round(float((hi - lo) / 2), 4)}
    return out


def spearman(x, y):
    def rank(v):
        v = np.asarray(v, dtype=float)
        r = np.empty(len(v))
        r[np.argsort(-v)] = np.arange(1, len(v) + 1)
        return r
    return float(np.corrcoef(rank(x), rank(y))[0, 1])


# --------------------------------------------------------------------------
# Runner
# --------------------------------------------------------------------------

def _py(o):
    if isinstance(o, dict):
        return {str(k): _py(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_py(v) for v in o]
    if isinstance(o, np.generic):
        return o.item()
    if isinstance(o, np.ndarray):
        return o.tolist()
    return o


def load_tables(results):
    results = Path(results)
    bank = load_probes()
    probe_ids = [p["id"] for p in bank["probes"]]
    meta = {p["id"]: p for p in bank["probes"]}
    main = build_table(score_mod.load_judgments(results), probe_ids)
    variants = build_table([j for f in VARIANT_FILES for j in read_jsonl(results / f)], probe_ids)
    ar_path = results / "judgments_ar.jsonl"
    arabic = build_table(read_jsonl(ar_path), probe_ids) if ar_path.exists() else None
    return bank, meta, probe_ids, main, variants, arabic


app = typer.Typer(help=__doc__, add_completion=False)


@app.command()
def run(results: Path = typer.Option(..., help="Results directory with the judgment .jsonl files"),
        out: Path = typer.Option(None, help="Output JSON (default: <package results>/mini_stats.json)"),
        quick: bool = typer.Option(False, help="Smoke run: 50 draws, 200 bootstraps, short grid"),
        skip_milp: bool = typer.Option(False, help="Skip the MILP optimality check"),
        milp_time_limit: float = typer.Option(300.0, help="HiGHS time limit (s)"),
        anneal_iters: int = typer.Option(20000, help="Annealing iterations"),
        freeze_artifact: bool = typer.Option(False, "--freeze/--no-freeze",
                                             help="(Re)write the frozen data/mini_v1.json. Off by "
                                                  "default and always off under --quick, so a re-run "
                                                  "cannot silently overwrite the paper-cited list.")):
    """Run every selection method over the k grid, validate (LOO, per-judge,
    Arabic, variants, per-pressure, bootstrap, optimality gap), freeze the
    mini at k*, and write mini_stats.json + data/mini_v1.json."""
    t_start = time.time()
    out = out or RESULTS / "mini_stats.json"
    if quick and freeze_artifact:
        typer.echo("--quick never rewrites the frozen artifact; ignoring --freeze")
        freeze_artifact = False
    if not skip_milp:
        # Fail fast: scipy is a dev-only dependency. Check it before the
        # multi-minute grid rather than inside freeze(), after the work is done.
        try:
            import scipy.optimize  # noqa: F401
        except ImportError as e:
            raise RuntimeError("scipy is required for the MILP check (uv sync --group dev), "
                               "or pass --skip-milp") from e
    n_draws = 50 if quick else N_DRAWS
    n_boot = 200 if quick else N_BOOT
    k_grid = [20, 40, 60, 80, 100] if quick else K_GRID

    bank, meta, probe_ids, main, variants, arabic = load_tables(results)
    subjects = [s for s in SELECTION_SUBJECTS if s in main.subjects]
    missing = [s for s in SELECTION_SUBJECTS if s not in main.subjects]
    if missing:
        raise RuntimeError(f"selection subjects missing from results: {missing}")
    rng = np.random.default_rng(SEED)
    full = {s: estimands(main, s) for s in subjects}
    typer.echo(f"subjects={len(subjects)} probes={main.n} judges={main.judges()}")
    stats = {"meta": {"seed": SEED, "boot_seed": BOOT_SEED, "n_boot": n_boot, "n_draws": n_draws,
                      "threshold": THRESHOLD, "separation": SEPARATION, "class_tol": CLASS_TOL,
                      "h1_max_k": H1_MAX_K, "k_grid": k_grid, "bank_version": bank["version"],
                      "subjects": subjects, "quick": quick},
             "full": full, "methods": {"random": {}, "stratified": {}, "greedy_loo": {},
                                       "greedy_insample": {}}}

    strata = strata_of(meta, probe_ids)
    for k in k_grid:
        cov = Coverage(meta, probe_ids, k)
        r_draws = [random_draw(rng, k, main.n) for _ in range(n_draws)]
        s_draws = [stratified_draw(rng, strata, k, main.n) for _ in range(n_draws)]
        stats["methods"]["random"][k] = draw_stats(main, subjects, k, r_draws)
        stats["methods"]["stratified"][k] = draw_stats(main, subjects, k, s_draws)
        ev, folds = loo_greedy(main, subjects, k, cov)
        stats["methods"]["greedy_loo"][k] = {**ev, "folds": {h: [probe_ids[i] for i in ix]
                                                            for h, ix in folds.items()}}
        idx = greedy_select(main, subjects, k, cov)
        ev_in = evaluate(full, {s: estimands(main, s, idx) for s in subjects})
        stats["methods"]["greedy_insample"][k] = {**ev_in, "probe_ids": [probe_ids[i] for i in idx]}
        typer.echo(f"k={k:3d} random pass={stats['methods']['random'][k]['pass_rate']:.2f} "
                   f"strat pass={stats['methods']['stratified'][k]['pass_rate']:.2f} "
                   f"greedy LOO worst={ev['worst_abs_err']:.3f} pass={ev['pass']} "
                   f"| in-sample worst={ev_in['worst_abs_err']:.3f}")

    passing = [k for k in k_grid if stats["methods"]["greedy_loo"][k]["pass"]]
    k_star = passing[0] if passing else None
    stats["k_star"] = k_star
    stats["h1"] = {"holds": bool(k_star is not None and k_star <= H1_MAX_K), "k_star": k_star}
    if k_star is None:
        # Negative result: no grid k passes. Still run the whole validation
        # ladder on the best-available k (smallest LOO worst error) so the
        # failure is documented, and flag it as not meeting the criteria.
        k_ref = min(k_grid, key=lambda k: (stats["methods"]["greedy_loo"][k]["worst_abs_err"], k))
        typer.echo(f"no grid k passes LOO; H1 falsified. Reporting the ladder at k={k_ref} "
                   f"(best LOO worst error), flagged criteria_met=false.")
    else:
        k_ref = k_star
    stats["h2"] = {"holds": bool(stats["methods"]["random"][k_ref]["pass_rate"] < 0.5
                                 and stats["methods"]["stratified"][k_ref]["pass_rate"] < 0.5),
                   "at_k": k_ref,
                   "random_pass_rate": stats["methods"]["random"][k_ref]["pass_rate"],
                   "stratified_pass_rate": stats["methods"]["stratified"][k_ref]["pass_rate"]}
    stats["frozen"] = freeze(main, variants, arabic, meta, probe_ids, subjects, k_ref,
                             stats, rng, n_boot, skip_milp, milp_time_limit, anneal_iters,
                             criteria_met=k_star is not None, write_frozen=freeze_artifact)
    stats["meta"]["wall_seconds"] = round(time.time() - t_start, 1)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(_py(stats), indent=1))
    typer.echo(f"wrote {out}  (k*={k_star}, H1={stats['h1']['holds']}, "
               f"{stats['meta']['wall_seconds']}s)")


def freeze(main, variants, arabic, meta, probe_ids, subjects, k, stats, rng, n_boot,
           skip_milp, milp_time_limit, anneal_iters, criteria_met=True, write_frozen=False):
    """Everything about the mini at k: in-sample + LOO fit, per-judge, Arabic,
    variants, per-pressure, bootstrap, optimality gap. Writes data/mini_v1.json
    only when `write_frozen` is set (the frozen list is a paper-cited artifact)."""
    cov = Coverage(meta, probe_ids, k)
    idx = greedy_select(main, subjects, k, cov)
    ids = [probe_ids[i] for i in idx]
    full = {s: estimands(main, s) for s in subjects}
    fz = {"k": k, "criteria_met": criteria_met, "probe_ids": ids, "coverage": cov.satisfied(idx)[1],
          "insample": evaluate(full, {s: estimands(main, s, idx) for s in subjects}),
          "loo": {kk: v for kk, v in stats["methods"]["greedy_loo"][k].items() if kk != "folds"}}
    fz["mini_scores"] = {s: estimands(main, s, idx) for s in subjects}

    # V2 per judge: frozen mini in-sample, and the LOO folds re-scored per judge.
    folds = stats["methods"]["greedy_loo"][k]["folds"]
    fold_idx = {h: [main.pidx[p] for p in ps] for h, ps in folds.items()}
    fz["per_judge"] = {}
    for judge in main.judges():
        fj = {s: estimands(main, s, judge=judge) for s in subjects}
        fz["per_judge"][judge] = {
            "insample": evaluate(fj, {s: estimands(main, s, idx, judge=judge) for s in subjects}),
            "loo": evaluate(fj, {s: estimands(main, s, fold_idx[s], judge=judge) for s in subjects})}

    # V3 Arabic: never used in selection.
    if arabic is not None:
        ar_subjects = list(arabic.subjects)
        ar_full = {s: estimands(arabic, s) for s in ar_subjects}
        ar_mini = {s: estimands(arabic, s, idx) for s in ar_subjects}
        shared = [s for s in AR_SHARED if s in ar_subjects and s in subjects]
        fz["arabic"] = {"subjects": ar_subjects, "shared": shared,
                        "eval": evaluate(ar_full, ar_mini),
                        "full": ar_full, "mini": ar_mini,
                        "rho_full": spearman([ar_full[s]["E1"] for s in shared],
                                             [full[s]["E1"] for s in shared]),
                        "rho_mini": spearman([ar_mini[s]["E1"] for s in shared],
                                             [fz["mini_scores"][s]["E1"] for s in shared]),
                        "rho_mini_ar_vs_full_en": spearman([ar_mini[s]["E1"] for s in shared],
                                                           [full[s]["E1"] for s in shared])}

    # V3b variants: never used in selection.
    v_subjects = list(variants.subjects)
    if v_subjects:
        v_full = {s: estimands(variants, s) for s in v_subjects}
        v_mini = {s: estimands(variants, s, idx) for s in v_subjects}
        fz["variants"] = {"subjects": v_subjects, "eval": evaluate(v_full, v_mini),
                          "full": v_full, "mini": v_mini}

    # Per-pressure steadfastness (reported, not gated).
    pp = {}
    for s in subjects:
        pp[s] = {}
        for pr in PRESSURES:
            f = estimands(main, s, pressure=pr)["E3"]
            m = estimands(main, s, idx, pressure=pr)["E3"]
            pp[s][pr] = {"full": f, "mini": m,
                         "abs_err": None if f is None or m is None else abs(m - f)}
    errs = [v["abs_err"] for d in pp.values() for v in d.values() if v["abs_err"] is not None]
    fz["per_pressure_steadfastness"] = {"cells": pp, "max_abs_err": max(errs),
                                        "mean_abs_err": float(np.mean(errs)),
                                        "n_cells_over_threshold": int(sum(e > THRESHOLD for e in errs))}

    # Bootstrap CIs and inflation.
    brng = np.random.default_rng(BOOT_SEED)
    fz["bootstrap"] = {"n_boot": n_boot, "sqrt_ratio": math.sqrt(main.n / k), "subjects": {}}
    infl = {e: [] for e in ESTIMANDS}
    for s in subjects:
        b_full = bootstrap(main, s, None, brng, n_boot)
        b_mini = bootstrap(main, s, idx, brng, n_boot)
        fz["bootstrap"]["subjects"][s] = {"full": b_full, "mini": b_mini}
        for e in ESTIMANDS:
            if b_full[e] and b_mini[e] and b_full[e]["half_width"] > 0:
                infl[e].append(b_mini[e]["half_width"] / b_full[e]["half_width"])
    fz["bootstrap"]["inflation_mean"] = {e: float(np.mean(v)) for e, v in infl.items() if v}

    # Optimality gap (in-sample objective on all subjects).
    specs = _specs(main, subjects)
    g_dev = max_dev(specs, idx)
    a_idx, a_dev, a_trace = anneal(main, subjects, k, cov, idx, rng, iters=anneal_iters)
    fz["annealing"] = {"greedy_dev": g_dev, "anneal_dev": a_dev, "gap": g_dev - a_dev,
                       "probe_ids": [probe_ids[i] for i in a_idx], **a_trace}
    if not skip_milp:
        t0 = time.time()
        m_idx, t_opt, status, exact = milp_select(main, subjects, k, cov, milp_time_limit)
        fz["milp"] = {"status": status, "t_opt_linearized": t_opt, "exact_dev": exact,
                      "greedy_dev": g_dev, "gap": None if exact is None else g_dev - exact,
                      "probe_ids": None if m_idx is None else [probe_ids[i] for i in m_idx],
                      "seconds": round(time.time() - t0, 1)}

    fz["frozen_artifact"] = frozen_record(k, ids, subjects, criteria_met,
                                          stats["methods"]["greedy_loo"][k]["worst_abs_err"],
                                          fz["per_judge"])
    if write_frozen:
        MINI_PATH.write_text(json.dumps(fz["frozen_artifact"], indent=1))
        typer.echo(f"froze k={k} -> {MINI_PATH}")
    else:
        typer.echo(f"k={k} evaluated; frozen artifact NOT written (pass --freeze to rewrite {MINI_PATH.name})")
    return fz


def frozen_record(k, ids, subjects, criteria_met, loo_worst, per_judge):
    """The content of data/mini_v1.json. `pooled_only` carries the per-judge
    caveat with the artifact: True when any single judge fails held-out."""
    judge_fail = [j for j, v in per_judge.items() if not v["loo"]["pass"]]
    return {
        "version": 1, "bank_version": load_probes()["version"], "k": k, "seed": SEED,
        "criteria_met": criteria_met, "loo_worst_abs_err": loo_worst,
        "pooled_only": bool(judge_fail),
        "per_judge_loo_fail": judge_fail,
        "selection": "constrained greedy forward selection, max |mini-full| over E1/E3/E4 x subjects",
        "selected_on": subjects, "threshold": THRESHOLD, "class_tol_pp": CLASS_TOL,
        "command": "uv run --directory jaleesbench python -m jaleesbench.mini run --results <results> --freeze",
        "probe_ids": ids}


@app.command()
def score(results: Path = typer.Option(..., help="Results directory"),
          subject: str = typer.Option(..., help="Subject name"),
          extra: Path = typer.Option(None, help="Additional judgments .jsonl to fold in"),
          n_boot: int = typer.Option(N_BOOT)):
    """Score one subject on the frozen mini (and on the full bank if it has
    full data): the path for the prospective test (V4) or any new subject."""
    frozen = json.loads(MINI_PATH.read_text())
    bank = load_probes()
    if bank["version"] != frozen["bank_version"]:
        raise RuntimeError(f"probe bank v{bank['version']} != mini bank v{frozen['bank_version']}; re-run selection")
    probe_ids = [p["id"] for p in bank["probes"]]
    js = score_mod.load_judgments(results)
    for f in VARIANT_FILES:
        if (Path(results) / f).exists():
            js += read_jsonl(Path(results) / f)
    if extra:
        js += read_jsonl(extra)
    table = build_table([j for j in js if j["subject"] == subject], probe_ids)
    if subject not in table.subjects:
        raise RuntimeError(f"no judgments for subject {subject!r}")
    idx = [table.pidx[p] for p in frozen["probe_ids"]]
    have = table.slice(subject, *SLICES["E1"])[1]
    n_full = int((have > 0).sum())
    n_mini = int((have[idx] > 0).sum())
    brng = np.random.default_rng(BOOT_SEED)
    out = {"subject": subject, "mini_k": frozen["k"], "probes_with_data_full": n_full,
           "probes_with_data_mini": n_mini,
           "mini": bootstrap(table, subject, idx, brng, n_boot)}
    if n_full == table.n:
        out["full"] = bootstrap(table, subject, None, brng, n_boot)
        out["abs_err"] = {e: (None if out["mini"][e] is None else
                              round(abs(out["mini"][e]["point"] - out["full"][e]["point"]), 4))
                          for e in ESTIMANDS}
        out["pass_threshold"] = all(v is None or v <= THRESHOLD for v in out["abs_err"].values())
    typer.echo(json.dumps(_py(out), indent=1))


# --------------------------------------------------------------------------
# Exploratory analyses (NOT preregistered; reported as such)
# --------------------------------------------------------------------------

def _pass_under(ev_errors, full, mini_e1, threshold, estimand_set):
    """Re-score stored per-subject errors under a different threshold and
    estimand set (E2 always applies)."""
    worst = max(v[e] for v in ev_errors.values() for e in estimand_set if v[e] is not None)
    rk = ranking_check(full, mini_e1)
    return worst <= threshold and not rk["sign_flips"] and not rk["discordant_pairs"], worst


@app.command()
def explore(results: Path = typer.Option(..., help="Results directory"),
            stats: Path = typer.Option(None, help="mini_stats.json from `run`"),
            out: Path = typer.Option(None, help="Output JSON (default: <results>/mini_explore.json)"),
            n_draws: int = typer.Option(N_DRAWS)):
    """Exploratory, not preregistered: threshold / estimand-set sensitivity of
    k*, the in-sample vs held-out gap, held-out failure attribution, and the
    analytic sampling floor for a random subset of size k."""
    stats = stats or RESULTS / "mini_stats.json"
    out = out or RESULTS / "mini_explore.json"
    st = json.loads(Path(stats).read_text())
    bank, meta, probe_ids, main, _, _ = load_tables(results)
    subjects = st["meta"]["subjects"]
    k_grid = st["meta"]["k_grid"]
    full = {s: estimands(main, s) for s in subjects}
    full_e1 = {s: full[s]["E1"] for s in subjects}
    thresholds = [0.05, 0.075, 0.10]
    sets = {"full_suite": ESTIMANDS, "headline_only": ["E1"], "headline_steadfastness": ["E1", "E3"]}
    ex = {"note": "exploratory; not preregistered", "thresholds": thresholds, "estimand_sets": sets}

    # (a) greedy-LOO k* under alternative criteria, from the stored fold errors.
    ex["greedy_loo_k_star"] = {}
    for name, es in sets.items():
        for th in thresholds:
            ks = []
            for k in k_grid:
                g = st["methods"]["greedy_loo"][str(k)]
                # rebuild the LOO prediction vector for E1 from stored errors is not
                # possible (errors are absolute); re-score the folds directly.
                fold_idx = {h: [main.pidx[p] for p in ps] for h, ps in g["folds"].items()}
                mini_e1 = {s: estimands(main, s, fold_idx[s])["E1"] for s in subjects}
                ok, _ = _pass_under(g["errors"], full_e1, mini_e1, th, es)
                if ok:
                    ks.append(k)
            ex["greedy_loo_k_star"][f"{name}@{th}"] = ks[0] if ks else None

    # (b)+(c) in-sample vs held-out gap and worst held-out cell per k.
    ex["gap"] = {}
    for k in k_grid:
        g = st["methods"]["greedy_loo"][str(k)]
        cells = [(v[e], s, e) for s, v in g["errors"].items() for e in ESTIMANDS if v[e] is not None]
        w = max(cells)
        ex["gap"][k] = {"insample_worst": st["methods"]["greedy_insample"][str(k)]["worst_abs_err"],
                        "loo_worst": g["worst_abs_err"], "worst_subject": w[1], "worst_estimand": w[2],
                        "n_cells_over": sum(c[0] > THRESHOLD for c in cells)}

    # (d) random draws under alternative criteria (same seed as `run`).
    rng = np.random.default_rng(SEED)
    ex["random_pass_rate"] = {}
    for k in k_grid:
        draws = [random_draw(rng, k, main.n) for _ in range(n_draws)]
        acc = {f"{name}@{th}": 0 for name in sets for th in thresholds}
        for idx in draws:
            mini = {s: estimands(main, s, idx) for s in subjects}
            errs = {s: {e: (None if full[s][e] is None else abs(mini[s][e] - full[s][e]))
                        for e in ESTIMANDS} for s in subjects}
            mini_e1 = {s: mini[s]["E1"] for s in subjects}
            for name, es in sets.items():
                for th in thresholds:
                    ok, _ = _pass_under(errs, full_e1, mini_e1, th, es)
                    acc[f"{name}@{th}"] += ok
        ex["random_pass_rate"][k] = {kk: v / n_draws for kk, v in acc.items()}

    # (e) analytic floor: finite-population SE of a size-k random subset for E1,
    # from the per-probe SD of probe means; and the SE at which the max over
    # 12 subjects stays under 0.05 (max of 12 |N(0,1)| ~ 2.3 SD).
    ex["sampling_floor"] = {}
    for s in subjects:
        a = main.slice(s, *SLICES["E1"])
        with np.errstate(divide="ignore", invalid="ignore"):
            pm = np.where(a[1] > 0, a[0] / a[1], np.nan) * SCORE_SCALE
        sd = float(np.nanstd(pm, ddof=1))
        ex["sampling_floor"][s] = {"probe_sd": sd,
                                   "se_by_k": {k: sd * math.sqrt(1 / k - 1 / main.n) for k in k_grid}}
    out.write_text(json.dumps(_py(ex), indent=1))
    typer.echo(f"wrote {out}")
    for kk, v in ex["greedy_loo_k_star"].items():
        typer.echo(f"  greedy LOO k* {kk}: {v}")


# --------------------------------------------------------------------------
# Paper figure
# --------------------------------------------------------------------------

@app.command()
def figures(stats: Path = typer.Option(None, help="mini_stats.json"),
            explore_json: Path = typer.Option(None, help="mini_explore.json"),
            out_dir: Path = typer.Option(None, help="default: docs/paper/figures")):
    """Render fig_mini_k.pdf/.png: held-out error vs k (greedy held-out,
    greedy in-sample, random median/p90) and random pass rate vs k."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    stats = stats or RESULTS / "mini_stats.json"
    explore_json = explore_json or RESULTS / "mini_explore.json"
    out_dir = out_dir or RESULTS.parent.parent / "docs" / "paper" / "figures"
    st = json.loads(Path(stats).read_text())
    ex = json.loads(Path(explore_json).read_text())
    ks = st["meta"]["k_grid"]
    g_loo = [st["methods"]["greedy_loo"][str(k)]["worst_abs_err"] for k in ks]
    g_in = [st["methods"]["greedy_insample"][str(k)]["worst_abs_err"] for k in ks]
    r_med = [st["methods"]["random"][str(k)]["worst_abs_err_median"] for k in ks]
    r_p90 = [st["methods"]["random"][str(k)]["worst_abs_err_p90"] for k in ks]
    BLUE, AQUA, ORANGE = "#2a78d6", "#1baf7a", "#eb6834"
    INK, MUTED, GRID = "#0b0b0b", "#52514e", "#e6e6e6"
    plt.rcParams.update({"font.family": "serif", "font.serif": ["STIX Two Text", "DejaVu Serif"],
                         "font.size": 9.5, "axes.edgecolor": MUTED, "axes.linewidth": 0.6,
                         "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.6,
                         "xtick.color": INK, "ytick.color": INK, "axes.labelcolor": INK,
                         "legend.frameon": False, "figure.facecolor": "white"})
    fig, (ax, bx) = plt.subplots(1, 2, figsize=(7.2, 3.0), constrained_layout=True)
    for a in (ax, bx):
        a.spines[["top", "right"]].set_visible(False)
        a.set_xlabel("probes in the mini, $k$")
        a.set_xlim(15, 125)
    ax.fill_between(ks, r_med, r_p90, color=ORANGE, alpha=0.15, linewidth=0)
    ax.plot(ks, r_p90, color=ORANGE, lw=1.4, ls=(0, (3, 2)), label="random, 90th pct.")
    ax.plot(ks, r_med, color=ORANGE, lw=2, label="random, median")
    ax.plot(ks, g_in, color=AQUA, lw=2, marker="o", ms=4, label="greedy, in-sample")
    ax.plot(ks, g_loo, color=BLUE, lw=2, marker="o", ms=4, label="greedy, held-out (LOO)")
    ax.axhline(THRESHOLD, color=MUTED, lw=1, ls=(0, (1, 2)))
    ax.text(58, THRESHOLD + 0.005, "0.05 threshold", color=MUTED, fontsize=8.5)
    ax.set_ylim(0, 0.28)
    ax.set_ylabel("worst |mini − full| over subjects × estimands")
    ax.legend(loc="upper right", fontsize=8.5)
    ax.set_title("(a) held-out error", loc="left", fontsize=10, color=INK)
    RAMP = {"0.05": "#184f95", "0.075": "#2a78d6", "0.1": "#6da7ec"}
    for th, col in RAMP.items():
        y = [ex["random_pass_rate"][str(k)][f"full_suite@{th}"] for k in ks]
        bx.plot(ks, y, color=col, lw=2, label=f"threshold {th}")
    bx.set_ylim(0, 1.02)
    bx.set_ylabel("share of random draws passing all criteria")
    bx.legend(loc="upper left", fontsize=8.5)
    bx.set_title("(b) random subsets, full-suite criteria", loc="left", fontsize=10, color=INK)
    out_dir.mkdir(parents=True, exist_ok=True)
    for ext in ("pdf", "png"):
        fig.savefig(out_dir / f"fig_mini_k.{ext}", dpi=200)
    typer.echo(f"wrote {out_dir / 'fig_mini_k.pdf'}")


if __name__ == "__main__":
    app()
