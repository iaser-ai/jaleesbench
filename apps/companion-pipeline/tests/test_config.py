"""Config loading: the EN reference loads completely; missing pieces fail
fast with errors that name the language and key."""

import shutil

import pytest

from companion_pipeline import cards, config
from companion_pipeline.config import (
    ConfigError, LANGUAGES_DIR, VIDEOS, available_languages, load_language)


@pytest.fixture
def broken_lang(tmp_path, monkeypatch):
    """Clone the EN config as language 'xy' under a temp languages dir;
    the test then breaks one piece and asserts fail-fast behavior."""
    langs = tmp_path / "languages"
    langs.mkdir()
    shutil.copytree(LANGUAGES_DIR / "en", langs / "xy")
    monkeypatch.setattr(config, "LANGUAGES_DIR", langs)
    return langs / "xy"


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


def test_broken_clone_loads_before_breaking(broken_lang):
    assert load_language("xy").lang == "xy"


def test_missing_tts_key_fails_fast(broken_lang):
    cfg = broken_lang / "config.toml"
    cfg.write_text(cfg.read_text().replace('voice = "Puck"', ""))
    with pytest.raises(ConfigError, match="missing required key: 'voice'"):
        load_language("xy")


def test_missing_recording_key_fails_fast(broken_lang):
    cfg = broken_lang / "config.toml"
    cfg.write_text(cfg.read_text().replace("prompt_chars = 1492", ""))
    with pytest.raises(ConfigError, match="prompt_chars"):
        load_language("xy")


def test_invalid_dir_fails_fast(broken_lang):
    cfg = broken_lang / "config.toml"
    cfg.write_text(cfg.read_text().replace('dir = "ltr"', 'dir = "both"'))
    with pytest.raises(ConfigError, match="dir must be"):
        load_language("xy")


def test_missing_vo_file_fails_fast(broken_lang):
    (broken_lang / "vo" / "claude.toml").unlink()
    with pytest.raises(ConfigError, match="xy/vo/claude"):
        load_language("xy")


def test_missing_segment_key_fails_fast(broken_lang):
    vo = broken_lang / "vo" / "chatgpt.toml"
    vo.write_text(vo.read_text().replace("offset = 0.5", ""))
    with pytest.raises(ConfigError, match="offset"):
        load_language("xy")


def test_empty_segments_fail_fast(broken_lang):
    vo = broken_lang / "vo" / "chatgpt.toml"
    head = vo.read_text().split("[[segments]]")[0]
    vo.write_text(head + "segments = []\n")
    with pytest.raises(ConfigError, match="segments must not be empty"):
        load_language("xy")


def test_missing_prompt_file_fails_fast(broken_lang):
    (broken_lang / "prompt.txt").unlink()
    with pytest.raises(ConfigError, match="missing required file"):
        load_language("xy")


def test_missing_card_template_fails_fast(broken_lang):
    (broken_lang / "cards" / "outro.html").unlink()
    with pytest.raises(ConfigError, match="missing required file"):
        load_language("xy")


def test_missing_article_key_fails_fast(broken_lang):
    cfg = broken_lang / "config.toml"
    cfg.write_text(cfg.read_text().replace("article_url =", "unused ="))
    with pytest.raises(ConfigError, match="article_url"):
        load_language("xy")


def test_ui_labels_merge_over_defaults(broken_lang):
    """A partially-localized ui section must fall back, not KeyError:
    labels are discovered live a few at a time."""
    cfg = broken_lang / "config.toml"
    cfg.write_text(cfg.read_text()
                   + '\n[recording.gemini_ui]\nsubmit = "Kirim"\n')
    c = load_language("xy")
    assert c.gemini_ui["submit"] == "Kirim"
    assert c.gemini_ui["delete_all"] == "Delete all"   # default survives


def test_recording_load_skips_later_phase_assets(broken_lang):
    """Clips are recorded a phase before VO and cards exist."""
    (broken_lang / "vo" / "claude.toml").unlink()
    (broken_lang / "cards" / "intro.html").unlink()
    cfg = load_language("xy", require_later_assets=False)
    assert cfg.videos == {}
    assert cfg.intro_card_html == ""
    # the core the drivers actually read still loads and still fails fast
    assert cfg.copy_button_label and cfg.prompt_url


def test_clip_path_explains_a_recording_only_config(broken_lang):
    cfg = load_language("xy", require_later_assets=False)
    with pytest.raises(ConfigError, match="require_later_assets=False"):
        cfg.clip_path("chatgpt")


def test_missing_spellouts_file_fails_fast(broken_lang):
    (broken_lang / "spellouts.toml").unlink()
    with pytest.raises(ConfigError, match="xy/spellouts"):
        load_language("xy")


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
