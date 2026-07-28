"""YouTube Studio automation helpers.

CHANNEL SAFETY (spec constraint): uploads go ONLY to the iaser-ai channel,
always Private. The Google login's DEFAULT channel is a personal one — all
Studio navigation is pinned to the channel URL, and preflight_channel()
must pass before any upload action. The full guarded upload flow ships in
the uploads plan phase; this module provides the connection + guard
foundation.
"""

from playwright.sync_api import sync_playwright

CHANNEL_ID = "UCF1yEgoyLfbgTUpeMn2ruqA"  # iaser-ai
STUDIO = f"https://studio.youtube.com/channel/{CHANNEL_ID}"


def connect(cdp_url: str | None = None):
    """Attach to the rec-profile Chrome; return (playwright, page).

    pages[0] over CDP is not stable — callers must verify pg.url before
    acting (seed gotcha).
    """
    from .recorder import CDP_URL
    pw = sync_playwright().start()
    b = pw.chromium.connect_over_cdp(cdp_url or CDP_URL)
    ctx = b.contexts[0]
    pg = ctx.pages[0] if ctx.pages else ctx.new_page()
    return pw, pg


def preflight_channel(pg) -> None:
    """Abort unless Studio is pinned to the iaser-ai channel.

    Navigates to the channel-pinned Studio URL and asserts the channel ID
    is present in the final URL (Studio redirects away if the login lacks
    access; a personal-channel context would land on a different /channel/
    path). Raises on any mismatch — callers must not catch and continue.
    """
    pg.goto(STUDIO, wait_until="domcontentloaded")
    pg.wait_for_timeout(3000)
    if CHANNEL_ID not in pg.url:
        raise RuntimeError(
            f"channel preflight FAILED: Studio landed on {pg.url!r}, "
            f"expected channel {CHANNEL_ID} (iaser-ai). Aborting — "
            "no upload actions may run against this session.")
    print(f"channel preflight OK: {pg.url}")
