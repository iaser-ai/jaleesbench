"""Caption text transforms and SRT cue math."""

import pytest

from companion_pipeline.captions import (
    LRM, bidi_wrap, caption_text, fmt_srt_time, readable, split_intro)
from companion_pipeline.config import load_language


@pytest.fixture(scope="module")
def en():
    return load_language("en")


def test_fmt_srt_time():
    assert fmt_srt_time(0.0) == "00:00:00,000"
    assert fmt_srt_time(0.4) == "00:00:00,400"
    assert fmt_srt_time(75.123) == "00:01:15,123"
    assert fmt_srt_time(3661.5) == "01:01:01,500"


def test_readable_maps_spellouts(en):
    assert readable(
        "visit s dot I-A-S-E-R dot A-I, slash prompt.", en
    ) == "visit s.iaser.ai/prompt."
    assert readable("research from I-A-S-E-R dot A-I, an org", en) \
        == "research from iaser.ai, an org"


def test_readable_longest_pattern_wins(en):
    # the full-URL spellout must not be half-eaten by the domain spellout
    out = readable("go to s dot I-A-S-E-R dot A-I, slash prompt now", en)
    assert "s.iaser.ai/prompt" in out
    assert "I-A-S-E-R" not in out


def test_bidi_noop_for_ltr(en):
    assert bidi_wrap("visit s.iaser.ai/prompt", en) \
        == "visit s.iaser.ai/prompt"


class FakeRtl:
    direction = "rtl"
    spellouts = ()


def test_bidi_wraps_ltr_runs_in_rtl():
    out = bidi_wrap("زر s.iaser.ai/prompt الآن", FakeRtl())
    assert f"{LRM}s.iaser.ai/prompt{LRM}" in out


def test_bidi_wraps_brand_names():
    out = bidi_wrap("افتح ChatGPT من", FakeRtl())
    assert f"{LRM}ChatGPT{LRM}" in out


def test_bidi_leaves_pure_rtl_untouched():
    text = "افتح القائمة الجانبية"
    assert bidi_wrap(text, FakeRtl()) == text


def test_caption_text_combines(en):
    assert caption_text(
        "visit s dot I-A-S-E-R dot A-I, slash prompt.", en
    ) == "visit s.iaser.ai/prompt."


def test_split_intro_proportional():
    text = "One. Two two two two. Three!"
    cues = split_intro(text, 0.4, 10.0)
    assert len(cues) == 3
    assert cues[0][0] == pytest.approx(0.4)
    # contiguous
    assert cues[0][1] == pytest.approx(cues[1][0])
    assert cues[1][1] == pytest.approx(cues[2][0])
    # total duration preserved
    assert cues[-1][1] == pytest.approx(0.4 + 10.0)
    # longer sentence gets proportionally more time
    assert (cues[1][1] - cues[1][0]) > (cues[0][1] - cues[0][0])
    # text preserved in order
    assert [c[2] for c in cues] == ["One.", "Two two two two.", "Three!"]


def test_split_intro_single_sentence():
    cues = split_intro("Just one sentence.", 0.4, 5.0)
    assert len(cues) == 1
    assert cues[0][0] == pytest.approx(0.4)
    assert cues[0][1] == pytest.approx(5.4)
    assert cues[0][2] == "Just one sentence."
