"""Constants and filters shared by the pipeline steps — one copy of what the
as-run scripts each carried inline."""

import json
import re

from .paths import SPLIT

# Judge holdout: Gemini selects training data, Opus scores held-out results.
GEMINI = "gemini-3.1-pro-preview"
OPUS = "claude-opus-4-8"

# Preference pairs need this much band gap on the native -2..+2 scale.
MIN_GAP = 2

# Dangling-citation screen: [n]-style markers that never resolve in-turn teach
# fabricated-citation style, so a chosen/training side that has them is dropped.
MARKER = re.compile(r"\[\d+\]")
RESOLVES = re.compile(r"(?im)^(\*{0,2}(references|sources|citations)\b|\[\d+\]\s*[A-Z؀-ۿ])")

# Guide-reference screen for stage-1 training sets: an answer that talks about
# its instructions would teach the model to mention a guide it no longer has.
GUIDE_REF = re.compile(
    r"(?i)(context above|the context for this conversation|as instructed|"
    r"my instructions|my guidelines|the guide(?:lines)? (?:above|says|asks)|"
    r"i was (?:asked|told) to|per the (?:context|instructions))")


def dangling_markers(turns) -> bool:
    text = turns[1]["content"] + "\n" + turns[3]["content"]
    return bool(MARKER.search(text)) and not RESOLVES.search(text)


def load_split(path=SPLIT) -> dict:
    """The 70/70 scenario split of record: {'train': [...], 'test': [...], 'seed': 3446, ...}."""
    return json.loads(path.read_text())
