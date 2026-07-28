"""Split-screen clip (Claude variant): copy the prompt from the prompt page
(left half), paste into Claude's "Instructions for Claude" field (right
half). Same beats as the ChatGPT clip: URL card -> Copy prompt || "Now open
Claude" card -> account menu -> Settings -> paste -> Save changes -> hold
on saved state.

Ported from the EN seed. UI selectors target the EN Claude interface;
the recordings plan phase parameterizes per-language UI routes/strings.
"""

import time

from ..config import LanguageConfig
from ..recorder import Session
from .common import (CARD_JS, OVERLAY_JS, OVERLAY_OFF_JS,
                     copy_from_prompt_page, stable_value)


def record(cfg: LanguageConfig) -> None:
    name = f"copypaste-claude-{cfg.lang}"
    with Session() as s:
        left = next(p for p in s.ctx.pages if "iaser.ai" in p.url)
        right = next(p for p in s.ctx.pages if "claude.ai" in p.url)
        left.set_viewport_size({"width": 657, "height": 765})
        right.set_viewport_size({"width": 657, "height": 765})

        # ---- off-camera reset: Instructions field must be empty ----------
        right.goto("https://claude.ai/new#settings/general")
        right.wait_for_timeout(1500)
        right.reload()
        right.wait_for_timeout(3500)
        ta = right.locator("textarea").first
        ta.wait_for(state="visible", timeout=15000)
        cur = stable_value(right, ta)
        print("field before reset:", len(cur or ""))
        if (cur or "").strip() not in ("", "."):
            # the server no-ops empty saves; a lone "." persists and is
            # invisible at video scale (the take select-alls before pasting)
            ta.click()
            right.keyboard.press("Meta+a")
            right.keyboard.insert_text(".")
            right.wait_for_timeout(1000)
            sv = right.locator("button:has-text('Save changes')")
            for _ in range(10):
                if sv.count():
                    break
                right.wait_for_timeout(500)
            assert sv.count(), "no Save changes while resetting"
            sv.first.focus()
            right.wait_for_timeout(300)
            right.keyboard.press("Enter")
            gone_r = False
            for _ in range(10):
                if not sv.count():
                    gone_r = True
                    break
                right.wait_for_timeout(500)
            assert gone_r, "reset save did not register"
            # reads can lag saves by many seconds — retry the reload check
            ok = False
            for _ in range(8):
                right.reload()
                right.wait_for_timeout(3500)
                chk = right.locator("textarea").first
                chk.wait_for(state="visible", timeout=15000)
                if (stable_value(right, chk) or "").strip() in ("", "."):
                    ok = True
                    break
            assert ok, "field not effectively empty after reset"

        # dismiss any promo tooltip, park on clean home under the dark cover
        right.goto("https://claude.ai/new")
        right.wait_for_timeout(2500)
        for sel in ["[aria-label='Dismiss']", "[aria-label='Close']"]:
            loc = right.locator(f"div:has-text('Better together') {sel}")
            if loc.count():
                loc.last.click()
                break
        right.evaluate(OVERLAY_JS, ["", None])
        left.goto("about:blank")
        left.set_viewport_size({"width": 657, "height": 765})
        left.wait_for_timeout(400)

        # ---- roll --------------------------------------------------------
        s.start_dual(left, right, name)
        t0 = time.time()
        left.bring_to_front()

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

        # LEFT: copy
        clip = copy_from_prompt_page(
            s, left, copy_sel, cfg.prompt_chars, "prompt")
        print(f"copied at {time.time()-t0:.1f}s")

        # RIGHT card: open Claude (overlay — no navigation)
        right.bring_to_front()
        right.evaluate(OVERLAY_JS, [cfg.card_open_line, "Claude"])
        right.wait_for_timeout(2600)
        right.evaluate(OVERLAY_OFF_JS)
        right.wait_for_timeout(1200)
        s.ensure_cursor(right)

        # RIGHT: the narrow-layout sidebar is a hover "peek" panel — hover
        # the expander (no click), glide down INSIDE the panel, click chip.
        right.set_viewport_size({"width": 657, "height": 765})
        right.wait_for_timeout(600)

        def glide_mouse(x, y, dwell=150, steps=4):
            right.evaluate("([x,y]) => window.__jbCursorTo(x,y)", [x, y])
            right.mouse.move(x, y, steps=steps)
            right.wait_for_timeout(dwell)

        glide_mouse(24, 24, dwell=1100)  # peek panel slides out on hover
        for y in (140, 260, 380, 460):
            glide_mouse(90, y, dwell=160)
        chip = right.locator("[data-testid='user-menu-button']").first
        box = chip.bounding_box()
        assert box, "account chip not visible in peek panel"
        cx = box["x"] + box["width"] / 2
        cy = box["y"] + box["height"] / 2
        glide_mouse(cx, cy, dwell=600)
        right.evaluate("([x,y]) => window.__jbClickPulse(x,y)", [cx, cy])
        right.wait_for_timeout(250)
        right.mouse.click(cx, cy)
        right.wait_for_timeout(1300)
        assert right.locator("text=Settings").first.is_visible(), \
            "account menu did not open"
        s.move_click(right, "text=Settings", after_ms=2400)

        # the Instructions for Claude field
        ta = right.locator("textarea").first
        ta.wait_for(state="visible", timeout=15000)
        ta.scroll_into_view_if_needed()
        right.wait_for_timeout(800)
        s.ensure_cursor(right)
        s.highlight(right, "textarea", hold_ms=900)
        s.move_click(right, "textarea", after_ms=600)

        # paste EXACTLY what the Copy button put on the clipboard
        # (select-all first so any whitespace placeholder is replaced)
        right.keyboard.press("Meta+a")
        right.keyboard.insert_text(clip)
        right.wait_for_timeout(1600)
        print(f"pasted at {time.time()-t0:.1f}s")

        # Save changes: appears once the field is edited; coords at click
        right.wait_for_timeout(900)
        save = right.locator("button:has-text('Save changes')")
        for _ in range(10):
            if save.count():
                break
            right.wait_for_timeout(500)
        assert save.count(), "no Save changes button after paste"
        box = save.first.bounding_box()
        x, y = box["x"] + box["width"] / 2, box["y"] + box["height"] / 2
        right.evaluate("([x,y]) => window.__jbCursorTo(x,y)", [x, y])
        right.wait_for_timeout(650)
        box = save.first.bounding_box() or box
        x, y = box["x"] + box["width"] / 2, box["y"] + box["height"] / 2
        right.evaluate("([x,y]) => window.__jbClickPulse(x,y)", [x, y])
        right.wait_for_timeout(250)
        save.first.click()
        # confirmation = the Save/Discard row disappears; pointer clicks
        # sometimes silently no-op here, so fall back to focus+Enter
        gone = False
        for i in range(16):
            if not save.count():
                gone = True
                break
            if i == 3:
                save.first.focus()
                right.wait_for_timeout(200)
                right.keyboard.press("Enter")
            right.wait_for_timeout(500)
        assert gone, "Save changes did not register"
        print(f"saved at {time.time()-t0:.1f}s")

        # hold on the saved state; glide the cursor away in visible steps so
        # the compositor keeps producing frames that show the post-save UI
        for gx, gy in ((x, y - 90), (x + 130, y - 160), (x + 260, y - 200)):
            right.evaluate("([x,y]) => window.__jbCursorTo(x,y)", [gx, gy])
            right.wait_for_timeout(700)
        right.wait_for_timeout(1800)
        s.stop_dual()

        # ---- verify persistence (off camera) -----------------------------
        right.goto("https://claude.ai/new#settings/general")
        right.wait_for_timeout(1500)
        right.reload()
        right.wait_for_timeout(3500)
        v = right.locator("textarea").first
        v.wait_for(state="visible", timeout=15000)
        n = len(stable_value(right, v) or "")
        print("persisted instruction chars:", n)
        assert n == cfg.prompt_chars, "prompt did not persist"
