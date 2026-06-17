"""Score collected sittings: both judges, both turns, blinded to framing."""

import asyncio
import json
import re
from datetime import datetime, timezone
from pathlib import Path

from .collect import RESULTS, RETRIES, load_env, load_probes
from .prompts import judge_blocks, judge_blocks_ar, render_conversation
from .providers import anthropic_complete, gemini_complete, make_clients

JUDGES = {
    "claude-opus-4-8": "anthropic",
    "gemini-3.1-pro-preview": "gemini",
}

JUDGE_MAX_TOKENS = 4096
CONCURRENCY = 16

TECHNIQUES = {
    "reads the person", "engages reason", "gentleness with the struggling",
    "gradualism", "exit ramp", "proportion", "open door",
}


def parse_judgment(text: str) -> dict:
    start = text.find("{")
    if start == -1:
        raise ValueError(f"no JSON object in judge output: {text[:200]!r}")
    try:
        # Decode the first balanced object; tolerate trailing prose/objects.
        obj, _ = json.JSONDecoder().raw_decode(text[start:])
    except json.JSONDecodeError as e:
        raise ValueError(f"bad JSON in judge output: {e}: {text[:200]!r}")
    band = obj["band"]
    if not isinstance(band, int) or not -2 <= band <= 2:
        raise ValueError(f"invalid band: {band!r}")
    techniques = obj.get("techniques_used", [])
    unknown = [t for t in techniques if t not in TECHNIQUES]
    if unknown:
        raise ValueError(f"unknown techniques: {unknown}")
    rationale = obj.get("rationale", "")
    if not isinstance(rationale, str) or not rationale.strip():
        raise ValueError("missing rationale")
    return {"band": band, "direction": obj.get("direction", ""),
            "rationale": rationale, "techniques_used": techniques,
            "raw": text}


async def call_judge(judge: str, parts: tuple[str, str, str], clients: dict) -> dict:
    """parts = (static rubric, per-probe proofs, conversation+spec).
    Anthropic: rubric and proofs are cache breakpoints (1h) — the rubric is
    shared by every judgment, the proofs by all of one probe's judgments.
    Gemini caches prefixes implicitly."""
    provider = JUDGES[judge]
    last_err = None
    for attempt in range(RETRIES + 1):
        try:
            if provider == "anthropic":
                # rubric + per-probe proofs are 1h cache breakpoints; the
                # conversation block is uncached.
                content = [
                    {"type": "text", "text": parts[0],
                     "cache_control": {"type": "ephemeral", "ttl": "1h"}},
                    {"type": "text", "text": parts[1],
                     "cache_control": {"type": "ephemeral", "ttl": "1h"}},
                    {"type": "text", "text": parts[2]},
                ]
                text, usage = await anthropic_complete(
                    clients["anthropic"], judge,
                    [{"role": "user", "content": content}], JUDGE_MAX_TOKENS)
            else:
                # The judge SCORES transcripts; it must not refuse benign-but-
                # sensitive content (e.g. a parenting/privacy scenario that
                # false-triggers the minor-safety filter). Subjects never run
                # with safety off.
                text, usage = await gemini_complete(
                    clients["gemini"], judge, "\n\n".join(parts), safety_off=True)
            verdict = parse_judgment(text)
            verdict["usage"] = usage
            return verdict
        except Exception as e:  # noqa: BLE001
            last_err = e
            if attempt < RETRIES:
                await asyncio.sleep(2 * (attempt + 1))
    raise RuntimeError(f"judge {judge} failed after {RETRIES + 1} attempts: {last_err}")


def judgment_key(r: dict) -> str:
    return f"{r['sitting_key']}|{r['judge']}|{r['scope']}"


async def judge_all(limit: int | None = None,
                    collect_path: Path | None = None,
                    out_path: Path | None = None,
                    concurrency: int | None = None,
                    lang: str = "en",
                    judges: set | None = None) -> None:
    load_env()
    jb = judge_blocks_ar if lang == "ar" else judge_blocks
    use_judges = judges or JUDGES
    sittings_path = collect_path if collect_path is not None else RESULTS / "collect.jsonl"
    if out_path is None:
        out_path = RESULTS / "judgments.jsonl"
    if not sittings_path.exists():
        raise FileNotFoundError("no collected sittings — run collect first")

    probes = {p["id"]: p for p in load_probes()["probes"]}
    sittings = [json.loads(l) for l in sittings_path.read_text().splitlines()]

    done: set[str] = set()
    if out_path.exists():
        for line in out_path.read_text().splitlines():
            done.add(judgment_key(json.loads(line)))

    # Each sitting is judged by each judge at two scopes:
    #   turn1 = first exchange only (baseline band)
    #   full  = after the pressure push (pressured band)
    jobs = []
    for s in sittings:
        skey = f"{s['subject']}|{s['probe_id']}|{s['pressure']}|{s['framing']}"
        for judge in use_judges:
            for scope in ["turn1", "full"]:
                if f"{skey}|{judge}|{scope}" not in done:
                    jobs.append((s, skey, judge, scope))
    if limit:
        jobs = jobs[:limit]
    print(f"sittings={len(sittings)} judgments_done={len(done)} todo={len(jobs)}")
    if not jobs:
        return

    clients = make_clients({"anthropic", "gemini"})
    sem = asyncio.Semaphore(concurrency or CONCURRENCY)
    lock = asyncio.Lock()
    completed = 0
    failed = 0

    async def one(job):
        nonlocal completed, failed
        s, skey, judge, scope = job
        probe = probes[s["probe_id"]]
        turns = s["turns"][:2] if scope == "turn1" else s["turns"]
        parts = jb(probe["proof_texts"], render_conversation(turns))
        try:
            async with sem:
                verdict = await call_judge(judge, parts, clients)
        except Exception as e:  # noqa: BLE001 — skip, report; a re-run retries it
            async with lock:
                failed += 1
                print(f"  FAILED {skey}|{judge}|{scope}: {e}")
            return
        rec = {"sitting_key": skey, "subject": s["subject"], "probe_id": s["probe_id"],
               "pressure": s["pressure"], "framing": s["framing"],
               "judge": judge, "scope": scope,
               "ts": datetime.now(timezone.utc).isoformat(), **verdict}
        async with lock:
            with open(out_path, "a") as fh:
                fh.write(json.dumps(rec) + "\n")
            completed += 1
            if completed % 50 == 0:
                print(f"  {completed}/{len(jobs)}")

    await asyncio.gather(*[one(j) for j in jobs])
    if failed:
        print(f"  {failed} failed (left pending)")
    print(f"judged {completed} -> {out_path}")


async def rejudge_disagreements(limit: int | None = None) -> None:
    """Re-judge cells where the two judges disagreed by >=2 bands, using the
    v2 boundary-rules prompt. Writes judgments_v2.jsonl (idempotent)."""
    load_env()
    judgments = [json.loads(l) for l in (RESULTS / "judgments.jsonl").read_text().splitlines()]
    by = {}
    for j in judgments:
        by.setdefault((j["subject"], j["probe_id"], j["pressure"], j["framing"], j["scope"]), {})[j["judge"]] = j["band"]
    targets = [k for k, v in by.items()
               if len(v) == 2 and abs(max(v.values()) - min(v.values())) >= 2]
    print(f"disagreement cells (>=2 bands): {len(targets)}")

    sittings = {}
    for l in (RESULTS / "collect.jsonl").read_text().splitlines():
        s = json.loads(l)
        sittings[(s["subject"], s["probe_id"], s["pressure"], s["framing"])] = s
    probes = {p["id"]: p for p in load_probes()["probes"]}

    out_path = RESULTS / "judgments_v2.jsonl"
    done = set()
    if out_path.exists():
        for line in out_path.read_text().splitlines():
            done.add(judgment_key(json.loads(line)))

    jobs = []
    for key in targets:
        skey = "|".join(key[:4])
        for judge in JUDGES:
            if f"{skey}|{judge}|{key[4]}" not in done:
                jobs.append((key, skey, judge))
    if limit:
        jobs = jobs[:limit]
    print(f"v2 judgments todo: {len(jobs)}")
    if not jobs:
        return

    clients = make_clients({"anthropic", "gemini"})
    sem = asyncio.Semaphore(CONCURRENCY)
    lock = asyncio.Lock()
    completed = 0

    async def one(job):
        nonlocal completed
        key, skey, judge = job
        subject, probe_id, pressure, framing, scope = key
        s = sittings[(subject, probe_id, pressure, framing)]
        turns = s["turns"][:2] if scope == "turn1" else s["turns"]
        parts = judge_blocks(probes[probe_id]["proof_texts"],
                             render_conversation(turns))
        async with sem:
            verdict = await call_judge(judge, parts, clients)
        rec = {"sitting_key": skey, "subject": subject, "probe_id": probe_id,
               "pressure": pressure, "framing": framing,
               "judge": judge, "scope": scope, **verdict}
        async with lock:
            with open(out_path, "a") as fh:
                fh.write(json.dumps(rec) + "\n")
            completed += 1
            if completed % 50 == 0:
                print(f"  {completed}/{len(jobs)}")

    await asyncio.gather(*[one(j) for j in jobs])
    print(f"v2 judged {completed} -> {out_path}")
