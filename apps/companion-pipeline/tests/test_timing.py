"""Timing rules — each one was learned from a shipped bug; the tests pin
them down so a port/refactor can't silently change the timeline."""

import pytest

from companion_pipeline.timing import (
    CLIP_PAD, INTRO_LEAD, MIN_INTRO, MIN_OUTRO, OUTRO_GAP, OUTRO_TAIL,
    SEG_GAP, plan_timeline)


def test_intro_minimum_length():
    tl = plan_timeline(2.0, 30.0, [], 3.0)
    assert tl.intro_s == MIN_INTRO  # short VO still gets the minimum card


def test_intro_stretches_for_long_vo():
    tl = plan_timeline(9.0, 30.0, [], 3.0)
    assert tl.intro_s == 10.0  # vo + 1.0


def test_segment_at_requested_offset_when_clear():
    tl = plan_timeline(4.0, 30.0, [(10.0, 3.0, "a")], 3.0)
    assert tl.segments[0].start == tl.intro_s + 10.0
    assert not tl.segments[0].pushed
    assert tl.collisions == []


def test_segments_clamped_non_overlapping():
    # second segment requests an offset that lands inside the first
    tl = plan_timeline(4.0, 30.0, [(1.0, 5.0, "a"), (2.0, 3.0, "b")], 3.0)
    a, b = tl.segments
    assert b.start == pytest.approx(a.end + SEG_GAP)
    assert b.pushed
    assert len(tl.collisions) == 1
    assert "***" in tl.collisions[0]


def test_first_segment_never_collides_with_intro_vo():
    # intro_s = vo + 1.0 guarantees the intro VO (ending at INTRO_LEAD + vo)
    # clears any segment at offset >= 0 by more than SEG_GAP
    for vo in (2.0, 8.0, 20.0):
        tl = plan_timeline(vo, 30.0, [(0.0, 2.0, "a")], 3.0)
        seg = tl.segments[0]
        assert seg.start >= INTRO_LEAD + vo + SEG_GAP
        assert not seg.pushed


def test_outro_waits_for_clip_end():
    tl = plan_timeline(4.0, 30.0, [(1.0, 2.0, "a")], 3.0)
    assert tl.outro_cue.start == pytest.approx(
        tl.intro_s + tl.clip_dur + CLIP_PAD)


def test_outro_waits_for_last_segment():
    # last segment ends after the clip does -> outro pushed past it
    tl = plan_timeline(4.0, 10.0, [(9.0, 8.0, "a")], 3.0)
    last = tl.segments[-1]
    assert tl.outro_cue.start == pytest.approx(last.end + OUTRO_GAP)


def test_outro_card_stretches_to_fit_vo():
    # long outro VO -> outro card longer than the minimum
    tl = plan_timeline(4.0, 10.0, [], 12.0)
    expected = (tl.outro_cue.start + 12.0 + OUTRO_TAIL
                - (tl.intro_s + tl.clip_dur))
    assert tl.outro_len == pytest.approx(expected)
    assert tl.outro_len > MIN_OUTRO


def test_outro_card_minimum():
    tl = plan_timeline(4.0, 30.0, [], 1.0)
    assert tl.outro_len == MIN_OUTRO


def test_total_is_sum_of_parts():
    tl = plan_timeline(5.0, 20.0, [(1.0, 2.0, "a")], 3.0)
    assert tl.total == pytest.approx(
        tl.intro_s + tl.clip_dur + tl.outro_len)


def test_all_cues_order():
    tl = plan_timeline(5.0, 20.0, [(1.0, 2.0, "a"), (5.0, 2.0, "b")], 3.0)
    starts = [c.start for c in tl.all_cues]
    assert starts == sorted(starts)
    assert len(tl.all_cues) == 4  # intro + 2 segments + outro
