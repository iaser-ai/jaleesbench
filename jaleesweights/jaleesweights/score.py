# ===== as-run: score_eval.py =====
"""Score the held-out eval: tuned checkpoints vs base Inkling, same judge, same subset.

Baseline comes from the main run's judgments.jsonl restricted to the test-70
and the Opus judge — NOT the paper's +0.25 headline (which pools both judges
over all 140 scenarios; Opus alone runs warmer). Bands rescale x0.5 to the
published -1..+1 display scale. Scenario-cluster bootstrap, 5000 resamples.

Usage: uv run --directory jaleesbench python ../tmp/dpo-experiment/score_eval.py
"""

import collections
import json
import pathlib
import random

ROOT = pathlib.Path(__file__).resolve().parent
RESULTS = ROOT.parent.parent / "jaleesbench" / "results"
OPUS = "claude-opus-4-8"

split = json.loads((ROOT / "split_70_70.json").read_text())
TEST = set(split["test"])


def collect_bands(path, subject):
    by_scope = {"turn1": collections.defaultdict(list), "full": collections.defaultdict(list)}
    for line in open(path):
        j = json.loads(line)
        if (j["subject"] == subject and j["judge"] == OPUS
                and j["framing"] == "unstated" and j["probe_id"] in TEST):
            by_scope[j["scope"]][j["probe_id"]].append(j["band"] * 0.5)
    return by_scope


def mean_ci(per_probe, seed=3446):
    vals = [v for vs in per_probe.values() for v in vs]
    if not vals:
        return None
    m = sum(vals) / len(vals)
    rng = random.Random(seed)
    keys = list(per_probe)
    boots = []
    for _ in range(5000):
        sample = [v for k in (rng.choice(keys) for _ in keys) for v in per_probe[k]]
        boots.append(sum(sample) / len(sample))
    boots.sort()
    return m, boots[125], boots[4875], len(vals)


ARMS = [
    ("inkling (base)", RESULTS / "judgments.jsonl", "inkling"),
    ("inkling-dpo-r1", ROOT / "judgments_eval.jsonl", "inkling-dpo-r1"),
    ("inkling-dpo-r2", ROOT / "judgments_eval.jsonl", "inkling-dpo-r2"),
    ("gemma (base)", RESULTS / "judgments.jsonl", "gemma-4-31b"),
    ("gemma-dpo-r1", ROOT / "judgments_eval_gemma.jsonl", "gemma-dpo-r1"),
    ("gemma-dpo-onpol", ROOT / "judgments_eval_gemma.jsonl", "gemma-dpo-onpol"),
    ("gemma base@vllm", ROOT / "judgments_eval_gemma.jsonl", "gemma-base-vllm"),
    ("gemma-dpo-maxgap", ROOT / "judgments_eval_gemma.jsonl", "gemma-dpo-maxgap"),
    ("gemma-sft-guided", ROOT / "judgments_eval_gemma.jsonl", "gemma-sft-guided"),
    ("gemma-sft-dpo", ROOT / "judgments_eval_gemma.jsonl", "gemma-sft-dpo"),
    ("gemma-sft-bf16", ROOT / "judgments_eval_gemma.jsonl", "gemma-sft-guided-bf16"),
    ("gemma-sftdpo-bf16", ROOT / "judgments_eval_gemma.jsonl", "gemma-sft-dpo-bf16"),
]

print(f"Held-out test-70, unstated, judge={OPUS}, display scale -1..+1\n")
print(f"{'arm':<18} {'turn1':<26} {'post-pressure':<26} {'Δ':<8}")
for label, path, subject in ARMS:
    if not path.exists():
        print(f"{label:<18} (no judgments yet)")
        continue
    scopes = collect_bands(path, subject)
    r1 = mean_ci(scopes["turn1"])
    rf = mean_ci(scopes["full"])
    if not r1 or not rf:
        print(f"{label:<18} (no judgments yet)")
        continue
    d = rf[0] - r1[0]
    print(f"{label:<18} {r1[0]:+.3f} [{r1[1]:+.3f},{r1[2]:+.3f}]  "
          f"{rf[0]:+.3f} [{rf[1]:+.3f},{rf[2]:+.3f}]  {d:+.3f}   (n={rf[3]})")

# ===== as-run: paired_sftdpo_bf16.py =====
"""Paired per-cell comparisons for the bf16 stage-2 run (issue #21).

Cells are (probe, pressure) on the Opus test-70 judgments, unstated framing,
matched exactly between arms; scenario-cluster bootstrap (5000 resamples) on
the per-cell band deltas, display scale x0.5 (-1..+1).

Comparisons:
  1. gemma-sft-dpo-bf16 vs gemma-sft-guided-bf16  (stage-2 gain, bf16 chain)
  2. gemma-sft-dpo-bf16 vs gemma-sft-dpo          (bf16 vs nf4 stage 2)

Run: python3 tmp/dpo-experiment/paired_sftdpo_bf16.py
"""

import collections
import json
import pathlib
import random

ROOT = pathlib.Path(__file__).resolve().parent
OPUS = "claude-opus-4-8"

split = json.loads((ROOT / "split_70_70.json").read_text())
TEST = set(split["test"])


def bands(subject):
    out = {}
    for line in open(ROOT / "judgments_eval_gemma.jsonl"):
        j = json.loads(line)
        if (j["subject"] == subject and j["judge"] == OPUS
                and j["framing"] == "unstated" and j["probe_id"] in TEST):
            out[(j["probe_id"], j["pressure"], j["scope"])] = j["band"]
    return out


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
    return m, boots[125], boots[4875], len(vals)


sftdpo = bands("gemma-sft-dpo-bf16")
sft = bands("gemma-sft-guided-bf16")
nf4 = bands("gemma-sft-dpo")

for label, a, b in [
    ("sftdpo-bf16 vs sft-bf16 (stage-2 gain)", sftdpo, sft),
    ("sftdpo-bf16 vs sft-dpo nf4 (precision)", sftdpo, nf4),
]:
    print(label)
    for scope in ("turn1", "full"):
        m, lo, hi, n = paired(a, b, scope)
        print(f"  {scope:<6} {m:+.3f} [{lo:+.3f},{hi:+.3f}]  (n={n})")
    print()

# ===== as-run: paired_small_sweep.py =====
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
