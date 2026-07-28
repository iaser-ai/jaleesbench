"""Config loading: the EN reference loads completely; missing pieces fail
fast with errors that name the language and key."""

import pytest

from companion_pipeline import cards
from companion_pipeline.config import (
    ConfigError, VIDEOS, available_languages, load_language)


def test_en_is_available():
    assert "en" in available_languages()


def test_en_loads_fully():
    cfg = load_language("en")
    assert cfg.lang == "en"
    assert cfg.direction == "ltr"
    assert cfg.tts.engine == "gemini"
    assert cfg.tts.voice == "Puck"
    assert cfg.tts.style.startswith("Say this as a warm")
    assert len(cfg.prompt) == 1492
    assert cfg.prompt_chars == 1492
    assert set(cfg.videos) == set(VIDEOS)
    assert len(cfg.spellouts) == 2


def test_en_vo_matches_seed_shape():
    cfg = load_language("en")
    assert len(cfg.videos["chatgpt"].segments) == 5
    assert len(cfg.videos["claude"].segments) == 5
    assert len(cfg.videos["gemini"].segments) == 7
    assert cfg.videos["chatgpt"].segments[0].offset == 0.5
    assert cfg.videos["gemini"].segments[-1].offset == 43.2
    for v in cfg.videos.values():
        assert v.intro_vo.startswith("Assalamu alaikum!")
        assert v.product in v.intro_vo


def test_en_clips_exist():
    cfg = load_language("en")
    for name in VIDEOS:
        assert cfg.clip_path(name).exists()


def test_unknown_language_fails_fast():
    with pytest.raises(ConfigError, match="unknown language"):
        load_language("xx")


def test_missing_clip_names_language_and_video(tmp_path):
    cfg = load_language("en")
    object.__setattr__(cfg.videos["chatgpt"], "clip", "nope.mp4")
    with pytest.raises(ConfigError, match="en/chatgpt"):
        cfg.clip_path("chatgpt")


def test_card_html_substitutes_placeholders():
    cfg = load_language("en")
    v = cfg.videos["chatgpt"]
    intro = cards.card_html(cfg, v, "intro")
    assert "Make ChatGPT a better" in intro
    assert "{product}" not in intro
    assert 'dir="ltr"' in intro
    outro = cards.card_html(cfg, v, "outro")
    assert "Claude and Gemini" in outro
    assert "{others}" not in outro


def test_card_html_rejects_bad_kind():
    cfg = load_language("en")
    with pytest.raises(ValueError):
        cards.card_html(cfg, cfg.videos["chatgpt"], "middle")
