"""Max-gap both-direction anchored pairs from pooled EXISTING gemma outputs
(issue #21, Waleed's design 08-04 — zero new generation or judging spend).

Pool per train-70 cell = 5 gemma outputs, all already Gemini-banded:
the main-run sitting (lane "gemma-main"; Friendli, default temp) + the 4 hot
chains (lanes gemma-onpol-s*; vLLM T1.3). Every output anchors up to two
pairs: (most-differently-banded output ABOVE it, anchor) and (anchor,
most-differently-banded output BELOW it), gap >= 2 native, deduped.

This is RELATIVE preference — no absolute chosen>=+1 threshold — so cells
whose best own output is a 0-band "least-bad" still teach a direction; the
317 no-chosen cells from the on-policy arm mostly re-enter coverage.
Dangling-[n]-citation screen applies to any chosen side.

Run: uv run --directory jaleesbench python ../tmp/dpo-experiment/build_maxgap_pairs.py
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
RESULTS = pathlib.Path("results")
GEMINI = "gemini-3.1-pro-preview"
MIN_GAP = 2

split = json.loads((ROOT / "split_70_70.json").read_text())
TRAIN = set(split["train"])

bands: dict = collections.defaultdict(dict)  # (probe, pressure) -> lane -> band
sittings: dict = {}

# hot chains
for line in open(ROOT / "judgments_train_samples.jsonl"):
    j = json.loads(line)
    if (j["judge"] == GEMINI and j["framing"] == "unstated"
            and j["scope"] == "full" and j["probe_id"] in TRAIN):
        bands[(j["probe_id"], j["pressure"])][j["subject"]] = j["band"]
for line in open(ROOT / "collect_train_samples.jsonl"):
    r = json.loads(line)
    sittings[(r["probe_id"], r["pressure"], r["subject"])] = r["turns"]

# main-run gemma output as a 5th lane
for line in open(RESULTS / "judgments.jsonl"):
    j = json.loads(line)
    if (j["judge"] == GEMINI and j["framing"] == "unstated" and j["scope"] == "full"
            and j["probe_id"] in TRAIN and j["subject"] == "gemma-4-31b"):
        bands[(j["probe_id"], j["pressure"])]["gemma-main"] = j["band"]
with open(RESULTS / "collect.jsonl") as fh:
    for line in fh:
        r = json.loads(line)
        if (r["framing"] == "unstated" and r["subject"] == "gemma-4-31b"
                and r["probe_id"] in TRAIN):
            sittings[(r["probe_id"], r["pressure"], "gemma-main")] = r["turns"]

pairs = []
stats = collections.Counter()
seen = set()

for (probe, pressure), lanes in sorted(bands.items()):
    havers = {s: b for s, b in lanes.items() if (probe, pressure, s) in sittings}
    stats[f"pool={len(havers)}"] += 1
    emitted_cell = False
    for anchor in sorted(havers):
        ab = havers[anchor]
        above = [s for s, b in havers.items() if b - ab >= MIN_GAP]
        below = [s for s, b in havers.items() if ab - b >= MIN_GAP]
        cands = []
        if above:
            top = max(havers[s] for s in above)
            ch = sorted(s for s in above if havers[s] == top)[0]
            cands.append((ch, anchor))
        if below:
            bot = min(havers[s] for s in below)
            rj = sorted(s for s in below if havers[s] == bot)[0]
            cands.append((anchor, rj))
        for ch, rj in cands:
            key = (probe, pressure, ch, rj)
            if key in seen:
                continue
            seen.add(key)
            if dangling_markers(sittings[(probe, pressure, ch)]):
                stats["chosen_screened_dangling"] += 1
                continue
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
            stats[f"chosen_band={havers[ch]}"] += 1
            emitted_cell = True
    if emitted_cell:
        stats["cells_covered"] += 1
    else:
        stats["cells_no_spread"] += 1

out = ROOT / "pairs_train70_gemma_maxgap.jsonl"
with open(out, "w") as fh:
    for p in pairs:
        fh.write(json.dumps(p, sort_keys=True) + "\n")

print(f"pairs: {stats['pair']}  cells covered: {stats['cells_covered']}/420"
      f"  no-spread cells: {stats['cells_no_spread']}"
      f"  dangling-screened: {stats['chosen_screened_dangling']}")
print("chosen-band mix:", {k.split("=")[1]: v for k, v in sorted(stats.items())
                           if k.startswith("chosen_band=")})
print("main-lane roles: chosen",
      sum(1 for p in pairs if p["chosen_subject"] == "gemma-main"),
      "rejected", sum(1 for p in pairs if p["rejected_subject"] == "gemma-main"))
print("sha256:", hashlib.sha256(out.read_bytes()).hexdigest())
