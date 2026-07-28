"""Exact-timeline .srt generation.

Cues come from the SAME compute_timeline() as video assembly, so captions
match the audio to the centisecond. Spoken spell-outs are mapped back to
readable text via the language's spellouts table, and for RTL languages
embedded LTR runs (URLs, brand names) are wrapped in U+200E LEFT-TO-RIGHT
MARKs so players don't misplace surrounding punctuation.

The long intro VO is split into sentence cues proportional to character
count, exactly as the EN seed did.
"""

import re
from pathlib import Path

from .assemble import compute_timeline
from .config import LanguageConfig, OUT_DIR
from .timing import INTRO_LEAD

LRM = "‎"
# A run of characters that renders left-to-right inside an RTL sentence:
# latin words, digits, and the URL/domain punctuation that binds them.
_LTR_RUN = re.compile(r"[A-Za-z0-9][A-Za-z0-9./:@_\-]*")


def readable(text: str, cfg: LanguageConfig) -> str:
    for spoken, written in cfg.spellouts:
        text = text.replace(spoken, written)
    return text


def bidi_wrap(text: str, cfg: LanguageConfig) -> str:
    """Wrap LTR runs with LRM marks when the language is RTL."""
    if cfg.direction != "rtl":
        return text
    return _LTR_RUN.sub(lambda m: f"{LRM}{m.group(0)}{LRM}", text)


def caption_text(text: str, cfg: LanguageConfig) -> str:
    return bidi_wrap(readable(text, cfg), cfg)


def fmt_srt_time(s: float) -> str:
    ms = int(round(s * 1000))
    return (f"{ms // 3600000:02d}:{ms % 3600000 // 60000:02d}:"
            f"{ms % 60000 // 1000:02d},{ms % 1000:03d}")


def split_intro(text: str, start: float, dur: float) -> list[tuple[float, float, str]]:
    """Split a long VO into sentence cues proportional to char count."""
    sents = re.split(r"(?<=[.!?؟]) +", text)
    tot = sum(len(x) for x in sents)
    cues, t = [], start
    for sent in sents:
        d = dur * len(sent) / tot
        cues.append((t, t + d, sent))
        t += d
    return cues


def build_srt(cfg: LanguageConfig, video: str) -> Path:
    tl, _ = compute_timeline(cfg, video)

    cues: list[tuple[float, float, str]] = []
    intro_text = caption_text(tl.intro_cue.text, cfg)
    cues.extend(split_intro(intro_text, INTRO_LEAD, tl.intro_cue.dur))
    for c in tl.segments:
        cues.append((c.start, c.end, caption_text(c.text, cfg)))
    cues.append((tl.outro_cue.start, tl.outro_cue.end,
                 caption_text(tl.outro_cue.text, cfg)))

    videos_dir = OUT_DIR / "videos" / cfg.lang
    videos_dir.mkdir(parents=True, exist_ok=True)
    srt = videos_dir / f"youtube-{video}.srt"
    with open(srt, "w", encoding="utf-8") as f:
        for i, (a, b, tx) in enumerate(cues, 1):
            f.write(f"{i}\n{fmt_srt_time(a)} --> {fmt_srt_time(b)}\n{tx}\n\n")
    print(f"wrote {srt} ({len(cues)} cues, ends {fmt_srt_time(cues[-1][1])})")
    return srt
