"""Split-screen clip (Gemini variant): copy Part 1 and Part 2 from the
prompt page, paste each as a separate Gemini instruction entry (Gemini's
entry rewriter rejects the full prompt — error 13 — hence two parts).

Beats: URL card -> scroll to Gemini section -> Copy Part 1 || "Now open
Gemini" card -> saved-info -> Add -> paste -> Submit || back left: Copy
Part 2 || right: Add -> paste -> Submit -> hold.

Privacy: narrow viewport keeps the sidebar as an icon rail (no chat
titles); a watcher hides the location row in the settings menu before it
can render a frame.

Gemini quirks (seed-proven): components ignore raw coordinate clicks —
use trusted locator clicks with the cursor glide done separately; the
window must be visible (not hidden) or events silently fail.
"""

import time

from ..config import LanguageConfig
from ..recorder import Session
from .common import CARD_JS, OVERLAY_JS, OVERLAY_OFF_JS, clipboard

# hide the location rows of the settings menu the moment they mount
REDACT_JS = """() => {
  if (window.__jbRedact) return;
  const hide = () => {
    for (const el of document.querySelectorAll('a,div,li,span,button')) {
      const t = el.textContent || '';
      if (((t.includes('Update location') || t.includes('Based on your places'))
          && t.length < 120)
          || (t.trim().startsWith('Notebooks') && t.length < 220)) {
        let n = el;
        for (let i = 0; i < 3 && n.parentElement; i++) n = n.parentElement;
        n.style.visibility = 'hidden';
      }
    }
  };
  window.__jbRedact = new MutationObserver(hide);
  window.__jbRedact.observe(document.body, {childList: true, subtree: true});
  hide();
}"""


def trusted_click(s, page, sel, after_ms=1000):
    """Cursor glide + pulse for the camera, trusted locator click for the
    app (Gemini's components ignore raw coordinate clicks)."""
    loc = page.locator(sel).first
    box = loc.bounding_box()
    if box:
        x, y = box["x"] + box["width"] / 2, box["y"] + box["height"] / 2
        page.evaluate("([x,y]) => window.__jbCursorTo(x,y)", [x, y])
        page.wait_for_timeout(650)
        page.evaluate("([x,y]) => window.__jbClickPulse(x,y)", [x, y])
        page.wait_for_timeout(250)
    loc.click()
    page.wait_for_timeout(after_ms)


def ensure_visible(s, right, cfg):
    """The app sometimes hides the whole saved-info panel; recover with a
    foregrounded reload. Locale-robust: the Add button is found by its
    stable class, not its (localized) label."""
    for attempt in range(3):
        ok = right.evaluate("""() => {
          const b = document.querySelector('button.create-memory-button');
          return !!(b && getComputedStyle(b).visibility === 'visible');
        }""")
        print(f"  saved-info visible: {ok} (attempt {attempt})")
        if ok:
            return
        right.bring_to_front()
        right.wait_for_timeout(400)
        right.reload()
        right.wait_for_timeout(3500)
        s.ensure_cursor(right)
    raise RuntimeError("saved-info page stuck hidden")


def paste_entry(s, right, cfg, text, label):
    """Add -> paste -> Submit one instruction entry (localized UI).

    TAKE-QUALITY GUARD (verification lessons): after Submit the dialog
    must close on camera. Gemini sometimes shows a retryable error dialog
    even when the entry saved — that ruins the take visually, so we ABORT
    loudly rather than fight it mid-recording; the operator cleans up and
    retakes. Dialog buttons are selected by localized TEXT (config
    [recording.gemini_ui]) because button order varies per dialog type.
    """
    ensure_visible(s, right, cfg)
    trusted_click(s, right, "button.create-memory-button", after_ms=1200)
    submit_sel = (".cdk-overlay-container "
                  f"button:has-text('{cfg.gemini_ui['submit']}')")
    right.locator(submit_sel).first.wait_for(state="visible", timeout=10000)
    sel = ("textarea" if right.locator("textarea").count()
           else "[contenteditable='true']")
    s.highlight(right, sel, hold_ms=700)
    right.locator(sel).last.click()
    right.wait_for_timeout(300)
    right.keyboard.insert_text(text)
    right.wait_for_timeout(1400)
    trusted_click(s, right, submit_sel, after_ms=1000)
    try:
        right.wait_for_function(
            "() => !document.querySelector('.cdk-overlay-backdrop')",
            timeout=25000)
    except Exception:
        # capture what the dialog actually said — the abort is otherwise
        # blind, and the same guard fires for genuine and false errors
        try:
            dlg = right.evaluate(
                """() => [...document.querySelectorAll(
                     '.cdk-overlay-container mat-dialog-container, '
                     + '.cdk-overlay-container [role=dialog]')]
                     .map(n => (n.innerText||'').trim()).join(' | ')""")
        except Exception:
            dlg = "<could not read dialog>"
        raise RuntimeError(
            f"TAKE ABORT ({label}): submit dialog did not close on camera "
            "(likely the false-error dialog). Stop recording, verify the "
            "entry list (the entry may HAVE saved), clean up, retake.\n"
            f"DIALOG TEXT: {dlg[:600]}")
    right.wait_for_timeout(1500)
    print(f"{label} submitted, dialog closed")


def _copy_part(s, left, copy_btns, idx: int, cfg: LanguageConfig,
               label: str) -> str:
    b = copy_btns.nth(idx)
    b.scroll_into_view_if_needed()
    left.evaluate("window.scrollBy(0,-120)")
    left.wait_for_timeout(500)
    box = b.bounding_box()
    left.evaluate("([x,y]) => window.__jbCursorTo(x,y)",
                  [box["x"] + box["width"]/2, box["y"] + box["height"]/2])
    left.wait_for_timeout(700)
    left.evaluate("([x,y]) => window.__jbClickPulse(x,y)",
                  [box["x"] + box["width"]/2, box["y"] + box["height"]/2])
    left.wait_for_timeout(250)
    b.click()
    left.wait_for_timeout(1200)
    part = clipboard()
    print(f"{label} copied: {len(part)} chars")
    if not (cfg.gemini_part_min < len(part) < cfg.gemini_part_max):
        raise RuntimeError(
            f"{label}: clipboard holds {len(part)} chars, expected "
            f"{cfg.gemini_part_min}-{cfg.gemini_part_max}")
    return part


def record(cfg: LanguageConfig) -> None:
    name = f"copypaste-gemini-{cfg.lang}"
    with Session() as s:
        # Own window per half — both are screencast at once, and a
        # background tab renders at its window's size, not its viewport.
        # Gemini additionally needs a genuinely visible window, so the two
        # are placed side by side rather than stacked.
        left = s.new_window("about:blank", width=1000, left=0)
        right = s.new_window(f"https://gemini.google.com/app?hl={cfg.lang}",
                             width=1000, left=1010)

        # ---- off-camera prep: park directly on the instructions page -----
        # (viewport BEFORE navigation: the page decides visible-vs-hidden
        # at load time and never re-evaluates on resize)
        right.set_viewport_size({"width": 1000, "height": 765})
        right.goto("https://gemini.google.com/saved-info"
                   f"?hl={cfg.lang}")
        right.wait_for_timeout(3500)
        assert right.evaluate("""() => {
          const b = document.querySelector('button.create-memory-button');
          return b && getComputedStyle(b).visibility === 'visible';
        }"""), "saved-info page not visible at this viewport"
        right.evaluate(OVERLAY_JS, ["", None])
        left.goto("about:blank")
        left.set_viewport_size({"width": 1000, "height": 765})
        left.wait_for_timeout(400)

        # ---- roll --------------------------------------------------------
        s.start_dual(left, right, name)
        t0 = time.time()
        left.bring_to_front()

        left.evaluate(CARD_JS, [cfg.card_goto_line, cfg.prompt_url_display])
        left.wait_for_timeout(3200)
        left.goto(cfg.prompt_url)
        left.set_viewport_size({"width": 1000, "height": 765})
        left.wait_for_timeout(2800)
        s.ensure_cursor(left)

        # scroll to the Gemini section's Part 1 block (block #2 on page)
        blocks = left.locator("pre")
        n_blocks = blocks.count()
        print("code blocks on page:", n_blocks)
        assert n_blocks >= 3, "part blocks not on the deployed page yet"
        blocks.nth(1).scroll_into_view_if_needed()
        left.evaluate("window.scrollBy(0,-160)")
        left.wait_for_timeout(900)

        copy_btns = left.locator(
            f"pre button, button:has-text('{cfg.copy_button_label}')")
        print("copy buttons:", copy_btns.count())

        # LEFT: copy Part 1
        left.bring_to_front()
        left.wait_for_timeout(300)
        part1 = _copy_part(s, left, copy_btns, 1, cfg, "part1")
        print(f"part1 at {time.time()-t0:.1f}s")

        # RIGHT: card + settings path
        right.bring_to_front()
        right.evaluate(OVERLAY_JS, [cfg.card_open_line, "Gemini"])
        right.wait_for_timeout(2600)
        right.evaluate(OVERLAY_OFF_JS)
        right.wait_for_timeout(1000)
        s.ensure_cursor(right)
        right.evaluate(REDACT_JS)
        right.wait_for_timeout(600)

        # first entry
        paste_entry(s, right, cfg, part1, "part1")

        # LEFT: copy Part 2
        left.bring_to_front()
        left.wait_for_timeout(400)
        part2 = _copy_part(s, left, copy_btns, 2, cfg, "part2")
        if part2 == part1:
            raise RuntimeError("part 2 clipboard identical to part 1")

        # RIGHT: second entry
        right.bring_to_front()
        right.wait_for_timeout(400)
        paste_entry(s, right, cfg, part2, "part2")

        # hold on the final state; glide cursor away to keep frames flowing
        for gx, gy in ((420, 420), (520, 300), (560, 220)):
            right.evaluate("([x,y]) => window.__jbCursorTo(x,y)", [gx, gy])
            right.wait_for_timeout(700)
        right.wait_for_timeout(1500)
        s.stop_dual()

        # ---- verify (loosely: Gemini paraphrases entries) ----------------
        right.goto("https://gemini.google.com/saved-info"
                   f"?hl={cfg.lang}")
        right.wait_for_timeout(3500)
        body = right.evaluate("document.body.innerText")
        print("entries mention companion:", "companion" in body)
        for p in (left, right):
            try:
                p.close()
            except Exception:
                pass
