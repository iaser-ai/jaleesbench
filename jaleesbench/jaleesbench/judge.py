"""Score collected sittings: both judges, both turns, blinded to framing."""

import asyncio
import json
import re
from pathlib import Path

from .collect import RESULTS, RETRIES, load_env, load_probes
from .prompts import judge_user_message, render_conversation

JUDGES = {
    "claude-opus-4-8": "anthropic",
    "gemini-3.1-pro-preview": "gemini",
}

JUDGE_MAX_TOKENS = 4096
CONCURRENCY = 8

TECHNIQUES = {
    "reads the person", "engages reason", "gentleness with the struggling",
    "gradualism", "exit ramp", "proportion", "open door",
}


def parse_judgment(text: str) -> dict:
    m = re.search(r"\{.*\}", text, re.DOTALL)
    if not m:
        raise ValueError(f"no JSON object in judge output: {text[:200]!r}")
    obj = json.loads(m.group(0))
    band = obj["band"]
    if not isinstance(band, int) or not -2 <= band <= 2:
        raise ValueError(f"invalid band: {band!r}")
    techniques = obj.get("techniques_used", [])
    unknown = [t for t in techniques if t not in TECHNIQUES]
    if unknown:
        raise ValueError(f"unknown techniques: {unknown}")
    return {"band": band, "direction": obj.get("direction", ""),
            "techniques_used": techniques}


async def call_judge(judge: str, prompt: str, clients: dict) -> dict:
    provider = JUDGES[judge]
    last_err = None
    for attempt in range(RETRIES + 1):
        try:
            if provider == "anthropic":
                resp = await clients["anthropic"].messages.create(
                    model=judge, max_tokens=JUDGE_MAX_TOKENS,
                    messages=[{"role": "user", "content": prompt}])
                text = "".join(b.text for b in resp.content if b.type == "text")
                usage = {"in": resp.usage.input_tokens, "out": resp.usage.output_tokens}
            else:
                resp = await clients["gemini"].aio.models.generate_content(
                    model=judge, contents=prompt)
                text = resp.text
                um = resp.usage_metadata
                usage = {"in": um.prompt_token_count or 0,
                         "out": (um.candidates_token_count or 0)
                                + (getattr(um, "thoughts_token_count", 0) or 0)}
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


async def judge_all(limit: int | None = None) -> None:
    from anthropic import AsyncAnthropic
    from google import genai

    load_env()
    sittings_path = RESULTS / "collect.jsonl"
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
        for judge in JUDGES:
            for scope in ["turn1", "full"]:
                if f"{skey}|{judge}|{scope}" not in done:
                    jobs.append((s, skey, judge, scope))
    if limit:
        jobs = jobs[:limit]
    print(f"sittings={len(sittings)} judgments_done={len(done)} todo={len(jobs)}")
    if not jobs:
        return

    clients = {"anthropic": AsyncAnthropic(), "gemini": genai.Client()}
    sem = asyncio.Semaphore(CONCURRENCY)
    lock = asyncio.Lock()
    completed = 0

    async def one(job):
        nonlocal completed
        s, skey, judge, scope = job
        probe = probes[s["probe_id"]]
        turns = s["turns"][:2] if scope == "turn1" else s["turns"]
        # v3: boundary + deliverable-classification rules are now standard.
        prompt = judge_user_message(probe["proof_texts"], render_conversation(turns),
                                    v2=True)
        async with sem:
            verdict = await call_judge(judge, prompt, clients)
        rec = {"sitting_key": skey, "subject": s["subject"], "probe_id": s["probe_id"],
               "pressure": s["pressure"], "framing": s["framing"],
               "judge": judge, "scope": scope, **verdict}
        async with lock:
            with open(out_path, "a") as fh:
                fh.write(json.dumps(rec) + "\n")
            completed += 1
            if completed % 50 == 0:
                print(f"  {completed}/{len(jobs)}")

    await asyncio.gather(*[one(j) for j in jobs])
    print(f"judged {completed} -> {out_path}")


async def rejudge_disagreements(limit: int | None = None) -> None:
    """Re-judge cells where the two judges disagreed by >=2 bands, using the
    v2 boundary-rules prompt. Writes judgments_v2.jsonl (idempotent)."""
    from anthropic import AsyncAnthropic
    from google import genai

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

    clients = {"anthropic": AsyncAnthropic(), "gemini": genai.Client()}
    sem = asyncio.Semaphore(CONCURRENCY)
    lock = asyncio.Lock()
    completed = 0

    async def one(job):
        nonlocal completed
        key, skey, judge = job
        subject, probe_id, pressure, framing, scope = key
        s = sittings[(subject, probe_id, pressure, framing)]
        turns = s["turns"][:2] if scope == "turn1" else s["turns"]
        prompt = judge_user_message(probes[probe_id]["proof_texts"],
                                    render_conversation(turns), v2=True)
        async with sem:
            verdict = await call_judge(judge, prompt, clients)
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
