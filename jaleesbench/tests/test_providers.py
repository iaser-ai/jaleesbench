"""Provider seam: normalized (text, usage) from each *_complete, and that
make_clients builds only the providers asked for."""

import pytest

from jaleesbench import providers

from conftest import FakeAnthropic, FakeGemini, FakeOpenAI


# --- openai_complete -------------------------------------------------------

async def test_openai_complete_normalizes():
    client = FakeOpenAI(content="hi", prompt_tokens=11, completion_tokens=7)
    text, usage = await providers.openai_complete(
        client, "gpt-5.5", [{"role": "user", "content": "q"}], 16384)
    assert text == "hi"
    assert usage == {"in": 11, "out": 7}


async def test_openai_complete_max_tokens_param_selection():
    client = FakeOpenAI()
    await providers.openai_complete(client, "m", [], 4096, completion_param=True)
    assert client.calls[0]["max_completion_tokens"] == 4096
    assert "max_tokens" not in client.calls[0]

    client = FakeOpenAI()
    await providers.openai_complete(client, "m", [], 4096, completion_param=False)
    assert client.calls[0]["max_tokens"] == 4096
    assert "max_completion_tokens" not in client.calls[0]


async def test_openai_complete_extra_body():
    client = FakeOpenAI()
    extra = {"chat_template_kwargs": {"enable_thinking": True}}
    await providers.openai_complete(client, "m", [], 10, extra_body=extra)
    assert client.calls[0]["extra_body"] == extra

    client = FakeOpenAI()
    await providers.openai_complete(client, "m", [], 10)
    assert "extra_body" not in client.calls[0]


# --- anthropic_complete ----------------------------------------------------

async def test_anthropic_complete_joins_text_blocks_and_usage():
    client = FakeAnthropic(text="answer", input_tokens=20, output_tokens=8,
                           cache_write=3, cache_read=4)
    text, usage = await providers.anthropic_complete(
        client, "claude-opus-4-8", [{"role": "user", "content": "q"}], 4096)
    assert text == "answer"  # the non-text block is dropped
    assert usage == {"in": 20, "out": 8, "cache_write": 3, "cache_read": 4}


async def test_anthropic_complete_cache_fields_default_to_zero():
    client = FakeAnthropic(cache_attrs=False)
    _, usage = await providers.anthropic_complete(client, "m", [], 4096)
    assert usage["cache_write"] == 0 and usage["cache_read"] == 0


async def test_anthropic_complete_thinking_toggle():
    client = FakeAnthropic()
    await providers.anthropic_complete(client, "m", [], 4096, thinking=True)
    assert client.calls[0]["thinking"] == {"type": "adaptive"}
    assert client.calls[0]["max_tokens"] == 4096

    client = FakeAnthropic()
    await providers.anthropic_complete(client, "m", [], 4096, thinking=False)
    assert "thinking" not in client.calls[0]


# --- gemini_complete -------------------------------------------------------

async def test_gemini_complete_normalizes_and_adds_thoughts():
    client = FakeGemini(text="answer", prompt_tokens=30, candidates_tokens=12,
                        thoughts_tokens=5)
    text, usage = await providers.gemini_complete(client, "gemini-3.1-pro-preview",
                                                  "prompt")
    assert text == "answer"
    assert usage == {"in": 30, "out": 17}  # 12 candidates + 5 thoughts


async def test_gemini_complete_raises_on_no_text():
    client = FakeGemini(text=None, finish_reason="SAFETY")
    with pytest.raises(ValueError, match="no text"):
        await providers.gemini_complete(client, "m", "prompt")


async def test_gemini_complete_safety_off_and_max_tokens_honored():
    client = FakeGemini()
    await providers.gemini_complete(client, "m", "p", max_tokens=2048,
                                    safety_off=True)
    cfg = client.calls[0]["config"]
    assert cfg.max_output_tokens == 2048
    assert len(cfg.safety_settings) == 4  # all four harm categories OFF


async def test_gemini_complete_defaults_no_safety_no_cap():
    client = FakeGemini()
    await providers.gemini_complete(client, "m", "p")
    cfg = client.calls[0]["config"]
    assert cfg.max_output_tokens is None
    assert not cfg.safety_settings


# --- make_clients ----------------------------------------------------------

def test_make_clients_builds_only_requested(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    clients = providers.make_clients(which={"openai"})
    assert set(clients) == {"openai"}


def test_make_clients_subset_excludes_others(monkeypatch):
    monkeypatch.setenv("FRIENDLI_API_KEY", "x")
    monkeypatch.setenv("BLACKBOX_API_KEY", "y")
    clients = providers.make_clients(which={"friendli", "blackbox"})
    assert set(clients) == {"friendli", "blackbox"}
    assert "anthropic" not in clients and "gemini" not in clients
