"""Stage-2 pairs: max-gap both-direction anchored pairs from the SFT policy's
OWN sampled chains (issue #21 SL-CAI stage 2).

Pool per train-70 cell = the 4 chains sampled from gemma-sft-guided at T=1.3,
Gemini-banded (judgments_sft2_samples.jsonl). The base-model main-run lane is
deliberately excluded — it is off-policy for the SFT policy, and stage 2's
premise is on-policy contrast with the SFT model as reference. Pairing rule
matches build_maxgap_pairs.py: every chain anchors up to two pairs (most-
differently-banded chain above / below it), gap >= 2 native, deduped;
dangling-[n]-citation screen on chosen sides.

Run: python3 tmp/dpo-experiment/build_sft2_pairs.py
"""

import collections
import hashlib
import json
import pathlib
import re

MARKER = re.compile(r"\[\d+\]")
RESOLVES = re.compile(r"(?im)^(\*{0,2}(references|sources|citations)\b|\[\d+\]\s*[A-Z؀-ۿ])")


def dangling_markers(turns) -> bool:
    text = turns[1]["content"] + "\n" + turns[3]["content"]
    return bool(MARKER.search(text)) and not RESOLVES.search(text)


ROOT = pathlib.Path(__file__).resolve().parent
GEMINI = "gemini-3.1-pro-preview"
MIN_GAP = 2

split = json.loads((ROOT / "split_70_70.json").read_text())
TRAIN = set(split["train"])

bands: dict = collections.defaultdict(dict)
for line in open(ROOT / "judgments_sft2_samples.jsonl"):
    j = json.loads(line)
    if (j["judge"] == GEMINI and j["framing"] == "unstated"
            and j["scope"] == "full" and j["probe_id"] in TRAIN):
        bands[(j["probe_id"], j["pressure"])][j["subject"]] = j["band"]

sittings: dict = {}
for line in open(ROOT / "collect_sft2_samples.jsonl"):
    r = json.loads(line)
    sittings[(r["probe_id"], r["pressure"], r["subject"])] = r["turns"]

pairs = []
stats = collections.Counter()
band_hist = collections.Counter()
seen = set()

for (probe, pressure), lanes in sorted(bands.items()):
    havers = {s: b for s, b in lanes.items() if (probe, pressure, s) in sittings}
    for b in havers.values():
        band_hist[b] += 1
    emitted = False
    for anchor in sorted(havers):
        ab = havers[anchor]
        above = [s for s, b in havers.items() if b - ab >= MIN_GAP]
        below = [s for s, b in havers.items() if ab - b >= MIN_GAP]
        cands = []
        if above:
            top = max(havers[s] for s in above)
            cands.append((sorted(s for s in above if havers[s] == top)[0], anchor))
        if below:
            bot = min(havers[s] for s in below)
            cands.append((anchor, sorted(s for s in below if havers[s] == bot)[0]))
        for ch, rj in cands:
            key = (probe, pressure, ch, rj)
            if key in seen:
                continue
            seen.add(key)
            if dangling_markers(sittings[(probe, pressure, ch)]):
                stats["chosen_screened_dangling"] += 1
                continue
            pairs.append({
                "probe_id": probe, "pressure": pressure,
                "chosen_subject": ch, "rejected_subject": rj,
                "chosen_band": havers[ch], "rejected_band": havers[rj],
                "chosen_cites": None, "rejected_is_inkling": False,
                "chosen_turns": sittings[(probe, pressure, ch)],
                "rejected_turns": sittings[(probe, pressure, rj)],
            })
            stats["pair"] += 1
            stats[f"chosen_band={havers[ch]}"] += 1
            emitted = True
    stats["cells_covered" if emitted else "cells_no_spread"] += 1

out = ROOT / "pairs_train70_sft2.jsonl"
with open(out, "w") as fh:
    for p in pairs:
        fh.write(json.dumps(p, sort_keys=True) + "\n")

print(f"pairs: {stats['pair']}  cells covered: {stats['cells_covered']}/{len(bands)}"
      f"  no-spread: {stats['cells_no_spread']}"
      f"  dangling-screened: {stats['chosen_screened_dangling']}")
print("band histogram (all SFT chains):", dict(sorted(band_hist.items())))
print("chosen-band mix:", {k.split("=")[1]: v for k, v in sorted(stats.items())
                           if k.startswith("chosen_band=")})
print("sha256:", hashlib.sha256(out.read_bytes()).hexdigest())
