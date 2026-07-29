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
from .common import CARD_JS, OVERLAY_JS, OVERLAY_OFF_JS, copy_from_prompt_page

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
        right.evaluate(OVERLAY_JS, ["", None])  # dark cover from the start
        left.goto("about:blank")
        left.set_viewport_size({"width": 657, "height": 765})
        left.wait_for_timeout(400)

        # ---- roll --------------------------------------------------------
        s.start_dual(left, right, name)
        t0 = time.time()
        left.bring_to_front()  # left must be its window's active tab

        # LEFT card: go to the short link
        left.evaluate(CARD_JS, [cfg.card_goto_line, cfg.prompt_url_display])
        left.wait_for_timeout(3200)
        left.goto(cfg.prompt_url)
        left.set_viewport_size({"width": 657, "height": 765})
        left.wait_for_timeout(2800)
        s.ensure_cursor(left)
        copy_sel = f"button:has-text('{cfg.copy_button_label}')"
        btn = left.locator(copy_sel).first
        btn.scroll_into_view_if_needed()
        left.evaluate("window.scrollBy(0,-140)")
        left.wait_for_timeout(800)

        # LEFT: copy (tab must be focused for the clipboard write to land)
        clip = copy_from_prompt_page(
            s, left, copy_sel, cfg.prompt_chars, "prompt")
        print(f"copied at {time.time()-t0:.1f}s")

        # RIGHT card: open ChatGPT (overlay on the live page)
        right.bring_to_front()
        right.evaluate(OVERLAY_JS, [cfg.card_open_line, "ChatGPT"])
        right.wait_for_timeout(2600)
        right.evaluate(OVERLAY_OFF_JS)
        right.wait_for_timeout(1200)
        s.ensure_cursor(right)

        # RIGHT: sidebar -> account -> Personalization
        s.move_click(right, "[data-testid='open-sidebar-button']",
                     after_ms=1100)
        s.move_click(right, f"text={cfg.account_label}", after_ms=1200)
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
        # close the take's windows before asserting, so a failed take still
        # leaves the rig as it found it
        for p in (left, right):
            try:
                p.close()
            except Exception:
                pass
        assert n == cfg.prompt_chars, "prompt did not persist"
