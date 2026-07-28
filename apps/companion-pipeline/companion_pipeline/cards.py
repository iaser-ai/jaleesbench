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
        pg.screenshot(path=str(png))
        b.close()
    return png
