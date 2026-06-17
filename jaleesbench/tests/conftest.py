"""Shared offline fakes for the provider seam.

The real clients are never built or called. Each fake mirrors the exact shape
the production code reaches into — `chat.completions.create`, `messages.create`,
`aio.models.generate_content` — returns a canned response, and records the
kwargs of every call so tests can assert on request layout. Set `error` to make
a fake raise (`fail_times=None` raises forever; an int raises on the first N
calls, then succeeds) to exercise the retry/raise paths.
"""

from types import SimpleNamespace

import pytest


def _maybe_fail(calls, error, fail_times):
    """Raise `error` while we're still inside the failing window."""
    if error is not None and (fail_times is None or len(calls) <= fail_times):
        raise error


class FakeOpenAI:
    """Stands in for AsyncOpenAI / any OpenAI-compatible client."""

    def __init__(self, content="A reply.", prompt_tokens=11, completion_tokens=7,
                 error=None, fail_times=None):
        self._content = content
        self._pt, self._ct = prompt_tokens, completion_tokens
        self._error, self._fail_times = error, fail_times
        self.calls = []
        self.chat = SimpleNamespace(
            completions=SimpleNamespace(create=self._create))

    async def _create(self, **kwargs):
        self.calls.append(kwargs)
        _maybe_fail(self.calls, self._error, self._fail_times)
        return SimpleNamespace(
            choices=[SimpleNamespace(
                message=SimpleNamespace(content=self._content))],
            usage=SimpleNamespace(prompt_tokens=self._pt,
                                  completion_tokens=self._ct))


class FakeAnthropic:
    """Stands in for AsyncAnthropic. `cache_attrs=False` drops the cache usage
    fields so the getattr-default path can be exercised; a non-text content
    block is always present so the text-only join is exercised too."""

    def __init__(self, text="A reply.", input_tokens=20, output_tokens=8,
                 cache_write=3, cache_read=4, cache_attrs=True,
                 error=None, fail_times=None):
        self._text = text
        self._in, self._out = input_tokens, output_tokens
        self._cw, self._cr, self._cache_attrs = cache_write, cache_read, cache_attrs
        self._error, self._fail_times = error, fail_times
        self.calls = []
        self.messages = SimpleNamespace(create=self._create)

    async def _create(self, **kwargs):
        self.calls.append(kwargs)
        _maybe_fail(self.calls, self._error, self._fail_times)
        content = [SimpleNamespace(type="thinking", text="(ignored trace)"),
                   SimpleNamespace(type="text", text=self._text)]
        usage_fields = {"input_tokens": self._in, "output_tokens": self._out}
        if self._cache_attrs:
            usage_fields["cache_creation_input_tokens"] = self._cw
            usage_fields["cache_read_input_tokens"] = self._cr
        return SimpleNamespace(content=content,
                               usage=SimpleNamespace(**usage_fields))


class FakeGemini:
    """Stands in for the google-genai client. `text=None` simulates a blocked/
    truncated response (no candidates text)."""

    def __init__(self, text="A reply.", prompt_tokens=30, candidates_tokens=12,
                 thoughts_tokens=5, finish_reason="SAFETY",
                 error=None, fail_times=None):
        self._text = text
        self._pt, self._ct, self._tt = prompt_tokens, candidates_tokens, thoughts_tokens
        self._finish = finish_reason
        self._error, self._fail_times = error, fail_times
        self.calls = []
        self.aio = SimpleNamespace(
            models=SimpleNamespace(generate_content=self._generate))

    async def _generate(self, *, model, contents, config):
        self.calls.append({"model": model, "contents": contents, "config": config})
        _maybe_fail(self.calls, self._error, self._fail_times)
        um = SimpleNamespace(prompt_token_count=self._pt,
                             candidates_token_count=self._ct,
                             thoughts_token_count=self._tt)
        candidates = [SimpleNamespace(finish_reason=self._finish)]
        return SimpleNamespace(text=self._text, usage_metadata=um,
                               candidates=candidates)


@pytest.fixture
def no_sleep(monkeypatch):
    """Make retry backoff instant so the retry/raise paths run fast."""
    import jaleesbench.collect as collect

    async def _instant(_seconds):
        return None

    monkeypatch.setattr(collect.asyncio, "sleep", _instant)
