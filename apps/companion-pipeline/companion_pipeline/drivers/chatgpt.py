"""Split-screen clip: copy the prompt from the prompt page (left half),
paste into ChatGPT custom instructions (right half). Both halves are
CDP-screencast simultaneously and composited side-by-side.

Beats: URL card -> post loads -> Copy prompt || "Now open ChatGPT" card ->
ChatGPT -> Personalization -> paste -> Save -> hold on the green
"Custom instructions updated" toast.

Ported from the EN seed. UI selectors target the EN ChatGPT interface;
the recordings plan phase parameterizes per-language UI routes/strings.
"""

import time

from ..config import LanguageConfig
from ..recorder import Session
from .common import (OVERLAY_JS, OVERLAY_OFF_JS, copy_block,
                     open_article)

# Hide the conversation history before a single frame can show it.
#
# This is not belt-and-braces: the ar and ur takes DID film it. The sidebar
# opens as an on-camera beat, and by the time those takes were shot the
# Recents list was populated — real conversation titles, legible, for
# several seconds. The clips had to be destroyed and purged from history.
# The EN clip escaped only because it was recorded while that list happened
# to be empty, which is luck, not a control.
#
# Same shape as the Gemini driver's REDACT_JS: a MutationObserver, because
# the list mounts asynchronously and re-mounts on navigation, so a one-shot
# hide loses the race. `visibility:hidden` rather than removal — the layout
# must not shift on camera.
SIDEBAR_REDACT_JS = """() => {
  if (window.__jbHistRedact) return;
  const hide = () => {
    for (const el of document.querySelectorAll('a[href^="/c/"]')) {
      el.style.visibility = 'hidden';          // each conversation link
    }
    for (const el of document.querySelectorAll('h2,div,span')) {
      const t = (el.textContent || '').trim();
      // the section heading itself, matched loosely so it survives
      // localization; guarded by length so it can't match a whole pane
      if (t.length < 24 && /^(Recents|Recent)\\b/i.test(t)) {
        let n = el;
        for (let i = 0; i < 2 && n.parentElement; i++) n = n.parentElement;
        n.style.visibility = 'hidden';
      }
    }
  };
  window.__jbHistRedact = new MutationObserver(hide);
  window.__jbHistRedact.observe(document.body, {childList: true, subtree: true});
  hide();
}"""


def open_account_menu(s, page):
    """Open the account menu, tolerating both sidebar states.

    `open-sidebar-button` no longer exists — today's UI ships
    `close-sidebar-button` when the rail is open, and a
    `stage-slideover-sidebar` overlay that intercepts clicks aimed at
    elements beneath it. The account chip is reachable directly via
    `accounts-profile-button` in either state, so go straight there rather
    than choreographing the sidebar open first.
    """
    chip = "[data-testid='accounts-profile-button']"
    if not page.locator(chip).count():
        raise RuntimeError(
            "TAKE ABORT: no accounts-profile-button on the ChatGPT page. "
            "The account-menu route has moved again — re-rec the selectors "
            "before shooting, don't improvise mid-take.")
    s.move_click(page, chip, after_ms=1400)


def ci_field(cfg):
    """Custom-instructions textarea, by localized placeholder substring."""
    return ("textarea[placeholder*="
            f"'{cfg.chatgpt_ui['ci_placeholder_substr']}']")


def visible_save(page, cfg):
    label = cfg.chatgpt_ui["save"]
    saves = page.evaluate("""(label) =>
      [...document.querySelectorAll('button')]
        .filter(b => (b.textContent||'').trim() === label)
        .map(b => { const x = b.getBoundingClientRect();
          return {x: x.x + x.width/2, y: x.y + x.height/2,
                  w: x.width, h: x.height}; })""", label)
    vis = [b for b in saves if b["w"] > 0 and b["h"] > 0 and b["y"] > 0]
    return vis[0] if vis else None


def record(cfg: LanguageConfig) -> None:
    name = f"copypaste-chatgpt-{cfg.lang}"
    CI_FIELD = ci_field(cfg)
    with Session() as s:
        # Each half needs its OWN window: both are screencast at once, and a
        # background tab renders at its window's size, not its viewport.
        # Identical viewports — the composite depends on every captured
        # frame having the same geometry.
        left = s.new_window("about:blank", left=0)
        right = s.new_window("https://chatgpt.com/", left=680)

        # ---- off-camera reset: custom-instructions field must be empty ---
        right.goto("https://chatgpt.com/#settings/Personalization")
        right.wait_for_timeout(1500)
        right.reload()
        right.wait_for_timeout(4000)
        ta = right.locator(CI_FIELD)
        for _ in range(15):
            if ta.count():
                break
            right.wait_for_timeout(700)
        assert ta.count(), "cannot open Personalization for reset"
        last, stable = None, 0
        for _ in range(30):
            v = ta.first.input_value()
            stable = stable + 1 if v == last else 0
            last = v
            if stable >= 4:
                break
            right.wait_for_timeout(500)
        if last:
            ta.first.click()
            right.keyboard.press("Meta+a")
            right.keyboard.press("Delete")
            right.wait_for_timeout(1000)
            sv = visible_save(right, cfg)
            assert sv, "no Save while clearing"
            right.mouse.click(sv["x"], sv["y"])
            right.wait_for_timeout(2000)
            right.reload()
            right.wait_for_timeout(4000)
            assert right.locator(CI_FIELD).first.input_value() == "", \
                "field not empty after reset"
        right.goto("https://chatgpt.com/")
        right.set_viewport_size({"width": 657, "height": 765})
        right.wait_for_timeout(2500)
        # Arm the history redaction BEFORE the first frame is captured, and
        # assert it took — a privacy control that fails open is not a
        # control. This is the reset step, off camera, so aborting here
        # costs nothing; discovering it in the footage costs the take.
        right.evaluate(SIDEBAR_REDACT_JS)
        right.wait_for_timeout(600)
        assert right.evaluate("() => !!window.__jbHistRedact"), \
            "history redaction did not arm — refusing to roll"
        right.evaluate(OVERLAY_JS, ["", None])  # dark cover from the start
        left.goto("about:blank")
        left.set_viewport_size({"width": 657, "height": 765})
        left.wait_for_timeout(400)

        # ---- roll --------------------------------------------------------
        s.start_dual(left, right, name)
        t0 = time.time()
        left.bring_to_front()  # left must be its window's active tab

        # LEFT: short link -> EN article -> language link, all on camera
        open_article(s, left, cfg)
        copy_sel = f"button:has-text('{cfg.article_copy_button_label}')"
        btn = left.locator(copy_sel).first     # block 0 = the full prompt
        btn.scroll_into_view_if_needed()
        left.evaluate("window.scrollBy(0,-140)")
        left.wait_for_timeout(1200)

        # LEFT: copy (tab must be focused for the clipboard write to land)
        clip = copy_block(s, left, copy_sel, cfg.prompt_chars, "prompt")
        print(f"copied at {time.time()-t0:.1f}s")

        # RIGHT card: open ChatGPT (overlay on the live page)
        right.bring_to_front()
        right.evaluate(OVERLAY_JS, [cfg.card_open_line, "ChatGPT"])
        right.wait_for_timeout(2600)
        right.evaluate(OVERLAY_OFF_JS)
        right.wait_for_timeout(1200)
        s.ensure_cursor(right)

        # RIGHT: account menu -> Personalization. Re-arm first: the card
        # overlay and any navigation since the reset can drop the observer.
        right.evaluate(SIDEBAR_REDACT_JS)
        open_account_menu(s, right)
        s.move_click(right, f"text={cfg.chatgpt_ui['personalization']}", after_ms=2200)

        # scroll to the Custom instructions field
        ci = right.locator(CI_FIELD).first
        ci.scroll_into_view_if_needed()
        right.wait_for_timeout(800)
        s.ensure_cursor(right)
        s.highlight(right, CI_FIELD, hold_ms=900)
        s.move_click(right, CI_FIELD, after_ms=600)

        # paste EXACTLY what the Copy button put on the clipboard
        right.keyboard.insert_text(clip)
        right.wait_for_timeout(1600)
        print(f"pasted at {time.time()-t0:.1f}s")

        # Save: recompute coordinates at click time (layout settles)
        right.wait_for_timeout(900)
        sv = visible_save(right, cfg)
        assert sv, "no visible Save button after paste"
        right.evaluate("([x,y]) => window.__jbCursorTo(x,y)",
                       [sv["x"], sv["y"]])
        right.wait_for_timeout(650)
        sv = visible_save(right, cfg) or sv
        right.evaluate("([x,y]) => window.__jbClickPulse(x,y)",
                       [sv["x"], sv["y"]])
        right.wait_for_timeout(250)
        right.mouse.click(sv["x"], sv["y"])

        # end on the green confirmation toast, held long enough to read
        right.locator(f"text={cfg.chatgpt_ui['toast_substr']}").first.wait_for(
            state="visible", timeout=10000)
        print(f"toast at {time.time()-t0:.1f}s")
        right.wait_for_timeout(3000)
        s.stop_dual()

        # ---- verify persistence (off camera) -----------------------------
        right.goto("https://chatgpt.com/#settings/Personalization")
        right.wait_for_timeout(1500)
        right.reload()
        right.wait_for_timeout(4500)
        v = right.locator(CI_FIELD)
        for _ in range(15):
            if v.count():
                break
            right.wait_for_timeout(700)
        n = len(v.first.input_value() or "") if v.count() else -1
        print("persisted custom-instruction chars:", n)
        assert n == cfg.prompt_chars, "prompt did not persist"
