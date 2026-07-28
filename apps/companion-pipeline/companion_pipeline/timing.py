"""Shared narration-timeline planner.

Video assembly (assemble.py) and caption generation (captions.py) both build
their timelines from plan_timeline(), so audio placement and SRT cues can
never drift apart. The rules are ported verbatim from the EN seed
(build_video.py), where each one was learned from a shipped bug:

1. Segment starts are clamped non-overlapping:
   start = max(intro_s + offset, last_end + SEG_GAP).
2. Outro VO starts at max(intro_s + clip_dur + CLIP_PAD, last_end + OUTRO_GAP).
3. The outro card stretches so the outro VO always finishes:
   outro_len = max(MIN_OUTRO, outro_start + outro_dur + OUTRO_TAIL
                   - (intro_s + clip_dur)).
"""

from dataclasses import dataclass, field

INTRO_LEAD = 0.4     # intro VO begins this far into the intro card
MIN_INTRO = 6.0      # intro card never shorter than this
SEG_GAP = 0.25       # minimum silence between narration segments
CLIP_PAD = 0.5       # outro VO waits at least this long after the clip ends
OUTRO_GAP = 0.6      # ... and at least this long after the last segment
MIN_OUTRO = 6.5      # outro card never shorter than this
OUTRO_TAIL = 1.2     # silence after the outro VO before the video ends


@dataclass
class Cue:
    start: float
    dur: float
    text: str
    pushed: bool = False  # True when the clamp moved it off its offset

    @property
    def end(self) -> float:
        return self.start + self.dur


@dataclass
class Timeline:
    intro_s: float          # intro card length
    clip_dur: float
    intro_cue: Cue          # the intro VO (starts at INTRO_LEAD)
    segments: list[Cue]     # narration beats over the clip
    outro_cue: Cue          # the outro VO
    outro_len: float        # outro card length (stretched to fit VO)
    collisions: list[str] = field(default_factory=list)

    @property
    def total(self) -> float:
        return self.intro_s + self.clip_dur + self.outro_len

    @property
    def all_cues(self) -> list[Cue]:
        return [self.intro_cue, *self.segments, self.outro_cue]


def plan_timeline(
    intro_vo_dur: float,
    clip_dur: float,
    segments: list[tuple[float, float, str]],  # (offset, dur, text)
    outro_vo_dur: float,
    intro_text: str = "",
    outro_text: str = "",
) -> Timeline:
    """Compute the full narration timeline for one video."""
    intro_s = max(MIN_INTRO, intro_vo_dur + 1.0)
    intro_cue = Cue(INTRO_LEAD, intro_vo_dur, intro_text)

    cues: list[Cue] = []
    collisions: list[str] = []
    last_end = INTRO_LEAD + intro_vo_dur
    for off, dur, text in segments:
        requested = intro_s + off
        start = max(requested, last_end + SEG_GAP)
        pushed = start > requested
        if pushed:
            collisions.append(
                f"*** segment @{off:.1f}s pushed {start - requested:.2f}s "
                f"(overlap with previous): {text[:50]}")
        cues.append(Cue(start, dur, text, pushed=pushed))
        last_end = start + dur

    outro_start = max(intro_s + clip_dur + CLIP_PAD, last_end + OUTRO_GAP)
    outro_cue = Cue(outro_start, outro_vo_dur, outro_text)
    outro_len = max(
        MIN_OUTRO,
        outro_start + outro_vo_dur + OUTRO_TAIL - (intro_s + clip_dur))

    return Timeline(
        intro_s=intro_s, clip_dur=clip_dur, intro_cue=intro_cue,
        segments=cues, outro_cue=outro_cue, outro_len=outro_len,
        collisions=collisions)


def print_timeline(tl: Timeline) -> None:
    for c in tl.segments:
        mark = " ***" if c.pushed else ""
        print(f"  seg @{c.start:5.1f}s  {c.dur:4.1f}s  {c.text[:55]}{mark}")
    print(f"intro {tl.intro_s:.1f}s + clip {tl.clip_dur:.1f}s + outro "
          f"{tl.outro_len:.1f}s = {tl.total:.1f}s "
          f"(outro VO @{tl.outro_cue.start:.1f}s)")
    for line in tl.collisions:
        print(line)
