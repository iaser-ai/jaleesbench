"""Collect subject-model responses for every sitting in the pilot grid."""

import asyncio
import json
import os
from pathlib import Path

from .prompts import FRAMINGS

ROOT = Path(__file__).resolve().parent
RESULTS = ROOT.parent / "results"

# provider: openai | anthropic | ansari (OpenAI-style messages, plain-text reply)
# framings: which framing conditions apply. Ansari takes no system prompt and is
# already a purpose-built Islamic assistant — it runs Unstated only.
SUBJECTS = {
    "gpt-5.5": {"provider": "openai", "framings": ["unstated", "stated", "guided"]},
    "claude-sonnet-4-6": {"provider": "anthropic",
                          "framings": ["unstated", "stated", "guided"]},
    "ansari": {"provider": "ansari", "framings": ["unstated"],
               "url": "https://api-35.ansari.chat/api/v2/mcp-complete"},
}

# Subjects run at provider-default temperature (gpt-5.5 accepts only the default).
# Generous cap: reasoning models spend completion tokens thinking before answering.
MAX_TOKENS = 16384
CONCURRENCY = 8
RETRIES = 2


def load_env() -> None:
    """Load keys from taqwabench/.env and the iaser Gemini env. Fail fast if missing."""
    for env_path in [ROOT.parent.parent / ".env",
                     Path("/Users/mwk/Development/iaser/tazkiya/.env")]:
        if not env_path.exists():
            raise FileNotFoundError(f"env file missing: {env_path}")
        for line in env_path.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                os.environ.setdefault(k.strip(), v.strip())
    for key in ["ANTHROPIC_API_KEY", "OPENAI_API_KEY", "GEMINI_API_KEY"]:
        if not os.environ.get(key):
            raise RuntimeError(f"{key} not set after loading env files")


def load_probes() -> dict:
    return json.loads((ROOT / "probes.json").read_text())


def sitting_key(r: dict) -> str:
    return f"{r['subject']}|{r['probe_id']}|{r['pressure']}|{r['framing']}"


async def call_subject(subject: str, system: str | None, messages: list[dict],
                       clients: dict) -> tuple[str, dict]:
    """Returns (content, usage) where usage = {'in': int, 'out': int} (zeros for ansari)."""
    spec = SUBJECTS[subject]
    # Ansari is a free community endpoint: be patient with rate limits.
    retries = 5 if spec["provider"] == "ansari" else RETRIES
    last_err = None
    for attempt in range(retries + 1):
        try:
            if spec["provider"] == "openai":
                msgs = ([{"role": "system", "content": system}] if system else []) + messages
                resp = await clients["openai"].chat.completions.create(
                    model=subject, messages=msgs, max_completion_tokens=MAX_TOKENS)
                content = resp.choices[0].message.content
                usage = {"in": resp.usage.prompt_tokens, "out": resp.usage.completion_tokens}
            elif spec["provider"] == "anthropic":
                kwargs = {"model": subject, "messages": messages, "max_tokens": MAX_TOKENS}
                if system:
                    kwargs["system"] = system
                resp = await clients["anthropic"].messages.create(**kwargs)
                content = "".join(b.text for b in resp.content if b.type == "text")
                usage = {"in": resp.usage.input_tokens, "out": resp.usage.output_tokens}
            else:  # ansari — plain-text reply, no auth, no usage reporting
                resp = await clients["httpx"].post(
                    spec["url"], json={"messages": messages}, timeout=180)
                resp.raise_for_status()
                content = resp.text
                usage = {"in": 0, "out": 0}
            if not content or not content.strip():
                raise RuntimeError("empty response content")
            return content.strip(), usage
        except Exception as e:  # noqa: BLE001 — retry transient, then fail loudly
            last_err = e
            if attempt < retries:
                backoff = 30 * (attempt + 1) if spec["provider"] == "ansari" \
                    else 2 * (attempt + 1)
                await asyncio.sleep(backoff)
    raise RuntimeError(f"subject {subject} failed after {retries + 1} attempts: {last_err}")


async def run_sitting(subject: str, probe: dict, pressure: str, framing: str,
                      sem: asyncio.Semaphore, clients: dict) -> dict:
    system = FRAMINGS[framing]
    async with sem:
        msgs = [{"role": "user", "content": probe["turn1"]}]
        reply1, usage1 = await call_subject(subject, system, msgs, clients)
        msgs = msgs + [{"role": "assistant", "content": reply1},
                       {"role": "user", "content": probe["pressure_turns"][pressure]}]
        reply2, usage2 = await call_subject(subject, system, msgs, clients)
    return {
        "subject": subject, "probe_id": probe["id"], "pressure": pressure,
        "framing": framing,
        "usage": [usage1, usage2],
        "turns": [
            {"role": "user", "content": probe["turn1"]},
            {"role": "assistant", "content": reply1},
            {"role": "user", "content": probe["pressure_turns"][pressure]},
            {"role": "assistant", "content": reply2},
        ],
    }


async def collect(limit: int | None = None) -> None:
    import httpx
    from anthropic import AsyncAnthropic
    from openai import AsyncOpenAI

    load_env()
    RESULTS.mkdir(exist_ok=True)
    out_path = RESULTS / "collect.jsonl"
    done: set[str] = set()
    if out_path.exists():
        for line in out_path.read_text().splitlines():
            done.add(sitting_key(json.loads(line)))

    bank = load_probes()
    grid = [(s, p, pr, f)
            for s, spec in SUBJECTS.items()
            for p in bank["probes"]
            for pr in bank["pressures"]
            for f in spec["framings"]]
    todo = [g for g in grid
            if f"{g[0]}|{g[1]['id']}|{g[2]}|{g[3]}" not in done]
    if limit:
        todo = todo[:limit]
    print(f"grid={len(grid)} done={len(done)} todo={len(todo)}")
    if not todo:
        return

    clients = {"openai": AsyncOpenAI(), "anthropic": AsyncAnthropic(),
               "httpx": httpx.AsyncClient()}
    sem = asyncio.Semaphore(CONCURRENCY)
    ansari_sem = asyncio.Semaphore(1)  # serial — free community endpoint
    lock = asyncio.Lock()
    completed = 0

    async def one(g):
        nonlocal completed
        which = ansari_sem if SUBJECTS[g[0]]["provider"] == "ansari" else sem
        rec = await run_sitting(g[0], g[1], g[2], g[3], which, clients)
        async with lock:
            with open(out_path, "a") as fh:
                fh.write(json.dumps(rec) + "\n")
            completed += 1
            if completed % 20 == 0:
                print(f"  {completed}/{len(todo)}")

    try:
        await asyncio.gather(*[one(g) for g in todo])
    finally:
        await clients["httpx"].aclose()
    print(f"collected {completed} sittings -> {out_path}")
