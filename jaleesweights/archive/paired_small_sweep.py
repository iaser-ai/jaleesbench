"""Paired per-cell comparisons for the Inkling-Small stage-2 learning-rate
sweep (2026-08-25), against the stage-1 SFT checkpoint.

Cells are (probe, pressure) on the Opus test-70 judgments, unstated framing,
matched exactly between arms; scenario-cluster bootstrap (5000 resamples) on
the per-cell band deltas, display scale x0.5 (-1..+1). Mirrors
paired_sftdpo_bf16.py.

Run: python3 tmp/dpo-experiment/paired_small_sweep.py
"""

import collections
import json
import pathlib
import random
import statistics

ROOT = pathlib.Path(__file__).resolve().parent
OPUS = "claude-opus-4-8"
SFT = "inkling-small-sft"
ARMS = ["inkling-small-sftdpo", "inkling-small-sftdpo-lr3e-5",
        "inkling-small-sftdpo-lr1e-4", "inkling-small-sftdpo-lr3e-4",
        "inkling-small-sftdpo-lr1e-5-ep3", "inkling-small-sftdpo-lr3e-5-ep3",
        "inkling-small-sftdpo-lr1e-4-ep3"]
RUNS = {"inkling-small-sftdpo": "dpo_small_sft2_run",
        "inkling-small-sftdpo-lr3e-5": "dpo_small_sft2_sweep_lr3e-05",
        "inkling-small-sftdpo-lr1e-4": "dpo_small_sft2_sweep_lr0.0001",
        "inkling-small-sftdpo-lr3e-4": "dpo_small_sft2_sweep_lr0.0003",
        "inkling-small-sftdpo-lr1e-5-ep3": "dpo_small_sft2_sweep_lr1e-05_ep3",
        "inkling-small-sftdpo-lr3e-5-ep3": "dpo_small_sft2_sweep_lr3e-05_ep3",
        "inkling-small-sftdpo-lr1e-4-ep3": "dpo_small_sft2_sweep_lr0.0001_ep3"}


def bands(subject):
    out = {}
    for line in open(ROOT / "judgments_eval_small.jsonl"):
        j = json.loads(line)
        if j["subject"] == subject and j["judge"] == OPUS and j["framing"] == "unstated":
            out[(j["probe_id"], j["pressure"], j["scope"])] = int(j["band"])
    return out


def mean_score(b, scope):
    vals = [v * 0.5 for k, v in b.items() if k[2] == scope]
    return sum(vals) / len(vals), len(vals)


def paired(a, b, scope, seed=3446):
    per_probe = collections.defaultdict(list)
    for key in a.keys() & b.keys():
        if key[2] == scope:
            per_probe[key[0]].append((a[key] - b[key]) * 0.5)
    vals = [v for vs in per_probe.values() for v in vs]
    m = sum(vals) / len(vals)
    rng = random.Random(seed)
    keys = list(per_probe)
    boots = []
    for _ in range(5000):
        sample = [v for k in (rng.choice(keys) for _ in keys) for v in per_probe[k]]
        boots.append(sum(sample) / len(sample))
    boots.sort()
    up = sum(v > 0 for v in vals); down = sum(v < 0 for v in vals)
    return m, boots[125], boots[4875], len(vals), up, down


def train_fit(run_dir):
    p = ROOT / run_dir / "metrics.jsonl"
    if not p.exists():
        return "no metrics"
    M = [json.loads(l) for l in open(p)]
    last = M[-20:]
    return (f"{len(M)} steps; last-20 acc {statistics.mean(m['accuracy'] for m in last):.2f}, "
            f"margin {statistics.mean(m['margin'] for m in last):.2f}, "
            f"dpo_loss {statistics.mean(m['dpo_loss'] for m in last):.2f}")


sft = bands(SFT)
print(f"{SFT}: turn1 {mean_score(sft,'turn1')[0]:+.3f}  post {mean_score(sft,'full')[0]:+.3f}  "
      f"(n={mean_score(sft,'full')[1]})\n")
for arm in ARMS:
    b = bands(arm)
    print(f"{arm}  [train: {train_fit(RUNS[arm])}]")
    if not b:
        print("   no judgments yet\n"); continue
    for scope in ("turn1", "full"):
        s, n = mean_score(b, scope)
        m, lo, hi, npair, up, down = paired(b, sft, scope)
        print(f"   {scope:<6} score {s:+.3f} (n={n})   paired vs SFT {m:+.3f} [{lo:+.3f},{hi:+.3f}]  "
              f"up {up} down {down}")
    t1, _ = mean_score(b, "turn1"); po, _ = mean_score(b, "full")
    print(f"   drop under pressure {po - t1:+.3f}\n")
