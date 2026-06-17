"""Judge the Ansari steadfastness experiment (original vs modified prompt) and
compare. Reads the .mts run output, attaches each tuning probe's chapter proof
texts, judges turn-1 and full with both judges on the -1..+1 scale, and reports
steadfastness (full - turn1) per arm and pressure. Run: uv run python judge_tune.py
"""
import asyncio, json
from collections import defaultdict
from statistics import mean

from jaleesbench.collect import gemini_client, load_env
from jaleesbench.judge import JUDGES, call_judge
from jaleesbench.authoring import chapter_proofs
from jaleesbench.prompts import judge_blocks, render_conversation

RESULTS = "/Users/mwk/Development/cluesmith/ansari4/ansari-multisage/tmp/tune_results.jsonl"
SCALE = 0.5


async def main():
    load_env()
    from anthropic import AsyncAnthropic
    clients = {"anthropic": AsyncAnthropic(), "gemini": gemini_client()}
    proofs = json.loads(open("jaleesbench/proof_texts.json").read())
    rows = [json.loads(l) for l in open(RESULTS)]

    sem = asyncio.Semaphore(12)
    bands = {}  # (probe,pressure,arm,scope,judge) -> band

    async def one(r, scope):
        turns = r["turns"][:2] if scope == "turn1" else r["turns"]
        parts = judge_blocks(chapter_proofs(r["bab"], proofs), render_conversation(turns))
        for judge in JUDGES:
            async with sem:
                try:
                    v = await call_judge(judge, parts, clients)
                    bands[(r["probe_id"], r["pressure"], r["arm"], scope, judge)] = v["band"]
                except Exception as e:
                    print("  judge fail", r["probe_id"], r["pressure"], r["arm"], scope, judge, str(e)[:60])

    await asyncio.gather(*[one(r, sc) for r in rows for sc in ("turn1", "full")])

    def score(arm, pressure=None, scope="full"):
        vals = [b for (p, pr, a, sc, j), b in bands.items()
                if a == arm and sc == scope and (pressure is None or pr == pressure)]
        return mean(vals) * SCALE if vals else None

    print("\n=== Ansari steadfastness: original vs modified prompt (−1..+1 scale) ===")
    print(f"{'pressure':16s} {'arm':9s} {'turn1':>7s} {'full':>7s} {'Δ steadfast':>12s}")
    for pr in ["insistence", "personal_appeal", "secularize"]:
        for arm in ["original", "modified"]:
            t1, fl = score(arm, pr, "turn1"), score(arm, pr, "full")
            print(f"{pr:16s} {arm:9s} {t1:+.2f}  {fl:+.2f}  {fl - t1:+.2f}")
        print()
    print("OVERALL (all 3 weak pressures):")
    for arm in ["original", "modified"]:
        t1, fl = score(arm, None, "turn1"), score(arm, None, "full")
        print(f"  {arm:9s} turn1 {t1:+.2f} -> full {fl:+.2f}   steadfastness {fl - t1:+.2f}")
    oi = score("original", None, "full") - score("original", None, "turn1")
    mi = score("modified", None, "full") - score("modified", None, "turn1")
    print(f"\n  improvement in steadfastness (modified − original): {mi - oi:+.2f}")
    print(f"  improvement in post-pressure score (modified − original full): "
          f"{score('modified', None, 'full') - score('original', None, 'full'):+.2f}")

asyncio.run(main())
