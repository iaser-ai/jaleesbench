"""Inkling-Small SL stage-1 dataset: its own good GUIDED sittings rendered
unstated (JaleesWeights replication; mirrors build_sft_guided.py exactly —
same filters and screens, sources from the fresh stage-0 collections).

Run: python3 tmp/dpo-experiment/build_sft_small.py
"""

import collections
import hashlib
import json
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parent
GEMINI = "gemini-3.1-pro-preview"

MARKER = re.compile(r"\[\d+\]")
RESOLVES = re.compile(r"(?im)^(\*{0,2}(references|sources|citations)\b|\[\d+\]\s*[A-Z؀-ۿ])")
GUIDE_REF = re.compile(
    r"(?i)(context above|the context for this conversation|as instructed|"
    r"my instructions|my guidelines|the guide(?:lines)? (?:above|says|asks)|"
    r"i was (?:asked|told) to|per the (?:context|instructions))")


def dangling_markers(turns) -> bool:
    text = turns[1]["content"] + "\n" + turns[3]["content"]
    return bool(MARKER.search(text)) and not RESOLVES.search(text)


bands: dict = {}
turn1_bands: dict = {}
for line in open(ROOT / "judgments_small_selection.jsonl"):
    j = json.loads(line)
    if j["judge"] == GEMINI and j["framing"] == "guided" and j["subject"] == "inkling-small":
        key = (j["probe_id"], j["pressure"])
        if j["scope"] == "full":
            bands[key] = j["band"]
        else:
            turn1_bands[key] = j["band"]

band_hist = collections.Counter(bands.values())
rows = []
stats = collections.Counter()
for line in open(ROOT / "collect_small_train_guided.jsonl"):
    r = json.loads(line)
    key = (r["probe_id"], r["pressure"])
    b = bands.get(key)
    if b is None or b < 1:
        stats["band_below_1"] += 1
        continue
    if (turn1_bands.get(key) or -2) < 1:
        stats["turn1_below_1"] += 1
        continue
    text = r["turns"][1]["content"] + "\n" + r["turns"][3]["content"]
    if GUIDE_REF.search(text):
        stats["guide_ref_screened"] += 1
        continue
    if dangling_markers(r["turns"]):
        stats["dangling_screened"] += 1
        continue
    rows.append({"probe_id": r["probe_id"], "pressure": r["pressure"],
                 "band": b, "turn1_band": turn1_bands.get(key), "turns": r["turns"]})
    stats["kept"] += 1

out = ROOT / "sft_train_small.jsonl"
with open(out, "w") as fh:
    for row in sorted(rows, key=lambda x: (x["probe_id"], x["pressure"])):
        fh.write(json.dumps(row, sort_keys=True) + "\n")

print("guided band histogram (train-70, Gemini full):", dict(sorted(band_hist.items())))
print(f"kept: {stats['kept']}  band<1: {stats['band_below_1']}"
      f"  turn1<1: {stats['turn1_below_1']}"
      f"  guide-ref: {stats['guide_ref_screened']}  dangling: {stats['dangling_screened']}")
print("sha256:", hashlib.sha256(out.read_bytes()).hexdigest())
