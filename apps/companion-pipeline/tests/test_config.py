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
    the test then breaks one piece and asserts fail-fast behavior.

    The clone gets assistant-UI label sections EN itself doesn't carry (EN's
    labels are the built-in defaults). Without them 'xy' would be a non-EN
    language with no recced UI at all, which load_language refuses outright
    — every test here would fail on that instead of on the thing it breaks.
    The sections are deliberately PARTIAL: that is the legal shape, and it
    is what test_ui_labels_merge_over_defaults asserts.
    """
    langs = tmp_path / "languages"
    langs.mkdir()
    shutil.copytree(LANGUAGES_DIR / "en", langs / "xy")
    cfg = langs / "xy" / "config.toml"
    cfg.write_text(cfg.read_text()
                   + '\n[recording.chatgpt_ui]\nsave = "Simpan"\n'
                   + '\n[recording.gemini_ui]\nsubmit = "Kirim"\n')
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
    cfg.write_text(cfg.read_text().replace("article_entry_url =", "unused ="))
    with pytest.raises(ConfigError, match="article_entry_url"):
        load_language("xy")


def test_ui_labels_merge_over_defaults(broken_lang):
    """A partially-localized ui section must fall back, not KeyError:
    labels are discovered live a few at a time."""
    c = load_language("xy")
    assert c.gemini_ui["submit"] == "Kirim"           # localized wins
    assert c.gemini_ui["delete_all"] == "Delete all"  # default survives


@pytest.mark.parametrize("section", ["chatgpt_ui", "gemini_ui"])
def test_absent_ui_section_fails_fast(broken_lang, section):
    """Absent entirely is NOT partial localization — it means nobody has
    recced that assistant in this language. Silently handing the driver EN
    labels is how the first Urdu take died, hunting for 'Personalization'
    in an Urdu interface."""
    cfg = broken_lang / "config.toml"
    cfg.write_text(cfg.read_text().replace(f"[recording.{section}]",
                                           "[recording.unused]"))
    with pytest.raises(ConfigError, match=section):
        load_language("xy")


def test_en_needs_no_ui_sections():
    """EN is the reference: its labels ARE the built-in defaults, so the
    absent-section rule must not fire on it."""
    assert load_language("en").chatgpt_ui["save"] == "Save"


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


def test_card_font_guard_detects_a_missing_face():
    """The guard must tell a resolved face from an absent one. It exists
    because document.fonts.check() cannot: that API returns true for
    families that do not exist, so it would have passed everything.

    Driven through the real card HTML, so it exercises the vendored
    @font-face rather than whatever the host machine happens to ship."""
    from playwright.sync_api import sync_playwright
    from companion_pipeline.cards import BASE_HTML, _FONT_PROBE_JS, font_face_css
    cfg = load_language("ur", require_later_assets=False)
    html = (BASE_HTML.replace("__DIR__", "rtl")
            .replace("__FONT_FACES__", font_face_css(cfg.card_require_font))
            .replace("__EXTRA_CSS__", "").replace("__BODY__", "<h1>اردو</h1>"))
    with sync_playwright() as pw:
        b = pw.chromium.launch(channel="chrome", headless=True)
        pg = b.new_page()
        pg.set_content(html)
        pg.evaluate("f => document.fonts.load('72px \"' + f + '\"')",
                    cfg.card_require_font)
        pg.evaluate("() => document.fonts.ready")
        assert pg.evaluate(_FONT_PROBE_JS, cfg.card_require_font)
        assert not pg.evaluate(_FONT_PROBE_JS, "No Such Family 91731")
        b.close()


def test_rtl_languages_require_a_vendored_face():
    """ar and ur both pin a face now (Waleed, 2026-07-31). Naming a family
    and hoping the host has it is what this replaced: ar had been silently
    rendering in a Geeza Pro fallback, never the face its config named."""
    from companion_pipeline.cards import VENDORED_FONTS
    for lang, family in (("ar", "Noto Naskh Arabic"),
                         ("ur", "Noto Nastaliq Urdu")):
        cfg = load_language(lang, require_later_assets=False)
        assert cfg.card_require_font == family
        assert family in VENDORED_FONTS
        # The required face must also be the one the CSS actually asks for.
        assert family in cfg.card_css


def test_font_face_css_embeds_every_subset_and_refuses_unvendored():
    """Cards mix scripts, so each family ships an arabic AND a latin file;
    a family that isn't vendored must fail loudly rather than emit CSS that
    silently resolves to nothing."""
    from companion_pipeline.cards import VENDORED_FONTS, font_face_css
    for family, files in VENDORED_FONTS.items():
        css = font_face_css(family)
        assert css.count("@font-face") == len(files) == 2
        assert css.count("data:font/woff2;base64,") == 2
        assert "url(https://" not in css       # self-hosted, never remote
    assert font_face_css("") == ""             # unguarded language
    with pytest.raises(RuntimeError, match="not vendored"):
        font_face_css("Comic Sans MS")


def test_vendored_fonts_ship_their_licenses():
    """OFL requires the license to travel with the files."""
    from companion_pipeline.cards import FONTS_DIR, VENDORED_FONTS
    for family, files in VENDORED_FONTS.items():
        for fname in files:
            path = FONTS_DIR / fname
            assert path.exists()
            assert path.read_bytes()[:4] == b"wOF2"   # real woff2
        slug = family.replace(" ", "")
        licence = FONTS_DIR / f"OFL-{slug}.txt"
        assert licence.exists(), f"missing OFL text for {family}"
        assert "SIL Open Font License" in licence.read_text(encoding="utf-8")


def test_vendored_bytes_resolve_without_any_system_font():
    """Proof the self-hosting works, not just that macOS ships Nastaliq.

    The positive check above would pass on this machine even with no
    vendored file at all, because the OS happens to have the face. So
    register the vendored BYTES under a family name no system font can
    supply: if that resolves, the data: URI is doing the work.
    """
    import base64
    from playwright.sync_api import sync_playwright
    from companion_pipeline.cards import FONTS_DIR, _FONT_PROBE_JS
    alias = "Vendor Proof Face 91731"
    b64 = base64.b64encode(
        (FONTS_DIR / "NotoNastaliqUrdu-arabic.woff2").read_bytes()
    ).decode("ascii")
    html = (f"<!doctype html><meta charset=utf-8><style>@font-face {{"
            f" font-family:'{alias}'; src:url(data:font/woff2;base64,{b64})"
            f" format('woff2'); }}</style><body></body>")
    with sync_playwright() as pw:
        b = pw.chromium.launch(channel="chrome", headless=True)
        pg = b.new_page()
        pg.set_content(html)
        pg.evaluate("f => document.fonts.load('72px \"' + f + '\"')", alias)
        pg.evaluate("() => document.fonts.ready")
        assert pg.evaluate(_FONT_PROBE_JS, alias)
        b.close()


def test_chatgpt_driver_redacts_history_and_has_no_stale_selector():
    """The ar/ur chatgpt clips filmed the conversation list and had to be
    destroyed. Two things must stay true: the driver arms a history
    redaction, and it no longer reaches for the selector that broke."""
    from companion_pipeline.drivers import chatgpt as d
    src = (LANGUAGES_DIR.parent / "companion_pipeline" / "drivers"
           / "chatgpt.py").read_text(encoding="utf-8")
    # the redaction exists, hides conversation links, and is observer-based
    assert 'a[href^="/c/"]' in d.SIDEBAR_REDACT_JS      # conversation links
    assert "MutationObserver" in d.SIDEBAR_REDACT_JS     # survives re-mounts
    assert "visibility" in d.SIDEBAR_REDACT_JS           # no layout shift
    # it is armed before rolling AND asserted, so it cannot fail open
    assert "refusing to roll" in src
    # The selector that no longer exists in ChatGPT's UI must not be USED.
    # Match the selector form, not the bare name — the name still appears
    # in prose explaining why it was dropped, and a test that forbids
    # naming the mistake discourages documenting it.
    assert "[data-testid='open-sidebar-button']" not in src
    assert "[data-testid='accounts-profile-button']" in src
