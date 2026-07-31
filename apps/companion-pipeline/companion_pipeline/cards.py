"""Intro/outro card rendering: HTML -> PNG via headless Chrome.

The page frame (geometry + base styling) lives here; the card *body* is a
per-language template (languages/<lang>/cards/{intro,outro}.html) with
{product} / {others} placeholders, and each language config can append a
CSS override block (fonts, line-height, direction tweaks) — required for
RTL scripts, where e.g. Nastaliq needs taller line metrics than the
EN-tuned defaults.
"""

from pathlib import Path

from .config import LanguageConfig, OUT_DIR, VideoConfig

BASE_HTML = """<!doctype html><html dir="__DIR__"><head>
<meta charset="utf-8"><style>
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
    if not pg.evaluate(_FONT_PROBE_JS, cfg.card_require_font):
        raise RuntimeError(
            f"[{cfg.lang}] card font {cfg.card_require_font!r} is not "
            f"available to Chrome on this machine — cards would render in "
            f"a substituted face with {cfg.lang}-tuned line metrics. "
            f"Install the font or vendor it into the card CSS as a "
            f"self-hosted @font-face, the way iaser.ai serves the web "
            f"surfaces.")


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
