"""Collect subject-model responses for every sitting in the pilot grid."""

import asyncio
import json
import os
from pathlib import Path

from .prompts import FRAMINGS

ROOT = Path(__file__).resolve().parent
RESULTS = ROOT.parent / "results"
DATA = ROOT / "data"  # bundled bench data: probes, proof texts, chapter map

# Gemini runs on Vertex AI (service-account key, gitignored). location="global"
# is where gemini-3.5-flash / gemini-3.1-pro-preview are served for this project.
VERTEX_SA = ROOT.parent.parent / ".vertex-sa.json"
VERTEX_PROJECT = "agentset-491018"
VERTEX_LOCATION = "global"


def gemini_client():
    """A google-genai client for Gemini. Prefers Vertex AI when the
    service-account key is present (this project's models are served there);
    otherwise uses the public Gemini Developer API via GEMINI_API_KEY. Fails
    loudly when neither credential is configured."""
    from google import genai
    if VERTEX_SA.exists():
        from google.oauth2 import service_account
        creds = service_account.Credentials.from_service_account_file(
            str(VERTEX_SA), scopes=["https://www.googleapis.com/auth/cloud-platform"])
        return genai.Client(vertexai=True, project=VERTEX_PROJECT,
                            location=VERTEX_LOCATION, credentials=creds)
    api_key = os.environ.get("GEMINI_API_KEY")
    if api_key:
        return genai.Client(api_key=api_key)
    raise RuntimeError(
        f"No Gemini credential: provide a Vertex service account at {VERTEX_SA} "
        "or set GEMINI_API_KEY.")

# provider: openai | anthropic | gemini | ansari
# framings: which framing conditions apply. Ansari takes no system prompt and is
# already a purpose-built Islamic assistant — it runs Unstated only.
SUBJECTS = {
    "gpt-5.5": {"provider": "openai", "framings": ["unstated", "stated", "guided"]},
    "claude-sonnet-4-6": {"provider": "anthropic",
                          "framings": ["unstated", "stated", "guided"]},
    # Opus 4.8 as a SUBJECT (also serves as a judge — self-judging conflict
    # handled at the judging step).
    "claude-opus-4-8": {"provider": "anthropic",
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
    # Thinking-mode arms (additive experiment — separate file collect_thinking.jsonl,
    # Unstated only). enable_thinking runs on the SAME serving as each baseline, so the
    # only difference is the reasoning pass. gemma/glm: Friendli chat_template_kwargs;
    # sonnet: Anthropic adaptive thinking. The final answer lands in content/text and is
    # what we save and judge; the reasoning trace is discarded (as for all subjects).
    "gemma-4-thinking": {"provider": "friendli", "model": "google/gemma-4-31B-it",
                         "thinking": True, "framings": ["unstated"]},
    "glm-thinking": {"provider": "friendli", "model": "zai-org/GLM-5.1",
                     "thinking": True, "framings": ["unstated"]},
    "claude-sonnet-thinking": {"provider": "anthropic", "model": "claude-sonnet-4-6",
                               "thinking": True, "framings": ["unstated"]},
}

# Subjects run at provider-default temperature (gpt-5.5 accepts only the default).
# Generous cap: reasoning models spend completion tokens thinking before answering.
MAX_TOKENS = 16384
CONCURRENCY = 24  # interleaved across 8 providers (~3 in flight per provider)
RETRIES = 2


def load_env() -> None:
    """Load keys from the repo-root .env, the iaser Gemini env, and shannon
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
    for key in ["ANTHROPIC_API_KEY", "OPENAI_API_KEY",
                "FRIENDLI_API_KEY", "BLACKBOX_API_KEY", "LEADERBOARD_API_KEY"]:
        if not os.environ.get(key):
            raise RuntimeError(f"{key} not set after loading env files")
    # Gemini auth: a Vertex service account (preferred) OR a Gemini API key.
    if not VERTEX_SA.exists() and not os.environ.get("GEMINI_API_KEY"):
        raise RuntimeError(
            f"No Gemini credential: provide {VERTEX_SA} or set GEMINI_API_KEY.")


def load_probes(path: str = "probes.json") -> dict:
    return json.loads((DATA / path).read_text())


def sitting_key(r: dict) -> str:
    return f"{r['subject']}|{r['probe_id']}|{r['pressure']}|{r['framing']}"


def ctx_block(ctx: str) -> str:
    return f"[Context for this conversation: {ctx}]"


async def call_subject(subject: str, ctx: str | None, messages: list[dict],
                       clients: dict) -> tuple[str, dict, int]:
    """Returns (content, usage, attempts).

    ctx is the framing text. It is included at the top of EVERY user message,
    never as a system prompt — no subject gets a privileged channel (Waleed's
    ruling 2026-06-12: a real user cannot set a system prompt). `messages`
    holds the clean probe turns; the fold happens here, per provider.
    """
    spec = SUBJECTS[subject]
    # Ansari is a free community endpoint: be patient with rate limits.
    retries = 5 if spec["provider"] == "ansari" else RETRIES

    def folded(m: dict) -> dict:
        if m["role"] != "user" or not ctx:
            return m
        return {"role": "user", "content": f"{ctx_block(ctx)}\n\n{m['content']}"}

    last_err = None
    for attempt in range(retries + 1):
        try:
            if spec["provider"] in ("openai", "friendli", "blackbox", "ansari"):
                msgs = [folded(m) for m in messages]
                kwargs = {"model": spec.get("model", subject), "messages": msgs}
                # gpt-5.5 requires the newer param name; the others
                # take the classic one.
                if spec["provider"] == "openai":
                    kwargs["max_completion_tokens"] = MAX_TOKENS
                else:
                    kwargs["max_tokens"] = MAX_TOKENS
                # Friendli thinking arms: turn on the gemma4/GLM reasoning pass.
                # The final answer stays in message.content; reasoning goes to a
                # separate `reasoning` field we don't read.
                if spec.get("thinking") and spec["provider"] == "friendli":
                    kwargs["extra_body"] = {"chat_template_kwargs": {"enable_thinking": True}}
                resp = await clients[spec["provider"]].chat.completions.create(**kwargs)
                content = resp.choices[0].message.content
                usage = {"in": resp.usage.prompt_tokens, "out": resp.usage.completion_tokens}
            elif spec["provider"] == "anthropic":
                # Prompt caching: the framing block (shared by every sitting of
                # this framing) is a 1h breakpoint; the first user question is
                # a default-TTL breakpoint so the turn-2 call rereads turn 1
                # from cache.
                amsgs = []
                first_user = True
                for m in messages:
                    if m["role"] != "user":
                        amsgs.append(m)
                        continue
                    blocks = []
                    if ctx:
                        b = {"type": "text", "text": ctx_block(ctx)}
                        if first_user:
                            b["cache_control"] = {"type": "ephemeral", "ttl": "1h"}
                        blocks.append(b)
                    q = {"type": "text", "text": m["content"]}
                    if first_user:
                        q["cache_control"] = {"type": "ephemeral"}
                    blocks.append(q)
                    amsgs.append({"role": "user", "content": blocks})
                    first_user = False
                akw = {"model": spec.get("model", subject),
                       "messages": amsgs, "max_tokens": MAX_TOKENS}
                if spec.get("thinking"):
                    akw["thinking"] = {"type": "adaptive"}
                resp = await clients["anthropic"].messages.create(**akw)
                content = "".join(b.text for b in resp.content if b.type == "text")
                u = resp.usage
                usage = {"in": u.input_tokens, "out": u.output_tokens,
                         "cache_write": getattr(u, "cache_creation_input_tokens", 0) or 0,
                         "cache_read": getattr(u, "cache_read_input_tokens", 0) or 0}
            elif spec["provider"] == "gemini":
                from google.genai import types
                contents = [
                    types.Content(role="model" if m["role"] == "assistant" else "user",
                                  parts=[types.Part(text=folded(m)["content"])])
                    for m in messages]
                cfg = types.GenerateContentConfig(max_output_tokens=MAX_TOKENS)
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
            return content.strip(), usage, attempt + 1
        except Exception as e:  # noqa: BLE001 — retry transient, then fail loudly
            last_err = e
            if attempt < retries:
                backoff = 30 * (attempt + 1) if spec["provider"] == "ansari" \
                    else 2 * (attempt + 1)
                await asyncio.sleep(backoff)
    raise RuntimeError(f"subject {subject} failed after {retries + 1} attempts: {last_err}")


async def run_sitting(subject: str, probe: dict, pressure: str, framing: str,
                      sem: asyncio.Semaphore, clients: dict,
                      framings: dict | None = None) -> dict:
    from datetime import datetime, timezone
    ctx = (framings or FRAMINGS)[framing]
    async with sem:
        msgs = [{"role": "user", "content": probe["turn1"]}]
        reply1, usage1, att1 = await call_subject(subject, ctx, msgs, clients)
        msgs = msgs + [{"role": "assistant", "content": reply1},
                       {"role": "user", "content": probe["pressure_turns"][pressure]}]
        reply2, usage2, att2 = await call_subject(subject, ctx, msgs, clients)
    # turns stay clean (probe text only): judges remain blinded to framing.
    # context_prefix + model + ts + attempts reconstruct the exact request.
    return {
        "subject": subject, "probe_id": probe["id"], "pressure": pressure,
        "framing": framing,
        "model": SUBJECTS[subject].get("model", subject),
        "context_prefix": ctx_block(ctx) if ctx else None,
        "ts": datetime.now(timezone.utc).isoformat(),
        "attempts": [att1, att2],
        "usage": [usage1, usage2],
        "turns": [
            {"role": "user", "content": probe["turn1"]},
            {"role": "assistant", "content": reply1},
            {"role": "user", "content": probe["pressure_turns"][pressure]},
            {"role": "assistant", "content": reply2},
        ],
    }


async def collect(limit: int | None = None,
                  out_path: Path | None = None,
                  subjects: set[str] | None = None,
                  concurrency: int | None = None,
                  probes_path: str = "probes.json",
                  framings: dict | None = None) -> None:
    import httpx
    from anthropic import AsyncAnthropic
    from google import genai
    from openai import AsyncOpenAI

    load_env()
    RESULTS.mkdir(exist_ok=True)
    if out_path is None:
        out_path = RESULTS / "collect.jsonl"
    done: set[str] = set()
    if out_path.exists():
        for line in out_path.read_text().splitlines():
            done.add(sitting_key(json.loads(line)))

    bank = load_probes(probes_path)
    grid = [(s, p, pr, f)
            for s, spec in SUBJECTS.items()
            if subjects is None or s in subjects
            for p in bank["probes"]
            for pr in bank["pressures"]
            for f in spec["framings"]]
    todo = [g for g in grid
            if f"{g[0]}|{g[1]['id']}|{g[2]}|{g[3]}" not in done]
    # Interleave subjects (cell-major order) so concurrency spreads across
    # providers instead of hammering one API at a time.
    todo.sort(key=lambda g: (g[1]["id"], g[2], g[3]))
    if limit:
        todo = todo[:limit]
    print(f"grid={len(grid)} done={len(done)} todo={len(todo)}")
    if not todo:
        return

    clients = {"openai": AsyncOpenAI(), "anthropic": AsyncAnthropic(),
               "gemini": gemini_client(), "httpx": httpx.AsyncClient(),
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
    sem = asyncio.Semaphore(concurrency or CONCURRENCY)
    lock = asyncio.Lock()
    completed = 0

    failed = 0

    async def one(g):
        nonlocal completed, failed
        try:
            rec = await run_sitting(g[0], g[1], g[2], g[3], sem, clients, framings)
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
