"""tts_spike phase: spike registry sanity + skeleton-language behavior."""

import pytest

from companion_pipeline.config import (
    ConfigError, available_languages, load_language, validate_skeleton)
from companion_pipeline.spike import CANDIDATE_VOICES, SAMPLE_TEXTS, run_spike


def test_sample_texts_cover_target_languages():
    assert set(SAMPLE_TEXTS) == {"ar", "ur", "id"}
    for lang, text in SAMPLE_TEXTS.items():
        assert len(text) > 50, f"{lang} sample too short to judge a voice"


def test_candidate_voices_include_en_baseline():
    assert "Puck" in CANDIDATE_VOICES  # shipped EN voice as reference
    assert len(CANDIDATE_VOICES) >= 3  # 2-3 candidates + baseline


def test_run_spike_rejects_unknown_language():
    with pytest.raises(RuntimeError, match="no spike sample text"):
        run_spike(("xx",), ("Puck",))


def test_skeleton_languages_are_listed():
    langs = available_languages()
    for code in ("ar", "ur", "id"):
        assert code in langs


@pytest.mark.parametrize("code", ["ar", "ur", "id"])
def test_skeleton_language_fails_fast_naming_missing_piece(code):
    # Skeletons carry config.toml + spellouts.toml only; loading must fail
    # fast, naming the first missing piece (vo files / prompt.txt arrive in
    # the localized_content / translated_prompts phases).
    with pytest.raises(ConfigError, match="missing required file"):
        load_language(code)


@pytest.mark.parametrize("code", ["ar", "ur", "id"])
def test_skeleton_core_passes_validation(code):
    # The plan's "config skeletons pass validation" criterion: the core
    # (config.toml + spellouts.toml) must be fully valid, with only
    # not-yet-delivered phase assets reported as missing.
    missing = validate_skeleton(code)
    assert "prompt.txt" not in missing        # delivered: translated_prompts
    assert "vo/chatgpt.toml" in missing       # localized_content phase
    assert "cards/intro.html" in missing      # localized_content phase


@pytest.mark.parametrize("code", ["ar", "ur", "id"])
def test_translated_prompt_fits_entry_limits(code):
    # ChatGPT's custom-instructions field caps at ~1,500 chars (EN
    # GUIDE_MIN was sized to 1,492 for exactly this reason).
    import tomllib
    from companion_pipeline.config import LANGUAGES_DIR
    text = (LANGUAGES_DIR / code / "prompt.txt").read_text(
        encoding="utf-8").rstrip("\n")
    assert 0 < len(text) <= 1500
    with open(LANGUAGES_DIR / code / "config.toml", "rb") as f:
        raw = tomllib.load(f)
    assert raw["recording"]["prompt_chars"] == len(text)
    # URL and honorific survive translation byte-for-byte
    assert ("https://api.askansari.ai/api/v2/mcp-complete"
            "?q=your+question&src=jbprompt") in text
    assert "ﷺ" in text
    # the 3+3 bullet split for Gemini's two-part paste stays within the
    # configured clipboard bounds
    bullets = text.split("\n- ")
    assert len(bullets) == 7  # header + 6 bullets, mirroring EN
    p1 = bullets[0] + "\n- " + "\n- ".join(bullets[1:4])
    p2 = "- " + "\n- ".join(bullets[4:])
    lo = raw["recording"]["gemini_part_min"]
    hi = raw["recording"]["gemini_part_max"]
    assert lo < len(p1) < hi
    assert lo < len(p2) < hi


def test_complete_language_has_nothing_missing():
    assert validate_skeleton("en") == []


def test_skeleton_validation_rejects_broken_core(tmp_path, monkeypatch):
    import shutil
    from companion_pipeline import config
    langs = tmp_path / "languages"
    langs.mkdir()
    shutil.copytree(config.LANGUAGES_DIR / "ar", langs / "ar")
    cfg = langs / "ar" / "config.toml"
    cfg.write_text(cfg.read_text().replace('voice = "Puck"', ""))
    monkeypatch.setattr(config, "LANGUAGES_DIR", langs)
    with pytest.raises(ConfigError, match="voice"):
        validate_skeleton("ar")


def test_rtl_skeletons_declare_direction_and_fonts():
    import tomllib
    from companion_pipeline.config import LANGUAGES_DIR
    for code, font in (("ar", "Noto Naskh Arabic"),
                       ("ur", "Noto Nastaliq Urdu")):
        with open(LANGUAGES_DIR / code / "config.toml", "rb") as f:
            raw = tomllib.load(f)
        assert raw["dir"] == "rtl"
        assert font in raw["cards"]["css"]
    with open(LANGUAGES_DIR / "id" / "config.toml", "rb") as f:
        assert tomllib.load(f)["dir"] == "ltr"