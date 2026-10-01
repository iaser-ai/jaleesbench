"""Build train-70 sampling inputs for the on-policy gemma arm (issue #21).

Same schema as eval_inputs_gemma.jsonl (probe_id, pressure, turn1,
pressure_text), but for TRAIN scenarios. Rows come from the main-run
collect.jsonl (unstated framing); the opening user turn and the authored
pressure turn must be identical across subjects within a cell — assert,
fail fast. Self-check: the same extraction over TEST must reproduce the
existing eval_inputs_gemma.jsonl row set exactly.

Run: uv run --directory jaleesbench python ../tmp/dpo-experiment/build_train_inputs.py
"""

import hashlib
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent
RESULTS = pathlib.Path("results")

split = json.loads((ROOT / "split_70_70.json").read_text())
TRAIN, TEST = set(split["train"]), set(split["test"])

buckets = {"train": {}, "test": {}}
with open(RESULTS / "collect.jsonl") as fh:
    for line in fh:
        r = json.loads(line)
        if r["framing"] != "unstated":
            continue
        side = "train" if r["probe_id"] in TRAIN else "test" if r["probe_id"] in TEST else None
        if side is None:
            continue
        row = {
            "probe_id": r["probe_id"],
            "pressure": r["pressure"],
            "turn1": r["turns"][0]["content"],
            "pressure_text": r["turns"][2]["content"],
        }
        key = (r["probe_id"], r["pressure"])
        prev = buckets[side].get(key)
        if prev is None:
            buckets[side][key] = row
        elif prev != row:
            raise RuntimeError(f"cell {key} differs across subjects ({r['subject']})")

for side, cells in buckets.items():
    if len(cells) != 420:
        raise RuntimeError(f"{side}: expected 420 cells, got {len(cells)}")

# Regeneration check: extraction over TEST == the file the r1/r2 evals used.
existing = [json.loads(l) for l in open(ROOT / "eval_inputs_gemma.jsonl")]
mine = {(r["probe_id"], r["pressure"]): r for r in existing}
if mine != buckets["test"]:
    raise RuntimeError("TEST extraction does not reproduce eval_inputs_gemma.jsonl")
print("self-check ok: TEST extraction reproduces eval_inputs_gemma.jsonl")

out = ROOT / "train_inputs_gemma.jsonl"
with open(out, "w") as fh:
    for key in sorted(buckets["train"]):
        fh.write(json.dumps(buckets["train"][key]) + "\n")
print(f"{len(buckets['train'])} rows -> {out}")
print("sha256:", hashlib.sha256(out.read_bytes()).hexdigest())
