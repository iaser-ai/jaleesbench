"""tts_spike phase: spike registry sanity + skeleton-language behavior."""

import pytest

from companion_pipeline.config import (
    ConfigError, available_languages, load_language, split_prompt,
    validate_skeleton)
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


@pytest.mark.parametrize("code", ["ar", "ur", "id", "en"])
def test_translated_prompt_fits_entry_limits(code):
    # ChatGPT's custom-instructions field caps at ~1,500 chars (EN
    # GUIDE_MIN was sized to 1,492 for exactly this reason). EXACT file
    # content — no stripping: recording drivers and the prompt page copy
    # the file byte-for-byte, so a trailing newline is an off-by-one bug.
    import tomllib
    from companion_pipeline.config import LANGUAGES_DIR
    text = (LANGUAGES_DIR / code / "prompt.txt").read_text(encoding="utf-8")
    assert not text.endswith("\n"), "prompt.txt must not end with a newline"
    assert 0 < len(text) <= 1500
    with open(LANGUAGES_DIR / code / "config.toml", "rb") as f:
        raw = tomllib.load(f)
    assert raw["recording"]["prompt_chars"] == len(text)
    if code == "en":
        return
    # URL and honorific survive translation byte-for-byte
    assert ("https://api.askansari.ai/api/v2/mcp-complete"
            "?q=your+question&src=jbprompt") in text
    assert "ﷺ" in text
    # the two-part split (with the part-2 prose lead-in) stays within the
    # configured clipboard bounds
    bullets = text.split("\n- ")
    assert len(bullets) == 7  # header + 6 bullets, mirroring EN
    leadin = raw["recording"]["gemini_part2_leadin"]
    assert leadin, ("ar/ur/id part 2 must carry a prose lead-in — "
                    "Gemini's rewriter language-switches bare-bullet "
                    "openings (observed for Arabic)")
    # Derive the parts from gemini_parts(), never by re-implementing the
    # split here: this test used to hardcode 3/3 and would have gone on
    # asserting the old boundary after ur moved to 5.
    p1, p2 = split_prompt(text, leadin,
                          raw["recording"].get("gemini_split_after", 3), code)
    lo = raw["recording"]["gemini_part_min"]
    hi = raw["recording"]["gemini_part_max"]
    assert lo < len(p1) < hi
    assert lo < len(p2) < hi
    # Every bullet survives the split exactly once, wherever the boundary
    # falls — a boundary move must never drop or duplicate a line.
    for b in bullets[1:]:
        assert (b in p1) != (b in p2), f"[{code}] bullet not in exactly one part"


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


@pytest.mark.parametrize("code", ["ar", "ur", "id"])
def test_handoff_prompt_package_integrity(code):
    # The prompt-page handoff must be byte-identical to the canonical
    # prompt, and the two Gemini part files must equal the shared split
    # (part 2 = prose lead-in + last three bullets; the lead-in exists
    # ONLY in the parts rendering, never in the canonical prompt).
    import tomllib
    from companion_pipeline.config import LANGUAGES_DIR, PIPELINE_ROOT
    canonical = (LANGUAGES_DIR / code / "prompt.txt").read_text(
        encoding="utf-8")
    with open(LANGUAGES_DIR / code / "config.toml", "rb") as f:
        leadin = tomllib.load(f)["recording"]["gemini_part2_leadin"]
    hand = PIPELINE_ROOT / "handoff" / "prompt-page" / code
    assert (hand / "prompt.txt").read_text(encoding="utf-8") == canonical
    p1 = (hand / "gemini-part1.txt").read_text(encoding="utf-8")
    p2 = (hand / "gemini-part2.txt").read_text(encoding="utf-8")
    assert p2.startswith(leadin + "\n")
    assert leadin not in canonical
    assert p1 + "\n" + p2.removeprefix(leadin + "\n") == canonical
    # Reassembling to the canonical prompt is boundary-AGNOSTIC — it holds
    # for any split, so on its own it would have let ur's package keep
    # shipping the superseded 3/3 files. Pin the parts to the configured
    # boundary as well; this is what the re-vendor package is checked on.
    with open(LANGUAGES_DIR / code / "config.toml", "rb") as f:
        split_after = tomllib.load(f)["recording"].get(
            "gemini_split_after", 3)
    assert (p1, p2) == split_prompt(canonical, leadin, split_after, code)


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