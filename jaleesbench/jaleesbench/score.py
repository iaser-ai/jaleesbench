"""Scoring utilities shared by the report, web export, and paper stats:
prices/usage accounting, band formatting, and judgment loading (v2 overlay)."""

import json
from pathlib import Path

from .collect import RESULTS

# USD per million tokens (input, output). Verified 2026-06-11 against provider
# docs (gemini-3.5-flash verified 2026-06-12).
PRICES = {
    "gpt-5.5": (5.00, 30.00),                 # developers.openai.com
    "claude-sonnet-4-6": (3.00, 15.00),       # Anthropic
    "claude-sonnet-5": (2.00, 10.00),         # Anthropic intro pricing through 2026-08-31 (sticker 3/15)
    "claude-opus-4-8": (5.00, 25.00),         # Anthropic
    "gemini-3.1-pro-preview": (2.00, 12.00),  # ai.google.dev, <=200K context tier
    "gemini-3.5-flash": (1.50, 9.00),         # ai.google.dev, flat (incl. thinking)
    "gemma-4-31b": (0.14, 0.40),              # friendli.ai/pricing, 2026-06-12
    "qwen3-235b": (0.20, 0.80),               # friendli.ai/pricing, 2026-06-12
    "glm-5.1": (1.40, 4.40),                  # friendli.ai/pricing, 2026-06-12
    "nemotron-3-ultra": (0.37, 1.08),         # blackbox.ai model page, 2026-06-12
    "inkling": (1.87, 4.68),                  # tinker models page, 2026-07-16 (50% launch discount)
    "ansari": (0.0, 0.0),                     # free community endpoint
}

def usage_cost(model: str, tok: dict) -> float:
    """Cost in USD for accumulated usage. Anthropic 1h-TTL caching: writes
    bill 2x input rate, reads 0.1x. b_-prefixed keys are batch-API tokens,
    billed at 50% of the corresponding rate."""
    pi, po = PRICES[model]
    full = (tok.get("in", 0) * pi + tok.get("out", 0) * po
            + tok.get("cache_write", 0) * pi * 2.0
            + tok.get("cache_read", 0) * pi * 0.1)
    batch = (tok.get("b_in", 0) * pi + tok.get("b_out", 0) * po
             + tok.get("b_cache_write", 0) * pi * 2.0
             + tok.get("b_cache_read", 0) * pi * 0.1)
    return (full + 0.5 * batch) / 1e6


def add_usage(acc: dict, u: dict) -> None:
    pre = "b_" if u.get("batch") else ""
    for k in ("in", "out", "cache_write", "cache_read"):
        acc[pre + k] = acc.get(pre + k, 0) + u.get(k, 0)


def tok_in(tok: dict) -> int:
    return sum(tok.get(k, 0) for k in
               ("in", "cache_write", "cache_read", "b_in", "b_cache_write", "b_cache_read"))


def tok_out(tok: dict) -> int:
    return tok.get("out", 0) + tok.get("b_out", 0)

def mean(xs):
    xs = list(xs)
    return sum(xs) / len(xs) if xs else None


# Band means are computed on the judges' native −2…+2 scale, then reported on a
# −1…+1 scale (halved). Percentages are untouched.
SCORE_SCALE = 0.5


def fmt(x, pct=False):
    if x is None:
        return "—"
    return f"{x:.0%}" if pct else f"{x * SCORE_SCALE:+.2f}"


# Identity of a single band judgment. A v2 re-judge record with the same
# identity overrides the base record (the ≥2-band-disagreement re-judge pass).
JUDGMENT_KEY = ("subject", "probe_id", "pressure", "framing", "judge", "scope")


def load_judgments(results_path=None):
    """Load base judgments, then overlay judgments_v2.jsonl by identity key
    (v2 wins). Non-destructive: the .jsonl files are never modified. v2 is a
    pure override set (every v2 key matches one base record), so the total
    judgment count is unchanged.

    `results_path` overrides the results directory (default: the module-level
    RESULTS) so callers — e.g. the web export — can read a results set that
    lives outside the package."""
    rp = Path(results_path) if results_path else RESULTS
    by_key = {}
    for l in (rp / "judgments.jsonl").read_text().splitlines():
        j = json.loads(l)
        by_key[tuple(j[k] for k in JUDGMENT_KEY)] = j
    v2_path = rp / "judgments_v2.jsonl"
    if v2_path.exists():
        for l in v2_path.read_text().splitlines():
            j = json.loads(l)
            by_key[tuple(j[k] for k in JUDGMENT_KEY)] = j
    return list(by_key.values())


def load(results_path=None):
    """Load (sittings, judgments). `results_path` overrides the results
    directory (default: RESULTS)."""
    rp = Path(results_path) if results_path else RESULTS
    sittings = [json.loads(l) for l in (rp / "collect.jsonl").read_text().splitlines()]
    judgments = load_judgments(results_path)
    return sittings, judgments

