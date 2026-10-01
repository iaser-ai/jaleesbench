"""SL-CAI stage-1 dataset: gemma's own good GUIDED responses, re-rendered as
unstated conversations (issue #21, Waleed's 08-04 call).

Context distillation: input = the unstated conversation (guide context_prefix
dropped — it lives outside the turns, so the transform is exact); target =
gemma's own guided assistant turns. Selection on Gemini full-scope band >= +1
(selection judge; Opus stays held out). Screens: explicit references to the
instruction context (persona adoption is the target behavior and is NOT
screened), and dangling-[n]-citation style.

Run: uv run --directory jaleesbench python ../tmp/dpo-experiment/build_sft_guided.py
"""

import collections
import hashlib
import json
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parent
RESULTS = pathlib.Path("results")
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


split = json.loads((ROOT / "split_70_70.json").read_text())
TRAIN = set(split["train"])

bands: dict = {}
turn1_bands: dict = {}
for line in open(RESULTS / "judgments.jsonl"):
    j = json.loads(line)
    if (j["judge"] == GEMINI and j["framing"] == "guided"
            and j["subject"] == "gemma-4-31b" and j["probe_id"] in TRAIN):
        if j["scope"] == "full":
            bands[(j["probe_id"], j["pressure"])] = j["band"]
        else:
            turn1_bands[(j["probe_id"], j["pressure"])] = j["band"]

rows = []
stats = collections.Counter()
t1_hist = collections.Counter()
with open(RESULTS / "collect.jsonl") as fh:
    for line in fh:
        r = json.loads(line)
        if (r["framing"] != "guided" or r["subject"] != "gemma-4-31b"
                or r["probe_id"] not in TRAIN):
            continue
        key = (r["probe_id"], r["pressure"])
        b = bands.get(key)
        if b is None or b < 1:
            stats["band_below_1"] += 1
            continue
        # Both assistant turns carry loss — a sitting whose opening counsel is
        # bad (turn1 band < +1) would teach that opening even if the sitting
        # recovers post-pressure.
        if (turn1_bands.get(key) or -2) < 1:
            stats["turn1_below_1"] += 1
            continue
        text = r["turns"][1]["content"] + "\n" + r["turns"][3]["content"]
        m = GUIDE_REF.search(text)
        if m:
            stats["guide_ref_screened"] += 1
            stats[f"ref:{m.group(0).lower()}"] += 1
            continue
        if dangling_markers(r["turns"]):
            stats["dangling_screened"] += 1
            continue
        t1_hist[turn1_bands.get(key)] += 1
        rows.append({
            "probe_id": r["probe_id"], "pressure": r["pressure"],
            "band": b, "turn1_band": turn1_bands.get(key),
            "turns": r["turns"],
        })
        stats["kept"] += 1

out = ROOT / "sft_train_guided.jsonl"
with open(out, "w") as fh:
    for row in sorted(rows, key=lambda x: (x["probe_id"], x["pressure"])):
        fh.write(json.dumps(row, sort_keys=True) + "\n")

print(f"kept: {stats['kept']}  band<1: {stats['band_below_1']}"
      f"  guide-ref screened: {stats['guide_ref_screened']}"
      f"  dangling screened: {stats['dangling_screened']}")
print("screened phrases:", {k[4:]: v for k, v in stats.items() if k.startswith("ref:")})
print("turn1-band histogram of kept:", dict(sorted(t1_hist.items(), key=str)))
print("sha256:", hashlib.sha256(out.read_bytes()).hexdigest())
