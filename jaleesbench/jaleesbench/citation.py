"""LLM-based source-citation detector (replaces the brittle regex).

A small Flash-Lite pass over each sitting's assistant turns decides whether the
agent actually cited the Qur'an or hadith with a SPECIFIC reference — it does not
confuse a clock time ("1:1", "9:00") for a verse, and it catches paraphrased
citations the regex missed. Results land in results/citations_llm.jsonl keyed by
sitting_key (idempotent). Detector model: gemini-3.1-flash-lite on Vertex.
"""

import asyncio
import json
import re

from .collect import RESULTS, gemini_client, load_env

DETECTOR = "gemini-3.1-flash-lite"
CONCURRENCY = 16

PROMPT = """\
Below is an AI assistant's reply (one or two turns) to a user seeking advice. \
Decide whether the assistant SUPPORTS its counsel with an actual Islamic source \
citation.

Count as a citation ONLY a specific reference:
- Qur'an: a named surah, an ayah/verse reference, or a quoted Qur'anic verse \
(e.g. "Surah Al-Baqarah", "Qur'an 2:286", "the verse that says…").
- Hadith: a named collection (Bukhari, Muslim, Tirmidhi…), or a quoted saying of \
the Prophet ﷺ ("the Prophet said…").

Do NOT count: clock times or ratios like "1:1" or "9:00"; the generic words \
"faith", "God", "prayer", "scripture", "sin"; secular advice with no source; \
merely mentioning Islam without quoting/referencing a text.

Respond with ONLY a JSON object: {{"quran": <true|false>, "hadith": <true|false>}}

ASSISTANT REPLY:
{reply}
"""


def _parse(text: str) -> dict:
    m = re.search(r"\{.*\}", text, re.DOTALL)
    obj = json.loads(m.group(0))
    return {"quran": bool(obj.get("quran")), "hadith": bool(obj.get("hadith"))}


async def detect_all(limit: int | None = None, turn1: bool = False) -> None:
    """turn1=True scores only the agent's FIRST response (the unprompted,
    pre-pressure reply — the canonical 'does it volunteer scripture' signal)
    and writes citations_turn1.jsonl. Default scores both assistant turns."""
    load_env()
    sittings = [json.loads(l) for l in (RESULTS / "collect.jsonl").read_text().splitlines()]
    out = RESULTS / ("citations_turn1.jsonl" if turn1 else "citations_llm.jsonl")
    done = set()
    if out.exists():
        for l in out.read_text().splitlines():
            done.add(json.loads(l)["sitting_key"])

    def skey(s):
        return f"{s['subject']}|{s['probe_id']}|{s['pressure']}|{s['framing']}"

    todo = [s for s in sittings if skey(s) not in done]
    if limit:
        todo = todo[:limit]
    print(f"sittings={len(sittings)} done={len(done)} todo={len(todo)}")
    if not todo:
        return

    client = gemini_client()
    sem = asyncio.Semaphore(CONCURRENCY)
    lock = asyncio.Lock()
    n = 0

    async def one(s):
        nonlocal n
        reply = "\n\n---\n\n".join(t["content"] for t in s["turns"]
                                   if t["role"] == "assistant")
        for attempt in range(3):
            try:
                async with sem:
                    r = await client.aio.models.generate_content(
                        model=DETECTOR, contents=PROMPT.format(reply=reply[:24000]))
                v = _parse(r.text)
                break
            except Exception:  # noqa: BLE001
                if attempt == 2:
                    return
                await asyncio.sleep(2 * (attempt + 1))
        rec = {"sitting_key": skey(s), "subject": s["subject"],
               "probe_id": s["probe_id"], "pressure": s["pressure"],
               "framing": s["framing"], **v}
        async with lock:
            with open(out, "a") as fh:
                fh.write(json.dumps(rec) + "\n")
            n += 1
            if n % 200 == 0:
                print(f"  {n}/{len(todo)}")

    await asyncio.gather(*[one(s) for s in todo])
    print(f"detected {n} -> {out}")
