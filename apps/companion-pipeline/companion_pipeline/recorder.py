"""Recording harness: attach Playwright to the CDP Chrome, inject a visible
fake cursor, and capture tab video via CDP Page.startScreencast frames.

Ported from the EN seed. Recording rules that each bit us at least once:
- Each recorded page needs its OWN WINDOW (background tabs render at the
  window's size, not their viewport).
- Set viewport BEFORE goto — some apps decide element visibility at load.
- Gemini needs trusted locator clicks and a visible (un-hidden) window.
- Tail frames freeze at paint-idle — append a real-state screenshot last.
- Purge stale frames between takes (stop_dual does this).

Usage from driver modules:
    from .recorder import Session
    with Session() as s:
        page = s.new_page("https://claude.ai")
        s.start_recording(page, "claude-install")
        s.move_click(page, "selector or (x, y)")
        ...
        s.stop_recording()   # frames -> out/recordings/<name>.mp4
"""

import base64
import os
import subprocess
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

from .config import OUT_DIR

RECORDINGS_DIR = OUT_DIR / "recordings"

# The recording Chrome is identified by a substring of its
# --user-data-dir; override when your profile directory isn't named
# "rec-profile" (see README setup).
REC_PROFILE_MATCH = os.environ.get("COMPANION_REC_PROFILE_MATCH",
                                   "rec-profile")
CDP_URL = os.environ.get("COMPANION_CDP_URL", "http://localhost:9222")


def hide_chrome():
    """Re-hide the recording Chrome (macOS un-hides an app whenever a new
    window appears). Targeted by PID so the user's main Chrome is untouched.
    NOTE: long-hidden windows eventually wedge the renderer — prefer
    visible-but-backgrounded during long sessions."""
    try:
        pid = subprocess.run(
            ["pgrep", "-f", f"user-data-dir=.*{REC_PROFILE_MATCH}"],
            capture_output=True, text=True).stdout.split()
        if pid:
            subprocess.run(
                ["osascript", "-e",
                 f'tell application "System Events" to set visible of '
                 f'(first process whose unix id is {pid[0]}) to false'],
                capture_output=True)
    except Exception:
        pass


CURSOR_JS = """
(() => {
  if (window.__jbCursor) return;
  const c = document.createElement('div');
  c.id = '__jb_cursor';
  c.style.cssText = `position:fixed;z-index:2147483647;width:22px;height:22px;
    pointer-events:none;transition:left .5s cubic-bezier(.25,.6,.3,1),
    top .5s cubic-bezier(.25,.6,.3,1);left:640px;top:400px;`;
  const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
  svg.setAttribute('viewBox', '0 0 24 24');
  svg.setAttribute('width', '22');
  svg.setAttribute('height', '22');
  const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
  path.setAttribute('d', 'M5 3l14 8-6.5 1.5L9 19z');
  path.setAttribute('fill', '#fff');
  path.setAttribute('stroke', '#000');
  path.setAttribute('stroke-width', '1.6');
  path.setAttribute('stroke-linejoin', 'round');
  svg.appendChild(path);
  c.appendChild(svg);
  document.documentElement.appendChild(c);
  window.__jbCursor = c;
  window.__jbCursorTo = (x, y) => { c.style.left = x + 'px'; c.style.top = y + 'px'; };
  window.__jbClickPulse = (x, y) => {
    const p = document.createElement('div');
    p.style.cssText = `position:fixed;z-index:2147483646;left:${x-18}px;top:${y-18}px;
      width:36px;height:36px;border-radius:50%;border:3px solid #4da3ff;
      pointer-events:none;animation:__jbp .45s ease-out forwards;`;
    document.documentElement.appendChild(p);
    setTimeout(() => p.remove(), 500);
  };
  const st = document.createElement('style');
  st.textContent = '@keyframes __jbp{from{transform:scale(.4);opacity:.9}to{transform:scale(1.4);opacity:0}}';
  document.head.appendChild(st);
})();
"""


class Session:
    def __init__(self, cdp_url: str = CDP_URL):
        self._pw = sync_playwright().start()
        self.browser = self._pw.chromium.connect_over_cdp(cdp_url)
        self.ctx = self.browser.contexts[0]
        self._frames = []
        self._rec_name = None
        self._cdp = None
        self._own_pages = []   # windows this Session opened; closed on exit

    # -- lifecycle ---------------------------------------------------------
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()

    def close(self):
        # Take windows MUST be torn down on abort as well as success —
        # every failed take used to strand two visible windows on the
        # operator's desktop, and they accumulated across a session.
        try:
            self.close_take_windows()
        finally:
            try:
                self.browser.close()
            finally:
                self._pw.stop()

    def close_take_windows(self):
        """Close every window this Session opened, ignoring the rig's."""
        while self._own_pages:
            page = self._own_pages.pop()
            try:
                page.close()
            except Exception:
                pass

    # -- pages -------------------------------------------------------------
    def new_page(self, url: str):
        page = self.ctx.new_page()
        page.set_viewport_size({"width": 1280, "height": 800})
        page.goto(url, wait_until="domcontentloaded")
        page.wait_for_timeout(1500)
        self.ensure_cursor(page)
        hide_chrome()
        return page

    def new_window(self, url: str, width: int = 657, height: int = 765,
                   left: int = 0):
        """Open `url` in its OWN top-level window and return the Page.

        Split-screen takes screencast both halves at once, so neither half
        may be a background tab: a backgrounded tab renders at its window's
        size rather than its viewport, and the composite letterboxes it
        (this shipped a visibly shrunken right half once). Reusing the
        rig's existing tabs puts both halves in one window, which cannot
        satisfy that — so each half gets a window here.
        """
        # window.open with explicit geometry — Chrome makes that a real
        # separate window, and Playwright tracks it as a popup. (Raw
        # Target.createTarget also opens a window, but an already-connected
        # Playwright session never attaches to it, so the page is invisible
        # to the driver.)
        opener = self.ctx.pages[0]
        with self.ctx.expect_page(timeout=20000) as info:
            opener.evaluate(
                """([w, h, l]) => window.open('about:blank', '_blank',
                     `width=${w},height=${h},left=${l},top=0`)""",
                [width, height, left])
        page = info.value
        self._own_pages.append(page)

        # viewport BEFORE goto — some apps fix element visibility at load
        page.set_viewport_size({"width": width, "height": height})
        page.goto(url, wait_until="domcontentloaded")
        page.wait_for_timeout(1500)
        self.ensure_cursor(page)
        return page

    def ensure_cursor(self, page):
        page.evaluate(CURSOR_JS)

    # -- recording ---------------------------------------------------------
    def start_recording(self, page, name: str):
        hide_chrome()
        RECORDINGS_DIR.mkdir(parents=True, exist_ok=True)
        self._frames = []
        self._rec_name = name
        self._t0 = time.time()
        self._cdp = self.ctx.new_cdp_session(page)

        def on_frame(params):
            self._frames.append((params["metadata"]["timestamp"],
                                 params["data"]))
            self._cdp.send("Page.screencastFrameAck",
                           {"sessionId": params["sessionId"]})

        self._cdp.on("Page.screencastFrame", on_frame)
        self._cdp.send("Page.startScreencast", {
            "format": "png", "everyNthFrame": 1,
            "maxWidth": 1280, "maxHeight": 800})

    def stop_recording(self, fps: int = 12) -> Path:
        self._cdp.send("Page.stopScreencast")
        time.sleep(0.3)
        name = self._rec_name
        fdir = RECORDINGS_DIR / f"frames-{name}"
        if fdir.exists():
            for old in fdir.glob("f*.png"):
                old.unlink()
        fdir.mkdir(exist_ok=True)
        if not self._frames:
            raise RuntimeError("no frames captured")
        # Resample variable-rate frames onto a fixed-fps timeline.
        t_start = self._frames[0][0]
        t_end = self._frames[-1][0]
        n_out = max(1, int((t_end - t_start) * fps))
        fi = 0
        for i in range(n_out):
            t = t_start + i / fps
            while fi + 1 < len(self._frames) and self._frames[fi + 1][0] <= t:
                fi += 1
            (fdir / f"f{i:05d}.png").write_bytes(
                base64.b64decode(self._frames[fi][1]))
        mp4 = RECORDINGS_DIR / f"{name}.mp4"
        subprocess.run(
            ["ffmpeg", "-y", "-framerate", str(fps),
             "-i", str(fdir / "f%05d.png"),
             "-c:v", "libx264", "-pix_fmt", "yuv420p",
             "-vf", "scale=1280:-2", "-crf", "21", str(mp4)],
            check=True, capture_output=True)
        print(f"wrote {mp4} ({n_out} frames @ {fps}fps, "
              f"{t_end - t_start:.1f}s)")
        return mp4

    # -- dual-tab recording (split view) -----------------------------------
    def start_dual(self, page_a, page_b, name: str):
        """Screencast two tabs at once; composite side-by-side on stop."""
        RECORDINGS_DIR.mkdir(parents=True, exist_ok=True)
        self._rec_name = name
        self._dual = []
        for page in (page_a, page_b):
            frames = []
            cdp = self.ctx.new_cdp_session(page)

            def on_frame(params, _cdp=cdp, _frames=frames):
                _frames.append((params["metadata"]["timestamp"],
                                params["data"]))
                _cdp.send("Page.screencastFrameAck",
                          {"sessionId": params["sessionId"]})

            cdp.on("Page.screencastFrame", on_frame)
            cdp.send("Page.startScreencast", {
                "format": "png", "everyNthFrame": 1,
                "maxWidth": 720, "maxHeight": 820})
            self._dual.append((cdp, frames))

    def stop_dual(self, fps: int = 12) -> Path:
        for cdp, _ in self._dual:
            cdp.send("Page.stopScreencast")
        time.sleep(0.4)
        name = self._rec_name
        sides = []
        t0 = max(fr[0][0] for _, fr in self._dual if fr)
        t1 = max(fr[-1][0] for _, fr in self._dual if fr)
        n_out = max(1, int((t1 - t0) * fps))
        for idx, (_, fr) in enumerate(self._dual):
            fdir = RECORDINGS_DIR / f"frames-{name}-{idx}"
            if fdir.exists():
                for old in fdir.glob("f*.png"):
                    old.unlink()
            fdir.mkdir(exist_ok=True)
            fi = 0
            for i in range(n_out):
                t = t0 + i / fps
                while fi + 1 < len(fr) and fr[fi + 1][0] <= t:
                    fi += 1
                (fdir / f"f{i:05d}.png").write_bytes(
                    base64.b64decode(fr[fi][1]))
            sides.append(fdir)
        # derive the cell geometry from side 0's first frame so different
        # viewport shapes compose cleanly
        from struct import unpack
        first = sorted(sides[0].glob("f*.png"))[0]
        cw, ch = unpack(">II", first.read_bytes()[16:24])
        cw, ch = (cw // 2) * 2, (ch // 2) * 2
        cell = (f"scale={cw}:{ch}:force_original_aspect_ratio=decrease,"
                f"pad={cw}:{ch}:(ow-iw)/2:(oh-ih)/2:color=#0d0d0d")
        mp4 = RECORDINGS_DIR / f"{name}.mp4"
        subprocess.run(
            ["ffmpeg", "-y",
             "-framerate", str(fps), "-i", str(sides[0] / "f%05d.png"),
             "-framerate", str(fps), "-i", str(sides[1] / "f%05d.png"),
             "-filter_complex",
             f"[0:v]{cell}[l];[1:v]{cell}[r];"
             "[l][r]hstack=inputs=2",
             "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "21",
             str(mp4)], check=True, capture_output=True)
        print(f"wrote {mp4} ({n_out} frames @ {fps}fps, {t1 - t0:.1f}s)")
        return mp4

    # -- interaction with visible cursor ----------------------------------
    def _xy(self, page, target):
        if isinstance(target, tuple):
            return target
        box = page.locator(target).first.bounding_box()
        if not box:
            raise RuntimeError(f"no bounding box for {target!r}")
        return (box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)

    def glide(self, page, target, settle_ms: int = 650):
        x, y = self._xy(page, target)
        self.ensure_cursor(page)
        page.evaluate("([x,y]) => window.__jbCursorTo(x,y)", [x, y])
        page.wait_for_timeout(settle_ms)
        return (x, y)

    def highlight(self, page, target, hold_ms: int = 700):
        """Glowing rounded-rect around the target element before acting."""
        if isinstance(target, tuple):
            return
        box = page.locator(target).first.bounding_box()
        if not box:
            return
        page.evaluate(
            """(b) => {
              const h = document.createElement('div');
              h.style.cssText = `position:fixed;z-index:2147483645;pointer-events:none;
                left:${b.x-6}px;top:${b.y-6}px;width:${b.width+12}px;height:${b.height+12}px;
                border:3px solid #ff9f2a;border-radius:10px;
                box-shadow:0 0 0 4000px rgba(0,0,0,.18),0 0 18px 2px #ff9f2a;
                transition:opacity .3s;opacity:0;`;
              document.documentElement.appendChild(h);
              requestAnimationFrame(() => h.style.opacity = '1');
              setTimeout(() => { h.style.opacity = '0';
                                 setTimeout(() => h.remove(), 350); }, 1200);
            }""", box)
        page.wait_for_timeout(hold_ms)

    def move_click(self, page, target, settle_ms: int = 650,
                   after_ms: int = 900, spotlight: bool = True):
        if spotlight:
            self.highlight(page, target)
        x, y = self.glide(page, target, settle_ms)
        page.evaluate("([x,y]) => window.__jbClickPulse(x,y)", [x, y])
        page.wait_for_timeout(250)
        page.mouse.click(x, y)
        page.wait_for_timeout(after_ms)

    def paste_into(self, page, target, text: str, after_ms: int = 900):
        """Click the field, then insert text at once (paste, not typing)."""
        self.move_click(page, target, after_ms=400)
        page.keyboard.insert_text(text)
        page.wait_for_timeout(after_ms)

    def type_into(self, page, target, text: str, delay_ms: int = 28,
                  after_ms: int = 600):
        self.move_click(page, target, after_ms=300)
        page.keyboard.type(text, delay=delay_ms)
        page.wait_for_timeout(after_ms)
