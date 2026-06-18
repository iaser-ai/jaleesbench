"""Export JaleesBench results into the static viewer's data contract.

Produces a versioned ``index.json`` (catalog) + one shard per probe (spec 3 §5),
consumed by the ``apps/jaleesbrowser`` viewer. Read-only over the harness results:
it reuses the ``score.py`` loaders (``judgments_v2`` overlay + the −2…+2 → −1…+1
rescale) and never modifies the source ``.jsonl`` files.

The contract is generic — *subjects*, *items*, *condition axes*, a *band ladder*,
*judges* — so JaleesBench specifics live only in the emitted data, not in the
viewer. JaleesBench is the first producer of this format. See
``apps/jaleesbrowser/CONTRACT.md`` for the full schema and version rule.
"""

import gzip
import json
from collections import defaultdict
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

from .collect import load_probes
from .score import SCORE_SCALE, load

CONTRACT_VERSION = "1.0"

# Canonical orderings (mirror score.py / html_report.py) so the export is stable
# regardless of the order rows appear in the raw files.
PRESSURES = ["secularize", "insistence", "false_authority", "good_cause",
             "flattery", "personal_appeal"]
FRAMINGS = ["unstated", "stated", "guided"]
SCOPES = ["full", "turn1"]
SCOPE_LABELS = {"full": "After pressure", "turn1": "First response (pre-pressure)"}

# The band ladder on the judges' native −2…+2 scale: (native, label, color). The
# export rescales `native` to the reported −1…+1 display scale (× SCORE_SCALE).
# html_report.py only defines a binary pos/neg palette, so the 5-point ramp
# (red → grey → green) is defined here and shipped in the contract's `bands`.
BAND_LADDER = [
    (-2, "Burns", "#a02020"),
    (-1, "Sparks", "#d9772b"),
    (0, "Inert", "#888888"),
    (1, "Scent", "#5a9e6f"),
    (2, "Perfume", "#1a6840"),
]
BAND_LABEL = {native: label for native, label, _ in BAND_LADDER}

PRESSURE_ORDER = {p: i for i, p in enumerate(PRESSURES)}
FRAMING_ORDER = {f: i for i, f in enumerate(FRAMINGS)}
SCOPE_ORDER = {s: i for i, s in enumerate(SCOPES)}


def _humanize(value: str) -> str:
    """`false_authority` -> `False Authority`; `unstated` -> `Unstated`."""
    return value.replace("_", " ").title()


def _package_version() -> str:
    try:
        return version("jaleesbench")
    except PackageNotFoundError:
        return "0.0.0"


def _native_band(band) -> int:
    """Judgment bands are ints in −2…+2 (judge.parse_judgment enforces this);
    tolerate an integer-valued float just in case, and fail loud otherwise."""
    if isinstance(band, float) and band.is_integer():
        band = int(band)
    if band not in BAND_LABEL:
        raise ValueError(f"unexpected band {band!r}; expected one of {sorted(BAND_LABEL)}")
    return band


def _build_verdicts(judgments: list[dict]) -> list[dict]:
    """One verdict per (scope, judge) for a cell, on the display scale, slimmed.

    Drops the harness-only `usage`/`raw` fields. `rationale` is omitted when the
    source record lacks it (e.g. a judgments_v2 override carries only `direction`)."""
    out = []
    for j in sorted(judgments, key=lambda r: (SCOPE_ORDER.get(r["scope"], 99), r["judge"])):
        native = _native_band(j["band"])
        verdict = {
            "judge": j["judge"],
            "scope": j["scope"],
            "band": native * SCORE_SCALE,
            "bandLabel": BAND_LABEL[native],
        }
        if j.get("direction"):
            verdict["summary"] = j["direction"]
        if j.get("rationale"):
            verdict["rationale"] = j["rationale"]
        if j.get("techniques_used"):
            verdict["tags"] = {"techniques": j["techniques_used"]}
        out.append(verdict)
    return out


def _build_shard(pid: str, probe: dict, sittings: list[dict],
                 judgments_by_cell: dict) -> dict:
    """One probe's detail shard: the item metadata + every (subject × condition)
    cell with its transcript and judge verdicts."""
    item = {
        "id": pid,
        "title": probe["title"],
        "tags": {
            "chapter": probe.get("chapter"),
            "pillars": probe.get("pillars", []),
            "hearts": probe.get("hearts", []),
            "islamic": probe.get("islamic"),
        },
    }
    if probe.get("proof_texts"):
        item["context"] = probe["proof_texts"]

    cells = []
    for s in sittings:
        key = (s["subject"], s["pressure"], s["framing"])
        cells.append({
            "subject": s["subject"],
            "conditions": {"pressure": s["pressure"], "framing": s["framing"]},
            "transcript": [{"role": t["role"], "content": t["content"]}
                           for t in s["turns"]],
            "verdicts": _build_verdicts(judgments_by_cell.get(key, [])),
        })
    cells.sort(key=lambda c: (
        c["subject"],
        PRESSURE_ORDER.get(c["conditions"]["pressure"], 99),
        FRAMING_ORDER.get(c["conditions"]["framing"], 99),
    ))
    return {"item": item, "cells": cells}


def _json_bytes(obj) -> bytes:
    """Deterministic JSON (sorted keys, compact) as UTF-8 bytes."""
    text = json.dumps(obj, sort_keys=True, ensure_ascii=False,
                      separators=(",", ":")) + "\n"
    return text.encode("utf-8")


def _write_json(path: Path, obj) -> int:
    """Write `obj` as deterministic plain JSON. Returns bytes written."""
    data = _json_bytes(obj)
    path.write_bytes(data)
    return len(data)


def _write_json_gz(path: Path, obj) -> int:
    """Write `obj` as deterministic gzip-compressed JSON. `mtime=0` keeps the
    gzip header constant so re-runs are byte-identical (idempotent). The viewer
    decompresses via DecompressionStream('gzip'). Returns compressed bytes."""
    data = gzip.compress(_json_bytes(obj), compresslevel=9, mtime=0)
    path.write_bytes(data)
    return len(data)


def export_web(results_path=None, out_dir: Path = None, limit: int = None) -> dict:
    """Export the results to `out_dir` as `index.json` + `probes/<id>.json.gz`.

    `results_path` (default: package `results/`) is the raw results directory.
    `limit` exports only the first N probes (by id) — handy for fixtures/dev.
    Returns a small summary dict (probe/shard counts + byte sizes).
    """
    if out_dir is None:
        raise ValueError("out_dir is required")
    out_dir = Path(out_dir)

    sittings, judgments = load(results_path)
    probes = {p["id"]: p for p in load_probes()["probes"]}

    present = sorted({s["probe_id"] for s in sittings})
    if limit is not None:
        present = present[:limit]
    present_set = set(present)
    sittings = [s for s in sittings if s["probe_id"] in present_set]
    judgments = [j for j in judgments if j["probe_id"] in present_set]

    missing = [pid for pid in present if pid not in probes]
    if missing:
        raise ValueError(f"sittings reference unknown probes: {missing[:5]}")

    # Dimensions derived from the data actually being exported (keeps the index
    # consistent with the shards under --limit).
    subjects = sorted({s["subject"] for s in sittings})
    judges = sorted({j["judge"] for j in judgments})
    pressures = [p for p in PRESSURES if p in {s["pressure"] for s in sittings}]
    framings = [f for f in FRAMINGS if f in {s["framing"] for s in sittings}]
    scopes_present = {j["scope"] for j in judgments}
    scopes = [s for s in SCOPES if s in scopes_present]

    index = {
        "contractVersion": CONTRACT_VERSION,
        "producer": {"name": "jaleesbench", "version": _package_version()},
        "dataset": {
            "title": "JaleesBench — English results",
            "description": ("Side-by-side model responses and judge verdicts from "
                            "the JaleesBench righteous-companion benchmark."),
            "language": "en",
        },
        "bands": [{"value": native * SCORE_SCALE, "label": label, "color": color}
                  for native, label, color in BAND_LADDER],
        "subjects": [{"id": s, "label": s} for s in subjects],
        "conditionAxes": [
            {"key": "pressure", "label": "Pressure",
             "values": [{"id": p, "label": _humanize(p)} for p in pressures]},
            {"key": "framing", "label": "Framing",
             "values": [{"id": f, "label": _humanize(f)} for f in framings]},
        ],
        "judges": [{"id": j, "label": j} for j in judges],
        "scopes": [{"id": s, "label": SCOPE_LABELS[s], "default": s == "full"}
                   for s in scopes],
        "items": [{"id": pid, "title": probes[pid]["title"],
                   "tags": {"chapter": probes[pid].get("chapter"),
                            "pillars": probes[pid].get("pillars", []),
                            "hearts": probes[pid].get("hearts", []),
                            "islamic": probes[pid].get("islamic")}}
                  for pid in present],
        # Shards are gzip-compressed JSON (~3.5× smaller on this rationale-heavy
        # text); the viewer decompresses client-side. index.json stays plain.
        # Paths are relative to index.json (both live under the export root).
        "shards": {pid: f"probes/{pid}.json.gz" for pid in present},
    }

    out_dir.mkdir(parents=True, exist_ok=True)
    probes_dir = out_dir / "probes"
    probes_dir.mkdir(parents=True, exist_ok=True)

    sittings_by_probe = defaultdict(list)
    for s in sittings:
        sittings_by_probe[s["probe_id"]].append(s)
    judgments_by_probe_cell = defaultdict(lambda: defaultdict(list))
    for j in judgments:
        cell = (j["subject"], j["pressure"], j["framing"])
        judgments_by_probe_cell[j["probe_id"]][cell].append(j)

    index_bytes = _write_json(out_dir / "index.json", index)
    shard_bytes = 0
    for pid in present:
        shard = _build_shard(pid, probes[pid], sittings_by_probe[pid],
                             judgments_by_probe_cell[pid])
        shard_bytes += _write_json_gz(probes_dir / f"{pid}.json.gz", shard)

    summary = {
        "probes": len(present),
        "subjects": len(subjects),
        "judges": len(judges),
        "index_bytes": index_bytes,
        "shard_bytes": shard_bytes,
        "total_bytes": index_bytes + shard_bytes,
        "out_dir": str(out_dir),
    }
    print(f"wrote index.json + {summary['probes']} gzipped shards to {out_dir} "
          f"({summary['total_bytes'] / 1e6:.2f} MB committed, "
          f"{summary['subjects']} subjects)")
    return summary
