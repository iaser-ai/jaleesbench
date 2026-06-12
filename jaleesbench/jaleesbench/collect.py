"""Collect subject-model responses for every sitting in the pilot grid."""

import asyncio
import json
import os
from pathlib import Path

from .prompts import FRAMINGS

ROOT = Path(__file__).resolve().parent
RESULTS = ROOT.parent / "results"

# provider: openai | anthropic | gemini | ansari
# framings: which framing conditions apply. Ansari takes no system prompt and is
# already a purpose-built Islamic assistant — it runs Unstated only.
SUBJECTS = {
    "gpt-5.5": {"provider": "openai", "framings": ["unstated", "stated", "guided"]},
    "claude-sonnet-4-6": {"provider": "anthropic",
                          "framings": ["unstated", "stated", "guided"]},
    # Ansari's underlying base model (per Waleed) — isolates Ansari's
    # retrieval/prompting value-add from raw model capability.
    "gemini-3.5-flash": {"provider": "gemini",
                         "framings": ["unstated", "stated", "guided"]},
    # Friendli serverless (key in cluesmith/shannon/.env).
    "gemma-4-31b": {"provider": "friendli", "model": "google/gemma-4-31B-it",
                    "framings": ["unstated", "stated", "guided"]},
    "qwen3-235b": {"provider": "friendli",
                   "model": "Qwen/Qwen3-235B-A22B-Instruct-2507",
                   "framings": ["unstated", "stated", "guided"]},
    "glm-5.1": {"provider": "friendli", "model": "zai-org/GLM-5.1",
                "framings": ["unstated", "stated", "guided"]},
    # Blackbox (key in cluesmith/shannon/.env). Reasoning model: hidden
    # reasoning pass bills as completion tokens; ample MAX_TOKENS required
    # or content arrives null (finish_reason=length mid-reasoning).
    "nemotron-3-ultra": {"provider": "blackbox",
                         "model": "blackboxai/nvidia/nemotron-3-ultra",
                         "framings": ["unstated", "stated", "guided"]},
    # Ansari via its OpenAI-compatible route (ansari-multisage spec 19):
    # drives the real facilitator pipeline, accepts the system role, reports
    # usage, no marketing footer, and the leaderboard bearer bypasses the
    # rate limiter — so collection runs parallel, not serial.
    "ansari": {"provider": "ansari", "model": "ansari",
               "framings": ["unstated", "stated", "guided"]},
}

# Subjects run at provider-default temperature (gpt-5.5 accepts only the default).
# Generous cap: reasoning models spend completion tokens thinking before answering.
MAX_TOKENS = 16384
CONCURRENCY = 8
RETRIES = 2


def load_env() -> None:
    """Load keys from taqwabench/.env, the iaser Gemini env, and shannon
    (Friendli + Blackbox). Fail fast if missing."""
    for env_path in [ROOT.parent.parent / ".env",
                     Path("/Users/mwk/Development/iaser/tazkiya/.env"),
                     Path("/Users/mwk/Development/cluesmith/shannon/.env"),
                     Path("/Users/mwk/Development/cluesmith/ansari4/ansari-multisage/.env")]:
        if not env_path.exists():
            raise FileNotFoundError(f"env file missing: {env_path}")
        for line in env_path.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                os.environ.setdefault(k.strip(), v.strip())
    for key in ["ANTHROPIC_API_KEY", "OPENAI_API_KEY", "GEMINI_API_KEY",
                "FRIENDLI_API_KEY", "BLACKBOX_API_KEY", "LEADERBOARD_API_KEY"]:
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
            if spec["provider"] in ("openai", "friendli", "blackbox", "ansari"):
                msgs = ([{"role": "system", "content": system}] if system else []) + messages
                kwargs = {"model": spec.get("model", subject), "messages": msgs}
                # gpt-5.5 requires the newer param name; the others
                # take the classic one.
                if spec["provider"] == "openai":
                    kwargs["max_completion_tokens"] = MAX_TOKENS
                else:
                    kwargs["max_tokens"] = MAX_TOKENS
                resp = await clients[spec["provider"]].chat.completions.create(**kwargs)
                content = resp.choices[0].message.content
                usage = {"in": resp.usage.prompt_tokens, "out": resp.usage.completion_tokens}
            elif spec["provider"] == "anthropic":
                kwargs = {"model": subject, "messages": messages, "max_tokens": MAX_TOKENS}
                if system:
                    kwargs["system"] = system
                resp = await clients["anthropic"].messages.create(**kwargs)
                content = "".join(b.text for b in resp.content if b.type == "text")
                usage = {"in": resp.usage.input_tokens, "out": resp.usage.output_tokens}
            elif spec["provider"] == "gemini":
                from google.genai import types
                contents = [
                    types.Content(role="model" if m["role"] == "assistant" else "user",
                                  parts=[types.Part(text=m["content"])])
                    for m in messages]
                cfg = types.GenerateContentConfig(
                    max_output_tokens=MAX_TOKENS,
                    system_instruction=system or None)
                resp = await clients["gemini"].aio.models.generate_content(
                    model=subject, contents=contents, config=cfg)
                content = resp.text
                um = resp.usage_metadata
                usage = {"in": um.prompt_token_count or 0,
                         "out": (um.candidates_token_count or 0)
                                + (getattr(um, "thoughts_token_count", 0) or 0)}
            else:
                raise RuntimeError(f"unknown provider: {spec['provider']}")
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
    from google import genai
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
               "gemini": genai.Client(), "httpx": httpx.AsyncClient(),
               "friendli": AsyncOpenAI(
                   base_url="https://api.friendli.ai/serverless/v1",
                   api_key=os.environ["FRIENDLI_API_KEY"]),
               "blackbox": AsyncOpenAI(
                   base_url="https://api.blackbox.ai/v1",
                   api_key=os.environ["BLACKBOX_API_KEY"]),
               "ansari": AsyncOpenAI(
                   base_url="https://api-35.ansari.chat/api/v1",
                   api_key=os.environ["LEADERBOARD_API_KEY"],
                   timeout=300)}
    sem = asyncio.Semaphore(CONCURRENCY)
    lock = asyncio.Lock()
    completed = 0

    failed = 0

    async def one(g):
        nonlocal completed, failed
        try:
            rec = await run_sitting(g[0], g[1], g[2], g[3], sem, clients)
        except Exception as e:  # noqa: BLE001 — skip, report, let a re-run retry it
            failed += 1
            print(f"  FAILED {g[0]}|{g[1]['id']}|{g[2]}|{g[3]}: {e}")
            return
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
    print(f"collected {completed} sittings -> {out_path} ({failed} failed)")
    if failed:
        raise SystemExit(1)
