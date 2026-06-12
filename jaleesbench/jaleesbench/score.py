"""Aggregate sittings + judgments into the pilot report."""

import json
from collections import defaultdict
from itertools import combinations

from .collect import RESULTS, load_probes

# USD per million tokens (input, output). Verified 2026-06-11 against provider docs.
PRICES = {
    "gpt-5.5": (5.00, 30.00),                 # developers.openai.com
    "claude-sonnet-4-6": (3.00, 15.00),       # Anthropic
    "claude-opus-4-8": (5.00, 25.00),         # Anthropic
    "gemini-3.1-pro-preview": (2.00, 12.00),  # ai.google.dev, <=200K context tier
    "ansari": (0.0, 0.0),                     # free community endpoint
}

PRESSURES = ["secularize", "insistence", "false_authority", "good_cause",
             "flattery", "personal_appeal"]
FRAMINGS = ["unstated", "stated", "guided"]
TECHNIQUES = ["reads the person", "engages reason", "gentleness with the struggling",
              "gradualism", "exit ramp", "proportion", "open door"]


def mean(xs):
    xs = list(xs)
    return sum(xs) / len(xs) if xs else None


def fmt(x, pct=False):
    if x is None:
        return "—"
    return f"{x:.0%}" if pct else f"{x:+.2f}"


def load():
    sittings = [json.loads(l) for l in (RESULTS / "collect.jsonl").read_text().splitlines()]
    judgments = [json.loads(l) for l in (RESULTS / "judgments.jsonl").read_text().splitlines()]
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

    lines = ["# JaleesBench Pilot Report (auto-generated sections)", ""]
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
    subj_tok = defaultdict(lambda: [0, 0])
    for s in sittings:
        for u in s.get("usage", []):
            subj_tok[s["subject"]][0] += u["in"]
            subj_tok[s["subject"]][1] += u["out"]
    for s, (ti, to) in sorted(subj_tok.items()):
        pi, po = PRICES[s]
        c = ti / 1e6 * pi + to / 1e6 * po
        total += c
        lines.append(f"| collection | {s} | {ti:,} | {to:,} | ${c:.2f} |")
    judge_tok = defaultdict(lambda: [0, 0])
    for j in judgments:
        u = j.get("usage")
        if u:
            judge_tok[j["judge"]][0] += u["in"]
            judge_tok[j["judge"]][1] += u["out"]
    for jname, (ti, to) in sorted(judge_tok.items()):
        pi, po = PRICES[jname]
        c = ti / 1e6 * pi + to / 1e6 * po
        total += c
        lines.append(f"| judging | {jname} | {ti:,} | {to:,} | ${c:.2f} |")
    lines.append(f"| **total** | | | | **${total:.2f}** |")
    lines.append("")
    lines.append("*Prices per Mtok, verified 2026-06-11: gpt-5.5 $5/$30; "
                 "claude-sonnet-4-6 $3/$15; claude-opus-4-8 $5/$25; "
                 "gemini-3.1-pro-preview $2/$12; ansari free (no usage reported).*")

    out = RESULTS / "pilot-report.md"
    out.write_text("\n".join(lines) + "\n")
    print(f"wrote {out}")
