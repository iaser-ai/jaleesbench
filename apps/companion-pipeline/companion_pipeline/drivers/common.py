"""Shared pieces for the per-assistant recording drivers (ported from the
EN seed's clip_copypaste*.py)."""

import subprocess

# Written to the clipboard before a copy click so a stale read is a loud
# failure instead of a plausible wrong payload.
_SENTINEL = "__jb_clipboard_sentinel__"

# Card rendered by navigating an about:blank page (left half).
CARD_JS = """([line1, line2]) => {
  document.body.style.cssText = 'margin:0;background:#0d0d0d;display:flex;'
    + 'align-items:center;justify-content:center;height:100vh;'
    + 'font-family:-apple-system,sans-serif';
  document.body.innerHTML = `<div style="text-align:center">
    <div style="color:#9ca3af;font-size:22px;margin-bottom:18px">${line1}</div>
    <div style="display:inline-block;background:#1f2937;color:#fff;
      border:1px solid #374151;border-radius:999px;padding:14px 30px;
      font-size:26px;font-family:ui-monospace,monospace">${line2}</div></div>`;
}"""

# Full-screen overlay card (no navigation, so viewport emulation survives).
OVERLAY_JS = """([line1, line2]) => {
  let o = document.getElementById('__jb_card');
  if (!o) {
    o = document.createElement('div');
    o.id = '__jb_card';
    o.style.cssText = 'position:fixed;inset:0;z-index:2147483644;'
      + 'background:#0d0d0d;display:flex;align-items:center;'
      + 'justify-content:center;font-family:-apple-system,sans-serif;'
      + 'transition:opacity .5s';
    document.documentElement.appendChild(o);
  }
  o.style.opacity = '1';
  while (o.firstChild) o.removeChild(o.firstChild);
  if (line2 !== null) {
    const wrap = document.createElement('div');
    wrap.style.textAlign = 'center';
    const l1 = document.createElement('div');
    l1.style.cssText = 'color:#9ca3af;font-size:22px;margin-bottom:18px';
    l1.textContent = line1;
    const l2 = document.createElement('div');
    l2.style.cssText = 'display:inline-block;background:#1f2937;color:#fff;'
      + 'border:1px solid #374151;border-radius:999px;padding:14px 30px;'
      + 'font-size:26px;font-family:ui-monospace,monospace';
    l2.textContent = line2;
    wrap.appendChild(l1); wrap.appendChild(l2);
    o.appendChild(wrap);
  }
}"""

OVERLAY_OFF_JS = """() => {
  const o = document.getElementById('__jb_card');
  if (o) { o.style.opacity = '0'; setTimeout(() => o.remove(), 550); }
}"""


def clipboard() -> str:
    return subprocess.run(["pbpaste"], capture_output=True, text=True).stdout


def stable_value(page, loc, rounds: int = 4):
    """Poll an input until its value has been stable for `rounds` reads
    (saves/reads can lag by many seconds)."""
    last, stable = None, 0
    for _ in range(30):
        v = loc.input_value()
        stable = stable + 1 if v == last else 0
        last = v
        if stable >= rounds:
            break
        page.wait_for_timeout(500)
    return last


def open_article(s, left, cfg, width: int = 657, height: int = 765):
    """Card -> short link -> (on camera) the page's own language link.

    Every language enters on the SAME short link, because that is the only
    address a viewer could realistically retype; it lands on the EN
    article and the take clicks through to the localized one on camera.
    The localized URL is never navigated to directly.
    """
    left.evaluate(CARD_JS, [cfg.card_goto_line, cfg.article_url_display])
    left.wait_for_timeout(3200)
    left.goto(cfg.article_entry_url)
    left.set_viewport_size({"width": width, "height": height})
    left.wait_for_timeout(2600)
    s.ensure_cursor(left)

    if cfg.article_lang_link:
        sel = f"a:has-text('{cfg.article_lang_link}')"
        assert left.locator(sel).count(), (
            f"no {cfg.article_lang_link!r} language link on "
            f"{cfg.article_entry_url}")
        s.move_click(left, sel, after_ms=1400)
        left.wait_for_function(
            "lang => location.pathname.includes('/' + lang + '/')",
            arg=cfg.lang, timeout=20000)
        left.set_viewport_size({"width": width, "height": height})
        left.wait_for_timeout(2200)
        s.ensure_cursor(left)
    print("article:", left.url)


def copy_block(s, left, button_sel: str, expected_chars: int,
               label: str) -> str:
    """Highlight + click a copy button (article OR prompt page) and verify
    the clipboard holds the expected payload.

    Set the clipboard to a sentinel first: reading it too soon after the
    click otherwise returns the PREVIOUS payload, which reads as a
    plausible-but-wrong result rather than a failure.
    """
    subprocess.run(["pbcopy"], input=_SENTINEL, text=True)
    left.bring_to_front()
    left.wait_for_timeout(300)
    s.highlight(left, button_sel, hold_ms=800)
    s.move_click(left, button_sel, after_ms=1400)
    text = clipboard()
    for _ in range(10):
        if text != _SENTINEL:
            break
        left.wait_for_timeout(300)
        text = clipboard()
    print(f"{label} copied: {len(text)} chars")
    if text == _SENTINEL:
        raise RuntimeError(f"{label}: copy button never wrote the clipboard")
    if len(text) != expected_chars:
        raise RuntimeError(
            f"{label}: clipboard holds {len(text)} chars, expected "
            f"{expected_chars} — is the deployed page current?")
    return text
