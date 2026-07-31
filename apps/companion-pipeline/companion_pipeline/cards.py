"""Intro/outro card rendering: HTML -> PNG via headless Chrome.

The page frame (geometry + base styling) lives here; the card *body* is a
per-language template (languages/<lang>/cards/{intro,outro}.html) with
{product} / {others} placeholders, and each language config can append a
CSS override block (fonts, line-height, direction tweaks) — required for
RTL scripts, where e.g. Nastaliq needs taller line metrics than the
EN-tuned defaults.
"""

import base64
from pathlib import Path

from .config import LanguageConfig, OUT_DIR, PIPELINE_ROOT, VideoConfig

FONTS_DIR = PIPELINE_ROOT / "assets" / "fonts"

# Vendored faces, keyed by the family a language's card CSS names. Cards
# used to name a family and hope the host had it — Chrome substitutes a
# missing family SILENTLY, so `ur` rendered right only because macOS ships
# NotoNastaliq.ttc, and `ar` had been rendering in its Geeza Pro fallback
# the whole time. Self-hosting these makes the output identical on every
# machine and matches the faces iaser.ai serves on the web surfaces.
#
# Two subsets per family: cards mix scripts (product names and
# s.iaser.ai/prompt are Latin inside otherwise-RTL text). One file covers
# both weights — these are variable fonts.
VENDORED_FONTS = {
    "Noto Naskh Arabic": ("NotoNaskhArabic-arabic.woff2",
                          "NotoNaskhArabic-latin.woff2"),
    "Noto Nastaliq Urdu": ("NotoNastaliqUrdu-arabic.woff2",
                           "NotoNastaliqUrdu-latin.woff2"),
}


def font_face_css(family: str) -> str:
    """@font-face rules embedding the vendored files as data: URIs.

    Inlined rather than linked so the card HTML is self-contained: it
    renders the same from any working directory, and a moved or deleted
    file fails here, at read time, instead of silently degrading to a
    substituted face at screenshot time.
    """
    if not family:
        return ""
    if family not in VENDORED_FONTS:
        raise RuntimeError(
            f"card font {family!r} is required but not vendored. Add the "
            f"woff2 (plus its OFL text) under assets/fonts/ and register "
            f"it in VENDORED_FONTS — naming a family the host might not "
            f"have is what this replaced.")
    rules = []
    for fname in VENDORED_FONTS[family]:
        path = FONTS_DIR / fname
        if not path.exists():
            raise RuntimeError(
                f"vendored font missing: {path} — required by {family!r}")
        b64 = base64.b64encode(path.read_bytes()).decode("ascii")
        rules.append(
            f"@font-face {{ font-family:'{family}'; font-style:normal;"
            f" font-weight:400 700;"
            f" src:url(data:font/woff2;base64,{b64}) format('woff2'); }}")
    return "\n".join(rules)


BASE_HTML = """<!doctype html><html dir="__DIR__"><head>
<meta charset="utf-8"><style>
__FONT_FACES__
  body { margin:0; width:1376px; height:800px; background:#0d0d0d;
         display:flex; align-items:center; justify-content:center;
         font-family:-apple-system,'Helvetica Neue',sans-serif; }
  .wrap { text-align:center; max-width:1050px; }
  .kicker { color:#9ca3af; font-size:30px; margin-bottom:26px; }
  h1 { color:#fff; font-size:56px; margin:0 0 30px; font-weight:700;
       line-height:1.25; }
  .pill { display:inline-block; background:#1f2937; color:#fff;
       border:1px solid #374151; border-radius:999px; padding:20px 44px;
       font-size:38px; font-family:ui-monospace,monospace; }
  .sub { color:#9ca3af; font-size:27px; margin-top:30px; line-height:1.4; }
__EXTRA_CSS__
</style></head><body><div class="wrap">__BODY__</div></body></html>"""


def card_html(cfg: LanguageConfig, video: VideoConfig, kind: str) -> str:
    if kind == "intro":
        body = cfg.intro_card_html
    elif kind == "outro":
        body = cfg.outro_card_html
    else:
        raise ValueError(f"kind must be intro|outro, got {kind!r}")
    body = (body.replace("{product}", video.product)
                .replace("{others}", video.others))
    return (BASE_HTML.replace("__DIR__", cfg.direction)
                     .replace("__FONT_FACES__",
                              font_face_css(cfg.card_require_font))
                     .replace("__EXTRA_CSS__", cfg.card_css)
                     .replace("__BODY__", body))


# Does a named family actually RESOLVE, or is the browser quietly falling
# back? `document.fonts.check()` cannot answer this — it returns true for
# families that do not exist (verified: a nonsense name checks true). The
# reliable test is metric comparison: render the same text under the target
# family and under a family that cannot exist, both backed by the same
# generic. Identical widths mean the target never resolved.
_FONT_PROBE_JS = """
(fam) => {
  const probe = (stack) => {
    const s = document.createElement('span');
    s.textContent = 'اردو عربی نستعلیق ابجد هوز';
    s.style.cssText = 'position:absolute;visibility:hidden;'
                    + 'font-size:72px;white-space:nowrap;font-family:' + stack;
    document.body.appendChild(s);
    const w = s.getBoundingClientRect().width;
    s.remove();
    return w;
  };
  return Math.abs(probe("'__no_such_family__', serif")
                  - probe("'" + fam + "', serif")) > 0.5;
}"""


def assert_font_available(pg, cfg: LanguageConfig) -> None:
    """Fail before a card is screenshotted in the wrong typeface.

    Chrome substitutes a missing family silently, so an absent face never
    announces itself — it just ships wrong-looking cards. That is sharpest
    for Urdu: the config raises line-height to 2.0 for Nastaliq's tall
    metrics, so falling back to a Naskh-shaped serif applies Nastaliq
    spacing to the wrong face. Empty require_font means the language has
    not committed to a face and is deliberately unguarded.
    """
    if not cfg.card_require_font:
        return
    # The face is embedded as a data: URI, so it has to finish decoding
    # before metrics mean anything.
    pg.evaluate("f => document.fonts.load('72px \"' + f + '\"')",
                cfg.card_require_font)
    pg.evaluate("() => document.fonts.ready")
    if not pg.evaluate(_FONT_PROBE_JS, cfg.card_require_font):
        raise RuntimeError(
            f"[{cfg.lang}] card font {cfg.card_require_font!r} did not "
            f"resolve — cards would render in a substituted face with "
            f"{cfg.lang}-tuned line metrics. The face is vendored at "
            f"assets/fonts/, so this means the embedded @font-face failed "
            f"to decode rather than a missing system font.")


def render_card(cfg: LanguageConfig, video: VideoConfig, kind: str) -> Path:
    from playwright.sync_api import sync_playwright

    work = OUT_DIR / "cards" / cfg.lang
    work.mkdir(parents=True, exist_ok=True)
    html_path = work / f"card-{video.name}-{kind}.html"
    html_path.write_text(card_html(cfg, video, kind), encoding="utf-8")
    png = work / f"card-{video.name}-{kind}.png"
    with sync_playwright() as pw:
        b = pw.chromium.launch(channel="chrome", headless=True)
        pg = b.new_page(viewport={"width": 1376, "height": 800})
        pg.goto(f"file://{html_path}")
        pg.wait_for_timeout(400)
        assert_font_available(pg, cfg)
        pg.screenshot(path=str(png))
        b.close()
    return png
