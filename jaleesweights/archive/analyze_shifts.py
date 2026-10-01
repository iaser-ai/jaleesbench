"""Per-example shift analysis (issue #21): which test cells move under each
gemma DPO arm, and which get worse.

Cell-level paired comparison on the Opus test-70 judgments: base band vs
tuned band per (probe, pressure), both scopes, native -2..+2 bands.

Run: python3 tmp/dpo-experiment/analyze_shifts.py
"""

import collections
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent
RESULTS = pathlib.Path("jaleesbench/results")
OPUS = "claude-opus-4-8"

split = json.loads((ROOT / "split_70_70.json").read_text())
TEST = set(split["test"])


def bands(path, subject):
    out = {}
    for line in open(path):
        j = json.loads(line)
        if (j["subject"] == subject and j["judge"] == OPUS
                and j["framing"] == "unstated" and j["probe_id"] in TEST):
            out[(j["probe_id"], j["pressure"], j["scope"])] = j["band"]
    return out


base = bands(RESULTS / "judgments.jsonl", "gemma-4-31b")
arms = {
    "r1-offpol": bands(ROOT / "judgments_eval_gemma.jsonl", "gemma-dpo-r1"),
    "onpol": bands(ROOT / "judgments_eval_gemma.jsonl", "gemma-dpo-onpol"),
}

for name, arm in arms.items():
    for scope in ("full", "turn1"):
        deltas = collections.Counter()
        moved = []
        for key, b in base.items():
            if key[2] != scope or key not in arm:
                continue
            d = arm[key] - b
            deltas[d] += 1
            if d:
                moved.append((d, key[0], key[1], b, arm[key]))
        n = sum(deltas.values())
        same = deltas[0]
        up = sum(v for k, v in deltas.items() if k > 0)
        down = sum(v for k, v in deltas.items() if k < 0)
        print(f"\n=== {name} / {scope}: n={n}  unchanged={same} ({same/n:.0%})  "
              f"up={up}  down={down}")
        print("delta histogram:", dict(sorted(deltas.items())))
        by_press = collections.defaultdict(lambda: [0, 0])
        for d, _, press, _, _ in moved:
            by_press[press][0 if d > 0 else 1] += 1
        print("moved by pressure (up/down):",
              {p: tuple(v) for p, v in sorted(by_press.items())})
        if scope == "full":
            moved.sort()
            print("worst shifts (base->arm):")
            for d, probe, press, b, a in moved[:10]:
                print(f"  {probe} {press:<16} {b:+d} -> {a:+d}")
            print("best shifts (base->arm):")
            for d, probe, press, b, a in sorted(moved, reverse=True)[:10]:
                print(f"  {probe} {press:<16} {b:+d} -> {a:+d}")
