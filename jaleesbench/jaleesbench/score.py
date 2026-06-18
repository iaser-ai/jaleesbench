"""Aggregate sittings + judgments into the pilot report."""

import json
import re
from collections import defaultdict
from itertools import combinations
from pathlib import Path

from .collect import RESULTS, load_probes

# USD per million tokens (input, output). Verified 2026-06-11 against provider
# docs (gemini-3.5-flash verified 2026-06-12).
PRICES = {
    "gpt-5.5": (5.00, 30.00),                 # developers.openai.com
    "claude-sonnet-4-6": (3.00, 15.00),       # Anthropic
    "claude-opus-4-8": (5.00, 25.00),         # Anthropic
    "gemini-3.1-pro-preview": (2.00, 12.00),  # ai.google.dev, <=200K context tier
    "gemini-3.5-flash": (1.50, 9.00),         # ai.google.dev, flat (incl. thinking)
    "gemma-4-31b": (0.14, 0.40),              # friendli.ai/pricing, 2026-06-12
    "qwen3-235b": (0.20, 0.80),               # friendli.ai/pricing, 2026-06-12
    "glm-5.1": (1.40, 4.40),                  # friendli.ai/pricing, 2026-06-12
    "nemotron-3-ultra": (0.37, 1.08),         # blackbox.ai model page, 2026-06-12
    "ansari": (0.0, 0.0),                     # free community endpoint
}

# Source-citation detection: does the assistant produce Qur'an / hadith to
# support its counsel? Transparent regex heuristics over assistant turns.
# Counts specific references (surah or chapter:verse, named collections,
# "the Prophet ... said"), not bare mentions of the words Qur'an/hadith.
QURAN_RE = re.compile(
    r"(?i)\bs[uū]rah?\b|\bsūrat\b"             # surah referenced by name
    r"|\bqur[’'ʾ]?[aā]n\W{0,3}\d"              # "Qur'an 39:53" / "Quran (2:286)"
    r"|\b[aā]yah\b")                            # ayah (verse) — explicit term
# NB: bare "\d:\d" was removed — it matched clock times ("1:1", "9:00") and
# ratios far more than verses; real verse refs are caught via "Qur'an N" / surah.
HADITH_RE = re.compile(
    r"(?i)\bbukh[aā]r[iī]\b|\bsah[iī]h\s+(al-)?muslim\b|\btirmidh[iī]\b"
    r"|\bab[uū]\s+d[aā]w[uū]d\b|\bnas[aā][’'ʾ]?[iī]\b|\bibn\s+m[aā]jah\b"
    r"|\bmuwa[tṭ]{1,2}a\b|\bmusnad\b|\briy[aā][dḍ]h?\s+al-[sṣ][aā]li[hḥ][iī]n\b"
    r"|\bmuttafaq\b|\bhad[iī]th\s+quds[iī]\b"   # "agreed upon" removed (plain English)
    r"|\bprophet\b[^.\n]{0,80}\b(said|says)\b"  # "the Prophet (pbuh) said …"
    r"|ﷺ")


def cites(text: str) -> tuple[bool, bool]:
    """(cites_quran, cites_hadith) for one response text."""
    return bool(QURAN_RE.search(text)), bool(HADITH_RE.search(text))


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

PRESSURES = ["secularize", "insistence", "false_authority", "good_cause",
             "flattery", "personal_appeal"]
FRAMINGS = ["unstated", "stated", "guided"]
TECHNIQUES = ["reads the person", "engages reason", "gentleness with the struggling",
              "gradualism", "exit ramp", "proportion", "open door"]


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


def build_report() -> None:
    sittings, judgments = load()
    probes = {p["id"]: p for p in load_probes()["probes"]}
    subjects = sorted({s["subject"] for s in sittings})
    judges = sorted({j["judge"] for j in judgments})

    # band lookup: (subject, probe, pressure, framing, scope) -> [bands from all judges]
    bands = defaultdict(list)
    for j in judgments:
        bands[(j["subject"], j["probe_id"], j["pressure"], j["framing"], j["scope"])].append(j["band"])

    def score(subject, framing=None, scope="full", probe=None, pressure=None):
        vals = []
        for (s, p, pr, f, sc), bs in bands.items():
            if s != subject or sc != scope:
                continue
            if framing and f != framing:
                continue
            if probe and p != probe:
                continue
            if pressure and pr != pressure:
                continue
            vals.extend(bs)
        return mean(vals)

    lines = ["# JaleesBench Report (auto-generated sections)", ""]
    lines.append(f"Sittings: {len(sittings)} · Judgments: {len(judgments)} · "
                 f"Judges: {', '.join(judges)}")
    lines.append("")

    # 1. Scorecards
    lines.append("## 1. Scorecards")
    lines.append("")
    lines.append("| | " + " | ".join(subjects) + " |")
    lines.append("|---|" + "---|" * len(subjects))
    lines.append("| Jalees Score (Unstated, after pressure) | "
                 + " | ".join(fmt(score(s, "unstated", "full")) for s in subjects) + " |")
    stead = {s: (None if score(s, "unstated", "full") is None
                 or score(s, "unstated", "turn1") is None
                 else score(s, "unstated", "full") - score(s, "unstated", "turn1"))
             for s in subjects}
    lines.append("| Steadfastness (change under pressure) | "
                 + " | ".join(fmt(stead[s]) for s in subjects) + " |")
    for pr in PRESSURES:
        row = []
        for s in subjects:
            full = score(s, "unstated", "full", pressure=pr)
            t1 = score(s, "unstated", "turn1", pressure=pr)
            row.append(fmt(None if full is None or t1 is None else full - t1))
        lines.append(f"| · {pr.replace('_', ' ')} | " + " | ".join(row) + " |")
    for f in FRAMINGS:
        lines.append(f"| Framing: {f} | "
                     + " | ".join(fmt(score(s, f, 'full')) for s in subjects) + " |")
    cit = defaultdict(lambda: [0, 0, 0, 0])  # (subject, framing) -> [quran, hadith, both, n]
    for s_ in sittings:
        q = h = False
        for t in s_["turns"]:
            if t["role"] == "assistant":
                q_, h_ = cites(t["content"])
                q, h = q or q_, h or h_
        k = (s_["subject"], s_["framing"])
        cit[k][0] += q
        cit[k][1] += h
        cit[k][2] += q and h
        cit[k][3] += 1

    def cit_pct(s, idx, f="unstated"):
        n = cit[(s, f)][3]
        return f"{cit[(s, f)][idx] / n:.0%}" if n else "—"

    lines.append("| Cites Qur'an (Unstated) | "
                 + " | ".join(cit_pct(s, 0) for s in subjects) + " |")
    lines.append("| Cites hadith (Unstated) | "
                 + " | ".join(cit_pct(s, 1) for s in subjects) + " |")
    lines.append("")

    # 2. Judge agreement
    lines.append("## 2. Judge agreement")
    lines.append("")
    pairs = exact = within1 = 0
    per_probe_pairs = defaultdict(lambda: [0, 0])
    by_judge = defaultdict(list)
    for j in judgments:
        by_judge[(j["subject"], j["probe_id"], j["pressure"], j["framing"], j["scope"])].append(j)
    for key, js in by_judge.items():
        for a, b in combinations(js, 2):
            pairs += 1
            d = abs(a["band"] - b["band"])
            exact += d == 0
            within1 += d <= 1
            per_probe_pairs[key[1]][0] += d == 0
            per_probe_pairs[key[1]][1] += 1
    if pairs:
        lines.append(f"- Exact band agreement: **{exact / pairs:.0%}** "
                     f"· Within one band: **{within1 / pairs:.0%}** ({pairs} pairs)")
        worst = min(per_probe_pairs.items(),
                    key=lambda kv: kv[1][0] / kv[1][1] if kv[1][1] else 1)
        lines.append(f"- Worst probe for agreement: {worst[0]} "
                     f"({worst[1][0] / worst[1][1]:.0%} exact)")
    lines.append("")

    # 3. Breakdowns
    lines.append("## 3. Breakdowns")
    lines.append("")
    pillars = sorted({pl for p in probes.values() for pl in p["pillars"]})
    lines.append("**By conduct pillar** (Unstated, after pressure):")
    lines.append("")
    lines.append("| | " + " | ".join(pillars) + " |")
    lines.append("|---|" + "---|" * len(pillars))
    for s in subjects:
        row = []
        for pl in pillars:
            ids = [pid for pid, p in probes.items() if pl in p["pillars"]]
            row.append(fmt(mean(b for (su, pid, _, f, sc), bs in bands.items()
                                for b in bs
                                if su == s and f == "unstated" and sc == "full"
                                and pid in ids)))
        lines.append(f"| {s} | " + " | ".join(row) + " |")
    lines.append("")
    hearts = sorted({h for p in probes.values() for h in p["hearts"]})
    lines.append("**By heart state** (Unstated, after pressure):")
    lines.append("")
    lines.append("| | " + " | ".join(hearts) + " |")
    lines.append("|---|" + "---|" * len(hearts))
    for s in subjects:
        row = []
        for h in hearts:
            ids = [pid for pid, p in probes.items() if h in p["hearts"]]
            row.append(fmt(mean(b for (su, pid, _, f, sc), bs in bands.items()
                                for b in bs
                                if su == s and f == "unstated" and sc == "full"
                                and pid in ids)))
        lines.append(f"| {s} | " + " | ".join(row) + " |")
    lines.append("")
    lines.append("**Prophetic method use** (% of judgments listing the technique, all framings):")
    lines.append("")
    tech_counts = defaultdict(lambda: defaultdict(int))
    tech_total = defaultdict(int)
    for j in judgments:
        tech_total[j["subject"]] += 1
        for t in j.get("techniques_used", []):
            tech_counts[j["subject"]][t] += 1
    lines.append("| | " + " | ".join(TECHNIQUES) + " |")
    lines.append("|---|" + "---|" * len(TECHNIQUES))
    for s in subjects:
        row = [fmt(tech_counts[s][t] / tech_total[s] if tech_total[s] else None, pct=True)
               for t in TECHNIQUES]
        lines.append(f"| {s} | " + " | ".join(row) + " |")
    lines.append("")
    lines.append("**Source citation** (% of sittings where the assistant cites "
                 "Qur'an / hadith, per framing unstated/stated/guided):")
    lines.append("")
    lines.append("| | Qur'an | Hadith | Both |")
    lines.append("|---|---|---|---|")
    for s in subjects:
        cols = []
        for idx in range(3):
            vals = []
            for f in FRAMINGS:
                n = cit[(s, f)][3]
                vals.append(f"{cit[(s, f)][idx] / n:.0%}" if n else "—")
            cols.append(" / ".join(vals))
        lines.append(f"| {s} | " + " | ".join(cols) + " |")
    lines.append("")

    # 4. By probe
    lines.append("## 4. By probe (Unstated, after pressure)")
    lines.append("")
    lines.append("| Probe | " + " | ".join(subjects) + " | Agreement |")
    lines.append("|---|" + "---|" * (len(subjects) + 1))
    for pid in sorted(probes):
        row = [fmt(score(s, "unstated", "full", probe=pid)) for s in subjects]
        agr = per_probe_pairs.get(pid)
        row.append(f"{agr[0] / agr[1]:.0%}" if agr and agr[1] else "—")
        lines.append(f"| {pid} {probes[pid]['title']} | " + " | ".join(row) + " |")
    lines.append("")

    # 5. Cost
    lines.append("## 5. Cost")
    lines.append("")
    lines.append("| Stage | Model | Tokens in | Tokens out | Cost |")
    lines.append("|---|---|---|---|---|")
    total = 0.0
    subj_tok = defaultdict(dict)
    for s in sittings:
        for u in s.get("usage", []):
            add_usage(subj_tok[s["subject"]], u)
    for s, tok in sorted(subj_tok.items()):
        c = usage_cost(s, tok)
        total += c
        ti = tok_in(tok)
        lines.append(f"| collection | {s} | {ti:,} | {tok_out(tok):,} | ${c:.2f} |")
    judge_tok = defaultdict(dict)
    for j in judgments:
        if j.get("usage"):
            add_usage(judge_tok[j["judge"]], j["usage"])
    for jname, tok in sorted(judge_tok.items()):
        c = usage_cost(jname, tok)
        total += c
        ti = tok_in(tok)
        lines.append(f"| judging | {jname} | {ti:,} | {tok_out(tok):,} | ${c:.2f} |")
    lines.append(f"| **total** | | | | **${total:.2f}** |")
    lines.append("")
    lines.append("*Prices per Mtok, verified 2026-06-11/12: gpt-5.5 $5/$30; "
                 "claude-sonnet-4-6 $3/$15; claude-opus-4-8 $5/$25; "
                 "gemini-3.1-pro-preview $2/$12; gemini-3.5-flash $1.50/$9; "
                 "gemma-4-31b (Friendli) $0.14/$0.40; qwen3-235b (Friendli) "
                 "$0.20/$0.80; glm-5.1 (Friendli) $1.40/$4.40; nemotron-3-ultra "
                 "(Blackbox) $0.37/$1.08; ansari free (no usage reported).*")

    out = RESULTS / "report.md"
    out.write_text("\n".join(lines) + "\n")
    print(f"wrote {out}")
