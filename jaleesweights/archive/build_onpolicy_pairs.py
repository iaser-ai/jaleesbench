"""Build on-policy DPO pairs from gemma's own sampled chains (issue #21).

Both sides of every pair are the model's OWN text — the redesign targets the
implicated mechanism from the three flat arms (off-policy chosen taught
cross-model ranking, not behavior). Selection on Gemini post-pressure bands
(Opus held out). One pair per (probe, pressure) cell: chosen = highest-band
own sample with band >= +1 (seeded tie-break), rejected = lowest-band own
sample with band <= 0 (deterministic tie-break), gap >= 2 on the -2..+2
native scale, dangling-[n]-citation screen on the chosen side — the same
rules as build_pairs.py, sample lanes standing in for subjects.

Run: python tmp/dpo-experiment/build_onpolicy_pairs.py   (no repo imports)
"""

import collections
import hashlib
import json
import os
import pathlib
import random
import re

MARKER = re.compile(r"\[\d+\]")
RESOLVES = re.compile(r"(?im)^(\*{0,2}(references|sources|citations)\b|\[\d+\]\s*[A-Z؀-ۿ])")


def dangling_markers(turns) -> bool:
    text = turns[1]["content"] + "\n" + turns[3]["content"]
    return bool(MARKER.search(text)) and not RESOLVES.search(text)


ROOT = pathlib.Path(__file__).resolve().parent
GEMINI = "gemini-3.1-pro-preview"
MIN_GAP = 2

# EXPANDED=1 emits every qualifying (chosen x rejected) combo per cell —
# multiple pairs over one prompt is standard for on-policy DPO, and with a
# 58-cell yield it is what gets the corpus to a fair dose (179 pairs).
EXPANDED = bool(int(os.environ.get("EXPANDED", "0")))

split = json.loads((ROOT / "split_70_70.json").read_text())
TRAIN = set(split["train"])

bands: dict = collections.defaultdict(dict)  # (probe, pressure) -> lane -> band
for line in open(ROOT / "judgments_train_samples.jsonl"):
    j = json.loads(line)
    if (j["judge"] == GEMINI and j["framing"] == "unstated"
            and j["scope"] == "full" and j["probe_id"] in TRAIN):
        bands[(j["probe_id"], j["pressure"])][j["subject"]] = j["band"]

sittings: dict = {}
for line in open(ROOT / "collect_train_samples.jsonl"):
    r = json.loads(line)
    sittings[(r["probe_id"], r["pressure"], r["subject"])] = r["turns"]

pairs = []
stats = collections.Counter()
band_hist = collections.Counter()
rng = random.Random(split["seed"])

for (probe, pressure), lanes in sorted(bands.items()):
    havers = {s: b for s, b in lanes.items() if (probe, pressure, s) in sittings}
    for b in havers.values():
        band_hist[b] += 1
    clean = {s: b for s, b in havers.items()
             if not (b >= 1 and dangling_markers(sittings[(probe, pressure, s)]))}
    stats["chosen_screened_dangling"] += len(havers) - len(clean)

    top = max((b for b in clean.values() if b >= 1), default=None)
    rejected_pool = sorted((s for s, b in havers.items() if b <= 0),
                           key=lambda s: (havers[s], s))
    if top is None:
        stats["cell_no_chosen"] += 1
        continue
    if not rejected_pool:
        stats["cell_no_rejected"] += 1
        continue
    if EXPANDED:
        cands = [(c, r) for c in sorted(s for s, b in clean.items() if b >= 1)
                 for r in rejected_pool if clean[c] - havers[r] >= MIN_GAP]
        if not cands:
            stats["cell_gap_too_small"] += 1
            continue
    else:
        ch = rng.choice(sorted(s for s, b in clean.items() if b == top))
        rj = rejected_pool[0]
        if havers[ch] - havers[rj] < MIN_GAP:
            stats["cell_gap_too_small"] += 1
            continue
        cands = [(ch, rj)]
    for ch, rj in cands:
        pairs.append({
            "probe_id": probe,
            "pressure": pressure,
            "chosen_subject": ch,
            "rejected_subject": rj,
            "chosen_band": havers[ch],
            "rejected_band": havers[rj],
            "chosen_cites": None,
            "rejected_is_inkling": False,
            "chosen_turns": sittings[(probe, pressure, ch)],
            "rejected_turns": sittings[(probe, pressure, rj)],
        })
        stats["pair"] += 1

out = ROOT / ("pairs_train70_gemma_onpol_all.jsonl" if EXPANDED
              else "pairs_train70_gemma_onpol.jsonl")
with open(out, "w") as fh:
    for p in pairs:
        fh.write(json.dumps(p, sort_keys=True) + "\n")

n_cells = len(bands)
print(f"cells judged: {n_cells}  pairs: {stats['pair']}"
      f"  no-chosen: {stats['cell_no_chosen']}  no-rejected: {stats['cell_no_rejected']}"
      f"  gap-too-small: {stats['cell_gap_too_small']}"
      f"  dangling-screened: {stats['chosen_screened_dangling']}")
print("band histogram (all sampled chains):",
      dict(sorted(band_hist.items())))
print("sha256:", hashlib.sha256(out.read_bytes()).hexdigest())
