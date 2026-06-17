"""The two dispatch sites: collect.call_subject and judge.call_judge.

These own request LAYOUT (context folding, the Anthropic cache breakpoints, the
judge's three blocks) and the retry policy, then hand a single call to a
provider. Fakes capture the request so we can assert the layout exactly.
"""

import pytest

from jaleesbench import collect, judge

from conftest import FakeAnthropic, FakeGemini, FakeOpenAI

CONV = [{"role": "user", "content": "turn1"},
        {"role": "assistant", "content": "reply1"},
        {"role": "user", "content": "turn2"}]

VALID_VERDICT = ('{"band": 1, "direction": "ok", "rationale": "sound counsel", '
                 '"techniques_used": ["open door"]}')


# --- call_subject: routing + context folding -------------------------------

async def test_call_subject_openai_folds_ctx_into_user_turns():
    client = FakeOpenAI(content="  spaced reply  ")
    text, usage, attempts = await collect.call_subject(
        "gpt-5.5", "FRAME", CONV, {"openai": client})
    assert text == "spaced reply"  # stripped
    assert (usage, attempts) == ({"in": 11, "out": 7}, 1)
    sent = client.calls[0]["messages"]
    ctx = collect.ctx_block("FRAME")
    assert sent[0]["content"] == f"{ctx}\n\nturn1"
    assert sent[1] == {"role": "assistant", "content": "reply1"}  # untouched
    assert sent[2]["content"] == f"{ctx}\n\nturn2"
    assert "max_completion_tokens" in client.calls[0]  # gpt-5.5 -> completion param


async def test_call_subject_friendli_thinking_arm():
    client = FakeOpenAI()
    await collect.call_subject("gemma-4-thinking", None, CONV, {"friendli": client})
    call = client.calls[0]
    assert call["model"] == "google/gemma-4-31B-it"
    assert call["extra_body"] == {"chat_template_kwargs": {"enable_thinking": True}}
    assert "max_tokens" in call  # friendli -> classic param


async def test_call_subject_anthropic_cache_layout():
    client = FakeAnthropic()
    await collect.call_subject("claude-sonnet-4-6", "FRAME", CONV,
                               {"anthropic": client})
    msgs = client.calls[0]["messages"]
    ctx = collect.ctx_block("FRAME")
    # first user turn: ctx block (1h breakpoint) + question (default-TTL breakpoint)
    first = msgs[0]["content"]
    assert first[0]["text"] == ctx
    assert first[0]["cache_control"] == {"type": "ephemeral", "ttl": "1h"}
    assert first[1]["text"] == "turn1"
    assert first[1]["cache_control"] == {"type": "ephemeral"}
    # assistant turn passes through unchanged
    assert msgs[1] == {"role": "assistant", "content": "reply1"}
    # later user turn: same blocks, no cache breakpoints
    later = msgs[2]["content"]
    assert later[0]["text"] == ctx and "cache_control" not in later[0]
    assert later[1]["text"] == "turn2" and "cache_control" not in later[1]


async def test_call_subject_gemini_builds_contents_with_roles():
    client = FakeGemini()
    await collect.call_subject("gemini-3.5-flash", "FRAME", CONV,
                               {"gemini": client})
    contents = client.calls[0]["contents"]
    ctx = collect.ctx_block("FRAME")
    assert [c.role for c in contents] == ["user", "model", "user"]
    assert contents[0].parts[0].text == f"{ctx}\n\nturn1"
    assert contents[1].parts[0].text == "reply1"  # assistant -> model, no fold


# --- call_subject: retry policy --------------------------------------------

async def test_call_subject_retries_then_raises(no_sleep):
    client = FakeOpenAI(error=RuntimeError("boom"))  # fails forever
    with pytest.raises(RuntimeError, match="failed after 3 attempts"):
        await collect.call_subject("gpt-5.5", None, CONV, {"openai": client})
    assert len(client.calls) == 3  # RETRIES (2) + 1


async def test_call_subject_recovers_after_transient_failure(no_sleep):
    client = FakeOpenAI(error=RuntimeError("transient"), fail_times=1)
    text, _, attempts = await collect.call_subject(
        "gpt-5.5", None, CONV, {"openai": client})
    assert text == "A reply."
    assert attempts == 2  # failed once, succeeded on the second attempt


# --- call_judge: routing + parse + usage -----------------------------------

async def test_call_judge_anthropic_layout_and_usage():
    client = FakeAnthropic(text=VALID_VERDICT)
    verdict = await judge.call_judge(
        "claude-opus-4-8", ("RUBRIC", "PROOFS", "CONV"), {"anthropic": client})
    assert verdict["band"] == 1
    assert verdict["usage"]["out"] == 8  # attached from the provider call
    blocks = client.calls[0]["messages"][0]["content"]
    assert [b["text"] for b in blocks] == ["RUBRIC", "PROOFS", "CONV"]
    assert blocks[0]["cache_control"] == {"type": "ephemeral", "ttl": "1h"}
    assert blocks[1]["cache_control"] == {"type": "ephemeral", "ttl": "1h"}
    assert "cache_control" not in blocks[2]  # the fresh conversation is uncached


async def test_call_judge_gemini_safety_off_and_usage():
    client = FakeGemini(text=VALID_VERDICT)
    verdict = await judge.call_judge(
        "gemini-3.1-pro-preview", ("RUBRIC", "PROOFS", "CONV"), {"gemini": client})
    assert verdict["band"] == 1
    assert verdict["usage"] == {"in": 30, "out": 17}
    call = client.calls[0]
    assert call["contents"] == "RUBRIC\n\nPROOFS\n\nCONV"
    assert len(call["config"].safety_settings) == 4  # judge scores with safety OFF
