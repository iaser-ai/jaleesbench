"""Batch judging at 50% batch pricing, both judges.

submit: enumerate pending judgments (same identity keys as the live judge),
submit Anthropic message batches + a Gemini batch file job, record state.
collect: poll, parse finished results into judgments.jsonl (same record shape
as the live judge, usage marked batch=True for the cost tables). Anything a
batch fails individually is simply left pending — the live `judge` command
remains the fallback and the identity keys make the two paths idempotent.
"""

import json
import time
from datetime import datetime, timezone
from pathlib import Path

from .collect import RESULTS, gemini_client, load_env, load_probes
from .judge import JUDGE_MAX_TOKENS, JUDGES, judgment_key, parse_judgment
from .prompts import judge_blocks, judge_blocks_ar, render_conversation

STATE = RESULTS / "batch_state.json"
ANTHROPIC_CHUNK = 10_000  # stay well under the 256MB batch cap


def _cfg(lang: str):
    """(collect_path, judgments_path, state_path, judge_blocks_fn) per variant."""
    if lang == "ar":
        return (RESULTS / "collect_ar.jsonl", RESULTS / "judgments_ar.jsonl",
                RESULTS / "batch_state_ar.json", judge_blocks_ar)
    return (RESULTS / "collect.jsonl", RESULTS / "judgments.jsonl",
            STATE, judge_blocks)


def _load_state(state_path: Path = STATE) -> dict:
    if state_path.exists():
        return json.loads(state_path.read_text())
    return {"anthropic": [], "gemini": []}


def _save_state(state: dict, state_path: Path = STATE) -> None:
    state_path.write_text(json.dumps(state, indent=1))


def _pending_jobs(collect_path: Path, jpath: Path,
                  state_path: Path) -> list[tuple[dict, str, str, str]]:
    """(sitting, skey, judge, scope) for every judgment not yet recorded
    and not already in a submitted batch manifest."""
    sittings = [json.loads(l) for l in collect_path.read_text().splitlines()]
    done = set()
    if jpath.exists():
        for line in jpath.read_text().splitlines():
            done.add(judgment_key(json.loads(line)))
    state = _load_state(state_path)
    # Only exclude manifests of batches STILL IN FLIGHT — a finished batch's
    # errored requests aren't in judgments.jsonl and must be re-eligible.
    for prov in ("anthropic", "gemini"):
        for b in state[prov]:
            if not b["done"]:
                done.update(b["manifest"].values())
    jobs = []
    for s in sittings:
        skey = f"{s['subject']}|{s['probe_id']}|{s['pressure']}|{s['framing']}"
        for judge in JUDGES:
            for scope in ["turn1", "full"]:
                if f"{skey}|{judge}|{scope}" not in done:
                    jobs.append((s, skey, judge, scope))
    return jobs


def _job_parts(probes: dict, s: dict, scope: str, jb=judge_blocks) -> tuple[str, str, str]:
    turns = s["turns"][:2] if scope == "turn1" else s["turns"]
    return jb(probes[s["probe_id"]]["proof_texts"], render_conversation(turns))


def submit(limit: int | None = None, lang: str = "en") -> None:
    import anthropic
    from google import genai
    from google.genai import types

    load_env()
    collect_path, jpath, state_path, jb = _cfg(lang)
    probes = {p["id"]: p for p in load_probes()["probes"]}
    jobs = _pending_jobs(collect_path, jpath, state_path)
    if limit:
        jobs = jobs[:limit]
    by_judge = {j: [x for x in jobs if x[2] == j] for j in JUDGES}
    print({j: len(v) for j, v in by_judge.items()})
    if not jobs:
        print("nothing pending")
        return
    state = _load_state(state_path)

    # Anthropic: chunked message batches with the same cached blocks as live.
    aclient = anthropic.Anthropic()
    opus_jobs = [x for j, v in by_judge.items() if JUDGES[j] == "anthropic" for x in v]
    for c0 in range(0, len(opus_jobs), ANTHROPIC_CHUNK):
        chunk = opus_jobs[c0:c0 + ANTHROPIC_CHUNK]
        manifest, requests = {}, []
        for i, (s, skey, judge, scope) in enumerate(chunk):
            parts = _job_parts(probes, s, scope, jb)
            cid = f"a{c0 + i:06d}"
            manifest[cid] = f"{skey}|{judge}|{scope}"
            requests.append({
                "custom_id": cid,
                "params": {
                    "model": judge, "max_tokens": JUDGE_MAX_TOKENS,
                    "messages": [{"role": "user", "content": [
                        {"type": "text", "text": parts[0],
                         "cache_control": {"type": "ephemeral", "ttl": "1h"}},
                        {"type": "text", "text": parts[1],
                         "cache_control": {"type": "ephemeral", "ttl": "1h"}},
                        {"type": "text", "text": parts[2]},
                    ]}],
                },
            })
        batch = aclient.messages.batches.create(requests=requests)
        state["anthropic"].append({"batch_id": batch.id, "manifest": manifest,
                                   "done": False})
        print(f"anthropic batch {batch.id}: {len(requests)} requests")

    # Gemini now runs on Vertex AI, whose batch API is GCS/BigQuery-based — the
    # developer-API file-batch used here does not exist there. So Gemini is NOT
    # batched: judge it live on Vertex with `jaleesbench judge` (which picks up
    # exactly these pending Gemini cells). Opus still batches at 50%.
    gem_jobs = [x for j, v in by_judge.items() if JUDGES[j] == "gemini" for x in v]
    if gem_jobs:
        print(f"gemini: {len(gem_jobs)} pending — NOT batched (Vertex has no "
              f"file-batch API); run `jaleesbench judge` to judge them live.")

    _save_state(state, state_path)


def _write_recs(recs: list[dict], jpath: Path = RESULTS / "judgments.jsonl") -> None:
    done = set()
    if jpath.exists():
        for line in jpath.read_text().splitlines():
            done.add(judgment_key(json.loads(line)))
    with open(jpath, "a") as fh:
        for r in recs:
            if judgment_key(r) not in done:
                fh.write(json.dumps(r, ensure_ascii=False) + "\n")


def _rec_from(jobkey: str, verdict: dict) -> dict:
    subject, probe_id, pressure, framing, judge, scope = jobkey.split("|")
    return {"sitting_key": f"{subject}|{probe_id}|{pressure}|{framing}",
            "subject": subject, "probe_id": probe_id, "pressure": pressure,
            "framing": framing, "judge": judge, "scope": scope,
            "ts": datetime.now(timezone.utc).isoformat(), **verdict}


def collect(lang: str = "en") -> None:
    import anthropic
    from google import genai

    load_env()
    _, jpath, state_path, _ = _cfg(lang)
    state = _load_state(state_path)
    open_batches = 0

    aclient = anthropic.Anthropic()
    for b in state["anthropic"]:
        if b["done"]:
            continue
        batch = aclient.messages.batches.retrieve(b["batch_id"])
        if batch.processing_status != "ended":
            print(f"anthropic {b['batch_id']}: {batch.processing_status} "
                  f"({batch.request_counts.processing} processing)")
            open_batches += 1
            continue
        recs, errored = [], 0
        for result in aclient.messages.batches.results(b["batch_id"]):
            if result.result.type != "succeeded":
                errored += 1
                continue
            msg = result.result.message
            text = "".join(x.text for x in msg.content if x.type == "text")
            try:
                verdict = parse_judgment(text)
            except ValueError:
                errored += 1  # left pending: live judge picks it up
                continue
            u = msg.usage
            verdict["usage"] = {
                "in": u.input_tokens, "out": u.output_tokens,
                "cache_write": getattr(u, "cache_creation_input_tokens", 0) or 0,
                "cache_read": getattr(u, "cache_read_input_tokens", 0) or 0,
                "batch": True}
            recs.append(_rec_from(b["manifest"][result.custom_id], verdict))
        _write_recs(recs, jpath)
        b["done"] = True
        print(f"anthropic {b['batch_id']}: wrote {len(recs)}, "
              f"left to live fallback {errored}")

    gclient = gemini_client()
    for b in state["gemini"]:
        if b["done"]:
            continue
        job = gclient.batches.get(name=b["job_name"])
        st = str(job.state)
        if "SUCCEEDED" not in st:
            if any(bad in st for bad in ("FAILED", "CANCELLED", "EXPIRED")):
                b["done"] = True  # terminal: leftovers go to live fallback
                print(f"gemini {b['job_name']}: {st} — leaving jobs to live judge")
            else:
                print(f"gemini {b['job_name']}: {st}")
                open_batches += 1
            continue
        content = gclient.files.download(file=job.dest.file_name).decode("utf-8")
        recs, errored = [], 0
        for line in content.splitlines():
            if not line.strip():
                continue
            obj = json.loads(line)
            try:
                resp = obj["response"]
                text = "".join(p.get("text", "")
                               for c in resp["candidates"]
                               for p in c["content"]["parts"])
                verdict = parse_judgment(text)
            except (KeyError, ValueError):
                errored += 1
                continue
            um = resp.get("usageMetadata", {})
            verdict["usage"] = {
                "in": um.get("promptTokenCount", 0),
                "out": (um.get("candidatesTokenCount", 0) or 0)
                       + (um.get("thoughtsTokenCount", 0) or 0),
                "batch": True}
            recs.append(_rec_from(b["manifest"][obj["key"]], verdict))
        _write_recs(recs, jpath)
        b["done"] = True
        print(f"gemini {b['job_name']}: wrote {len(recs)}, "
              f"left to live fallback {errored}")

    _save_state(state, state_path)
    if open_batches:
        print(f"{open_batches} batch(es) still processing")
    else:
        print("all batches done")
