"""Provider/model seam: client construction + normalized completion calls.

Both subject collection (`collect.call_subject`) and judging (`judge.call_judge`)
dispatch through here, so provider-specific mechanics — which client to build,
how to call it, and how each provider reports token usage — live in one place
instead of being duplicated across the two modules.

Division of labour: a *caller* owns the request LAYOUT that is specific to its
job (Anthropic cache breakpoints, context folding, the judge's three-block
prompt, Gemini safety-off) and the retry policy; this module owns the single
API call and turns each provider's response into a uniform `(text, usage)`
pair. `usage` is always `{"in", "out"[, "cache_write", "cache_read"]}`.
"""

import os


def make_clients(which: set[str] | None = None) -> dict:
    """Build the `provider -> async client` map. `which` limits construction to
    a subset (judges pass `{"anthropic", "gemini"}`); `None` builds them all.

    OpenAI-compatible providers are all `AsyncOpenAI` with different base URLs;
    Anthropic and Gemini use their own SDKs. Gemini's client (Vertex or API key)
    is built by `collect.gemini_client` — imported lazily to avoid a cycle.
    """
    import httpx
    from anthropic import AsyncAnthropic
    from openai import AsyncOpenAI

    def want(p: str) -> bool:
        return which is None or p in which

    clients: dict = {}
    if want("openai"):
        clients["openai"] = AsyncOpenAI()
    if want("anthropic"):
        clients["anthropic"] = AsyncAnthropic()
    if want("gemini"):
        from .collect import gemini_client
        clients["gemini"] = gemini_client()
    if want("friendli"):
        clients["friendli"] = AsyncOpenAI(
            base_url="https://api.friendli.ai/serverless/v1",
            api_key=os.environ["FRIENDLI_API_KEY"])
    if want("blackbox"):
        clients["blackbox"] = AsyncOpenAI(
            base_url="https://api.blackbox.ai/v1",
            api_key=os.environ["BLACKBOX_API_KEY"])
    if want("ansari"):
        clients["ansari"] = AsyncOpenAI(
            base_url="https://api-35.ansari.chat/api/v1",
            api_key=os.environ["LEADERBOARD_API_KEY"], timeout=300)
    if want("httpx"):
        clients["httpx"] = httpx.AsyncClient()
    return clients


async def openai_complete(client, model: str, messages: list, max_tokens: int,
                          *, completion_param: bool = False,
                          extra_body: dict | None = None) -> tuple[str, dict]:
    """Chat-completions call for any OpenAI-compatible provider. `gpt-5.5`
    requires `max_completion_tokens`; the others take the classic `max_tokens`
    (`completion_param` selects which). `extra_body` carries provider extras
    such as Friendli's `chat_template_kwargs` thinking toggle."""
    kwargs: dict = {"model": model, "messages": messages}
    kwargs["max_completion_tokens" if completion_param else "max_tokens"] = max_tokens
    if extra_body:
        kwargs["extra_body"] = extra_body
    resp = await client.chat.completions.create(**kwargs)
    content = resp.choices[0].message.content
    usage = {"in": resp.usage.prompt_tokens, "out": resp.usage.completion_tokens}
    return content, usage


async def anthropic_complete(client, model: str, messages: list, max_tokens: int,
                             *, thinking: bool = False) -> tuple[str, dict]:
    """Messages call. The caller supplies `messages` already laid out with any
    `cache_control` breakpoints. `thinking` enables the adaptive reasoning pass;
    the final answer still lands in the text blocks. Usage includes cache
    read/write counts."""
    kwargs: dict = {"model": model, "messages": messages, "max_tokens": max_tokens}
    if thinking:
        kwargs["thinking"] = {"type": "adaptive"}
    resp = await client.messages.create(**kwargs)
    text = "".join(b.text for b in resp.content if b.type == "text")
    u = resp.usage
    usage = {"in": u.input_tokens, "out": u.output_tokens,
             "cache_write": getattr(u, "cache_creation_input_tokens", 0) or 0,
             "cache_read": getattr(u, "cache_read_input_tokens", 0) or 0}
    return text, usage


async def gemini_complete(client, model: str, contents, *,
                          max_tokens: int | None = None,
                          safety_off: bool = False) -> tuple[str, dict]:
    """Generate-content call. `contents` is whatever the SDK accepts — a string
    or a list of `types.Content` the caller built. `max_tokens` caps output when
    set (subjects cap, judges don't). `safety_off` disables the content filters
    (judges only — they SCORE transcripts and must not refuse benign-but-
    sensitive material). Raises if no text comes back (blocked/truncated)."""
    from google.genai import types
    cfg_kwargs: dict = {}
    if max_tokens is not None:
        cfg_kwargs["max_output_tokens"] = max_tokens
    if safety_off:
        cfg_kwargs["safety_settings"] = [
            types.SafetySetting(category=c, threshold="OFF") for c in (
                "HARM_CATEGORY_HARASSMENT", "HARM_CATEGORY_HATE_SPEECH",
                "HARM_CATEGORY_SEXUALLY_EXPLICIT",
                "HARM_CATEGORY_DANGEROUS_CONTENT")]
    cfg = types.GenerateContentConfig(**cfg_kwargs)
    resp = await client.aio.models.generate_content(
        model=model, contents=contents, config=cfg)
    text = resp.text
    if text is None:
        fr = (getattr(resp.candidates[0], "finish_reason", "?")
              if resp.candidates else "no-candidates")
        raise ValueError(f"gemini returned no text (finish_reason={fr})")
    um = resp.usage_metadata
    usage = {"in": um.prompt_token_count or 0,
             "out": (um.candidates_token_count or 0)
                    + (getattr(um, "thoughts_token_count", 0) or 0)}
    return text, usage
