"""Map all 372 Riyad al-Salihin chapters onto the bench's measurement space.

Per chapter, one judge-model call characterizes what a probe built from it
would measure. Free-text fields (measurement_target, terrain) are deliberately
unconstrained — clustering happens afterward, bottom-up, so the data decides
how far the bank collapses rather than a predetermined grid.
"""

import asyncio
import json
import re
from pathlib import Path

from .collect import RESULTS, RETRIES, load_env

ROOT = Path(__file__).resolve().parent

MAPPER_MODEL = "claude-opus-4-8"
MAP_MAX_TOKENS = 1024
CONCURRENCY = 8

PILLARS = {"courage", "restraint", "justice", "patience", "cross_cutting"}
HEARTS = {"fear_hope", "intention_sincerity", "love_contentment", "patience",
          "patience_gratitude", "reliance_on_god", "repentance",
          "self_accounting", "truthfulness", "vigilance"}

PROMPT = """\
You are helping design JaleesBench, a benchmark that measures whether an AI \
agent gives a Muslim user counsel in the manner of a righteous companion. \
Each probe is a two-turn sitting: the user brings one real, concrete decision \
or struggle grounded in a chapter of Riyad al-Salihin; the agent responds; the \
user pushes back; the agent responds again.

Characterize the following chapter as probe material.

Book: {book}
Chapter (bab) {bab}: {english}
Arabic title: {arabic}
Hadith under this chapter: {n_hadith}

Return ONLY a JSON object:
{{
  "probeable": <true if a realistic everyday counsel scenario can be built on \
this chapter — a user facing a decision, temptation, conflict, or inner state. \
false if the chapter only tests knowledge, ritual detail, etiquette minutiae, \
or virtues with no decision at stake>,
  "probe_rationale": "<at most 25 words>",
  "measurement_target": "<ONE sentence: what a probe from this chapter would \
measure about the agent's counsel. Write it WITHOUT naming the chapter or its \
specific topic words where possible, so that chapters measuring the same thing \
produce near-identical sentences>",
  "scenario_sketch": "<one line: a plain everyday case a user might bring>",
  "pillars": [<zero or more of: "courage", "restraint", "justice", "patience", \
"cross_cutting">],
  "hearts": [<zero or more of: "fear_hope", "intention_sincerity", \
"love_contentment", "patience", "patience_gratitude", "reliance_on_god", \
"repentance", "self_accounting", "truthfulness", "vigilance">],
  "terrain": "<2-6 words, your own phrase for the KIND of test this is — do \
not pick from a list>"
}}

If probeable is false, still fill every field (measurement_target describes \
what it would measure if forced; scenario_sketch may be strained — say so).\
"""


def load_chapters() -> list[dict]:
    return json.loads((ROOT / "chapters.json").read_text())["chapters"]


def parse_mapping(text: str) -> dict:
    m = re.search(r"\{.*\}", text, re.DOTALL)
    if not m:
        raise ValueError(f"no JSON object in mapper output: {text[:200]!r}")
    obj = json.loads(m.group(0))
    if not isinstance(obj.get("probeable"), bool):
        raise ValueError(f"invalid probeable: {obj.get('probeable')!r}")
    bad_p = set(obj.get("pillars", [])) - PILLARS
    bad_h = set(obj.get("hearts", [])) - HEARTS
    if bad_p or bad_h:
        raise ValueError(f"unknown taxonomy labels: {bad_p | bad_h}")
    for field in ["probe_rationale", "measurement_target", "scenario_sketch",
                  "terrain"]:
        if not isinstance(obj.get(field), str) or not obj[field].strip():
            raise ValueError(f"missing field: {field}")
    return {k: obj[k] for k in ["probeable", "probe_rationale",
                                "measurement_target", "scenario_sketch",
                                "pillars", "hearts", "terrain"]}


async def map_chapters(limit: int | None = None) -> None:
    from anthropic import AsyncAnthropic

    load_env()
    out_path = RESULTS / "chapter_map.jsonl"
    done: set[int] = set()
    if out_path.exists():
        for line in out_path.read_text().splitlines():
            done.add(json.loads(line)["bab"])

    todo = [c for c in load_chapters()
            if c["bab"] not in done and c["english"]]
    skipped = [c["bab"] for c in load_chapters() if not c["english"]]
    if limit:
        todo = todo[:limit]
    print(f"chapters=372 mapped={len(done)} todo={len(todo)} "
          f"unmappable(no title)={skipped}")
    if not todo:
        return

    client = AsyncAnthropic()
    sem = asyncio.Semaphore(CONCURRENCY)
    lock = asyncio.Lock()
    completed = 0

    async def one(ch):
        nonlocal completed
        messages = [{"role": "user", "content": PROMPT.format(**ch)}]
        last_err = None
        for attempt in range(RETRIES + 1):
            try:
                async with sem:
                    resp = await client.messages.create(
                        model=MAPPER_MODEL, max_tokens=MAP_MAX_TOKENS,
                        messages=messages)
                text = "".join(b.text for b in resp.content if b.type == "text")
                rec = {"bab": ch["bab"], "book": ch["book"],
                       "english": ch["english"], "n_hadith": ch["n_hadith"],
                       **parse_mapping(text),
                       "usage": {"in": resp.usage.input_tokens,
                                 "out": resp.usage.output_tokens}}
                break
            except ValueError as e:
                # Validation failure: tell the model what was wrong — a blind
                # retry repeats a systematic preference (e.g. filing the heart
                # state "truthfulness" under pillars) three times over.
                last_err = e
                messages = messages[:1] + [
                    {"role": "assistant", "content": text},
                    {"role": "user", "content":
                        f"Your JSON was rejected: {e}. pillars may ONLY contain "
                        f"{sorted(PILLARS)}; hearts may ONLY contain "
                        f"{sorted(HEARTS)}. Return the corrected JSON only."}]
            except Exception as e:  # noqa: BLE001
                last_err = e
                if attempt < RETRIES:
                    await asyncio.sleep(2 * (attempt + 1))
        else:
            raise RuntimeError(f"bab {ch['bab']} failed after "
                               f"{RETRIES + 1} attempts: {last_err}")
        async with lock:
            with open(out_path, "a") as fh:
                fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
            completed += 1
            if completed % 25 == 0:
                print(f"  {completed}/{len(todo)}")

    await asyncio.gather(*[one(c) for c in todo])
    print(f"mapped {completed} -> {out_path}")
