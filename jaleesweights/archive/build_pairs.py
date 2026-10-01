"""Build DPO pairs for issue #21 from the existing JaleesBench main run.

Selection judge: Gemini only (Opus is held out for eval). Unstated framing,
train-70 scenarios, post-pressure scope. A pair lives inside one
(probe, pressure) cell: chosen = a subject's full sitting with Gemini band
>= +1, rejected = a subject's sitting with Gemini band <= 0. The completion
is the whole sitting after the shared opening user turn; the authored
pressure turn inside it is emitted as a separate masked span.

Run: uv run --directory jaleesbench python ../tmp/dpo-experiment/build_pairs.py
"""

import collections
import hashlib
import json
import pathlib
import random
import re

MARKER = re.compile(r"\[\d+\]")
RESOLVES = re.compile(r"(?im)^(\*{0,2}(references|sources|citations)\b|\[\d+\]\s*[A-Z؀-ۿ])")


def dangling_markers(turns) -> bool:
    """True when a sitting cites [n]-style markers that never resolve in-turn.

    Training on these teaches the model to emit reference markers with no
    referent — fabricated-citation style (issue #21 guard).
    """
    text = turns[1]["content"] + "\n" + turns[3]["content"]
    return bool(MARKER.search(text)) and not RESOLVES.search(text)

ROOT = pathlib.Path(__file__).resolve().parent
RESULTS = pathlib.Path("results")

GEMINI = "gemini-3.1-pro-preview"
MIN_GAP = 2  # chosen band minus rejected band, on the -2..+2 native scale

# Ansari is retrieval-backed (RAG): its counsel leans on retrieved sources the
# tuned model won't have, which both teaches unbacked-citation style and
# muddies the weights-vs-guide claim. Excluded from BOTH sides of every pair.
# fanar-sadiq is retrieval-backed too (same ruling as Ansari) — excluded on
# Waleed's 08-03 call. Post-dates the frozen inkling pair files, which no
# longer byte-reproduce anyway (judgments.jsonl gained fanar/sadiq rows).
SUBJECT_EXCLUDE = {"ansari", "fanar-sadiq"}

split = json.loads((ROOT / "split_70_70.json").read_text())
TRAIN = set(split["train"])

# --- Gemini post-pressure bands, unstated, train scenarios ------------------
bands: dict = collections.defaultdict(dict)  # (probe, pressure) -> subject -> band
with open(RESULTS / "judgments.jsonl") as fh:
    for line in fh:
        j = json.loads(line)
        if (
            j["judge"] == GEMINI
            and j["framing"] == "unstated"
            and j["scope"] == "full"
            and j["probe_id"] in TRAIN
        ):
            bands[(j["probe_id"], j["pressure"])][j["subject"]] = j["band"]

# --- Citation flags (presence, not verification) ----------------------------
cites: dict = {}
with open(RESULTS / "citations_llm.jsonl") as fh:
    for line in fh:
        c = json.loads(line)
        if c["framing"] == "unstated" and c["probe_id"] in TRAIN:
            cites[(c["probe_id"], c["pressure"], c["subject"])] = {
                "quran": c["quran"],
                "hadith": c["hadith"],
            }

# --- Sittings (transcripts), streamed from the big collect file -------------
wanted = set()
for (probe, pressure), subs in bands.items():
    for sub in subs:
        wanted.add((probe, pressure, sub))

sittings: dict = {}
with open(RESULTS / "collect.jsonl") as fh:
    for line in fh:
        r = json.loads(line)
        key = (r["probe_id"], r["pressure"], r["subject"])
        if r["framing"] == "unstated" and key in wanted:
            sittings[key] = r["turns"]

# --- Pair assembly ----------------------------------------------------------
# EXPANDED = 0 reproduces the original one-pair-per-cell set byte-for-byte.
# EXPANDED = N > 0 emits every on-policy combo (chosen x target-rejected)
# plus up to N seeded off-policy combos per cell, chosen-diversified.
EXPANDED = int(__import__("os").environ.get("EXPANDED_PER_CELL", "0"))
# On-policy target: whose rejected sittings anchor the pairs. Defaults to
# inkling (original experiment); gemma-4-31b for the hedge arm.
TARGET = __import__("os").environ.get("TARGET_SUBJECT", "inkling")

pairs = []
stats = collections.Counter()
rng = random.Random(split["seed"])


def emit(probe, pressure, havers, ch, rj):
    pairs.append(
        {
            "probe_id": probe,
            "pressure": pressure,
            "chosen_subject": ch,
            "rejected_subject": rj,
            "chosen_band": havers[ch],
            "rejected_band": havers[rj],
            "chosen_cites": cites.get((probe, pressure, ch)),
            "rejected_is_inkling": rj == "inkling",
            "chosen_turns": sittings[(probe, pressure, ch)],
            "rejected_turns": sittings[(probe, pressure, rj)],
        }
    )
    stats["pair"] += 1
    stats[f"rejected={rj}"] += 1
    stats[f"chosen={ch}"] += 1


for (probe, pressure), subs in sorted(bands.items()):
    havers = {
        s: b for s, b in subs.items()
        if s not in SUBJECT_EXCLUDE and (probe, pressure, s) in sittings
    }
    clean = {
        s: b for s, b in havers.items()
        if not (b >= 1 and dangling_markers(sittings[(probe, pressure, s)]))
    }
    stats["chosen_screened_dangling"] += len(havers) - len(clean)
    rejected_pool = sorted(
        (s for s, b in havers.items() if b <= 0),
        key=lambda s: (havers[s], s),
    )

    if not EXPANDED:
        top = max((b for b in clean.values() if b >= 1), default=None)
        chosen_pool = sorted(s for s, b in clean.items() if b == top)
        if top is None or not rejected_pool:
            stats["cell_no_pair"] += 1
            continue
        # One pair per cell. Chosen: seeded draw among the tied top-band
        # subjects (an alphabetical tie-break made the set 86% Ansari —
        # citation-heavy retrieval style Inkling can't back, so diversify).
        # Rejected: Inkling whenever its own response qualifies (on-policy),
        # else the worst band.
        ch = rng.choice(chosen_pool)
        rj = TARGET if havers.get(TARGET, 1) <= 0 else rejected_pool[0]
        if havers[ch] - havers[rj] < MIN_GAP:
            stats["cell_gap_too_small"] += 1
            continue
        emit(probe, pressure, havers, ch, rj)
        continue

    chosen_pool = sorted(s for s, b in clean.items() if b >= 1)
    combos = [
        (c, r)
        for c in chosen_pool
        for r in rejected_pool
        if havers[c] - havers[r] >= MIN_GAP
    ]
    if not combos:
        stats["cell_no_pair"] += 1
        continue
    on_policy = [x for x in combos if x[1] == TARGET]
    off_policy = [x for x in combos if x[1] != TARGET]
    rng.shuffle(off_policy)
    for ch, rj in on_policy + off_policy[:EXPANDED]:
        emit(probe, pressure, havers, ch, rj)

suffix = f"_expanded{EXPANDED}" if EXPANDED else ""
if TARGET != "inkling":
    suffix = f"_{TARGET}{suffix}"
out = ROOT / f"pairs_train70{suffix}.jsonl"
with open(out, "w") as fh:
    for p in pairs:
        fh.write(json.dumps(p, sort_keys=True) + "\n")

sha = hashlib.sha256(out.read_bytes()).hexdigest()
print(f"pairs: {stats['pair']}  no-pair cells: {stats['cell_no_pair']}"
      f"  gap-too-small: {stats['cell_gap_too_small']}")
print("rejected side:", {k.split("=")[1]: v for k, v in stats.items() if k.startswith("rejected=")})
print("chosen side:", {k.split("=")[1]: v for k, v in stats.items() if k.startswith("chosen=")})
print("sha256:", sha)
