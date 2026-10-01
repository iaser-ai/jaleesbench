"""Export pairs_train70.jsonl to the tinker-cookbook LabeledComparison schema.

Prompt = the shared opening user turn. Completion = the rest of the sitting
(assistant turn-1, the authored pressure user turn, assistant turn-2); the
renderer masks user turns, so only assistant tokens carry loss. Which side
is A is a seeded coin flip per pair.

Run: uv run --directory jaleesbench python ../tmp/dpo-experiment/export_comparisons.py
"""

import hashlib
import json
import pathlib
import random
import sys

ROOT = pathlib.Path(__file__).resolve().parent
rng = random.Random(3446)
SRC = sys.argv[1] if len(sys.argv) > 1 else "pairs_train70.jsonl"

rows = []
for line in open(ROOT / SRC):
    p = json.loads(line)
    ch, rj = p["chosen_turns"], p["rejected_turns"]
    assert ch[0] == rj[0], f"prompt mismatch in {p['probe_id']}|{p['pressure']}"
    assert [t["role"] for t in ch] == ["user", "assistant", "user", "assistant"]
    assert [t["role"] for t in rj] == ["user", "assistant", "user", "assistant"]
    chosen_is_a = rng.random() < 0.5
    comp = {
        "prompt_conversation": [ch[0]],
        "completion_A": (ch if chosen_is_a else rj)[1:],
        "completion_B": (rj if chosen_is_a else ch)[1:],
    }
    rows.append({"comparison": comp, "label": "A" if chosen_is_a else "B"})

out = ROOT / SRC.replace("pairs_train70", "comparisons_train")
with open(out, "w") as fh:
    for r in rows:
        fh.write(json.dumps(r, sort_keys=True) + "\n")
labels = sum(1 for r in rows if r["label"] == "A")
print(f"{len(rows)} comparisons  label A: {labels}  label B: {len(rows) - labels}")
print("sha256:", hashlib.sha256(out.read_bytes()).hexdigest())
