"""Pre-commit / pre-upload privacy sweep for recorded clips.

Exists because two committed clips leaked the account's ChatGPT chat
titles. `inputs/clips/{ar,ur}/copypaste-chatgpt.mp4` open the ChatGPT
sidebar as an on-camera beat, and by the time those takes were shot the
Recents list was populated — seven real conversation titles, legible,
in a public repo. The EN clip was clean only because it was recorded when
that list happened to be empty. Nothing in the pipeline noticed.

Two lessons shaped this module:

* **Sampling misses transients.** A 1-in-5-frames pass over the same
  clips found nothing. So this reads EVERY frame.
* **A coarse whole-frame hash misses small regions.** A 16x16 average
  hash cannot see a 250px-wide sidebar appear in a 1376px frame. So
  change detection is per-block on a 160x120 grid, which is what surfaces
  a panel, dropdown, or popup opening.

This flags *candidate* frames for a human to look at. It does not read
text and does not decide what is sensitive — that judgement is the
author's, and identity content (their own name, handle, avatar) is
usually intended.
"""

import shutil
import subprocess
import tempfile
from pathlib import Path

GRID = (160, 120)
BLOCK = 8
# mean-luma delta within one block that counts as "something changed here"
BLOCK_THRESH = 18


def _blocks(im):
    from PIL import Image
    g = im.convert("L").resize(GRID, Image.BILINEAR)
    px = g.load()
    out = []
    for by in range(0, GRID[1], BLOCK):
        for bx in range(0, GRID[0], BLOCK):
            s = 0
            for y in range(by, by + BLOCK):
                for x in range(bx, bx + BLOCK):
                    s += px[x, y]
            out.append(s / (BLOCK * BLOCK))
    return out


def frame_rate(video: Path) -> float:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0",
         "-show_entries", "stream=r_frame_rate", "-of", "csv=p=0", str(video)],
        capture_output=True, text=True, check=True).stdout.strip()
    num, den = (out.split("/") + ["1"])[:2]
    return float(num) / float(den)


def distinct_frames(video: Path, workdir: Path | None = None):
    """Every frame of `video`, reduced to the ones where some region
    changed. Returns [(frame_index, path, seconds)] — review all of them.
    """
    from PIL import Image
    tmp = workdir or Path(tempfile.mkdtemp(prefix="privacy-"))
    raw = tmp / "raw"
    if raw.exists():
        shutil.rmtree(raw)
    raw.mkdir(parents=True)
    subprocess.run(["ffmpeg", "-v", "error", "-i", str(video),
                    str(raw / "f%05d.png")], check=True)
    rate = frame_rate(video)
    kept, prev = [], None
    for i, f in enumerate(sorted(raw.glob("*.png"))):
        b = _blocks(Image.open(f))
        if prev is None or max(abs(x - y) for x, y in zip(b, prev)) >= BLOCK_THRESH:
            kept.append((i, f, i / rate))
            prev = b
    return kept


def contact_sheet(kept, out_png: Path, cols: int = 5, cell_w: int = 420):
    """One grid of every distinct frame, timestamped, for eyeballing."""
    from PIL import Image, ImageDraw
    if not kept:
        return None
    ims = []
    for _, f, t in kept:
        im = Image.open(f).convert("RGB")
        w, h = im.size
        sc = cell_w / w
        im = im.resize((int(w * sc), int(h * sc)))
        d = ImageDraw.Draw(im)
        d.rectangle([0, 0, 60, 14], fill="black")
        d.text((2, 2), f"{t:.1f}s", fill="yellow")
        ims.append(im)
    W, H = ims[0].size
    rows = (len(ims) + cols - 1) // cols
    sheet = Image.new("RGB", (W * cols, H * rows), "#111")
    for k, im in enumerate(ims):
        sheet.paste(im, ((k % cols) * W, (k // cols) * H))
    out_png.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out_png)
    return out_png


# What a reviewer is looking for. Deliberately a checklist for a human,
# not a classifier: the failure was never detection, it was nobody looking.
CHECKLIST = (
    "history / recents lists WITH ENTRIES (the one that actually leaked)",
    "search boxes or autocomplete dropdowns",
    "conversation or document titles",
    "email addresses, account-chooser contents",
    "notification popups or unread badges",
    "browser tab titles, bookmark bars",
    "anything on screen that is not the demo content",
)

# Tracked separately: usually intended, since the author is named on the
# piece — but inventoried so it is their call rather than an assumption.
IDENTITY_CHECKLIST = (
    "the author's name, handle, or avatar",
    "greetings containing their name",
    "plan/tier badges tied to their account",
)
