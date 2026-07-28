"""tts_spike phase: spike registry sanity + skeleton-language behavior."""

import pytest

from companion_pipeline.config import (
    ConfigError, available_languages, load_language)
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