# Results-viewer data contract

**Version 1.0**

The `jaleesbrowser` viewer renders any dataset that conforms to this contract. It is
**generic** — it knows about *subjects*, *items*, *condition axes*, a *band ladder*,
*judges*, *transcripts*, and *verdicts*, but nothing about JaleesBench's specific
models, pressures, framings, or band names. All of those live in the **data**, so a
different producer emitting the same shapes renders with no code change.

JaleesBench is the first producer of this format, via
`jaleesbench export-web --out <dir> [--results-path <dir>] [--limit N]`.

A dataset is two kinds of artifact:

1. **`index.json`** — one catalog/manifest, loaded once on startup. Plain JSON.
2. **Per-item shards** — one **gzip-compressed** JSON file per item (here: per probe),
   loaded on demand and decompressed client-side. Paths in `index.shards` end in
   `.json.gz`.

---

## `index.json`

```jsonc
{
  "contractVersion": "1.0",            // MAJOR.MINOR; viewer requires matching MAJOR
  "producer": { "name": "jaleesbench", "version": "0.1.0" },
  "dataset": {
    "title": "JaleesBench — English results",
    "description": "…",
    "language": "en"                   // BCP-47-ish; drives LTR/RTL text direction
  },

  // The band ladder on the DISPLAY scale (−1…+1 here), low → high. The viewer
  // renders chips and the legend purely from this list. `color` is optional; when
  // absent the viewer derives a positional ramp. Labels carry the meaning, so color
  // is never the sole differentiator.
  "bands": [
    { "value": -1,   "label": "Burns",   "color": "#a02020" },
    { "value": -0.5, "label": "Sparks",  "color": "#d9772b" },
    { "value": 0,    "label": "Inert",   "color": "#888888" },
    { "value": 0.5,  "label": "Scent",   "color": "#5a9e6f" },
    { "value": 1,    "label": "Perfume", "color": "#1a6840" }
  ],

  "subjects": [ { "id": "ansari", "label": "ansari" }, … ],   // the comparable models

  // The generic seam for what JaleesBench calls pressure + framing. An ORDERED list
  // of axes; the viewer renders one selector per axis by iterating this list — it
  // never hardcodes axis keys. A producer with one axis, or three, works unchanged.
  "conditionAxes": [
    { "key": "pressure", "label": "Pressure",
      "values": [ { "id": "secularize", "label": "Secularize" }, … ] },
    { "key": "framing",  "label": "Framing",
      "values": [ { "id": "unstated", "label": "Unstated" }, … ] }
  ],

  "judges": [ { "id": "claude-opus-4-8", "label": "claude-opus-4-8" }, … ],

  // Optional per-verdict scope axis. Exactly one entry SHOULD set "default": true.
  "scopes": [
    { "id": "full",  "label": "After pressure",            "default": true },
    { "id": "turn1", "label": "First response (pre-pressure)" }
  ],

  // The questions/probes. `title` shows in the picker; `tags` is an OPAQUE, optional
  // key→value(s) map shown generically (the viewer assigns no meaning to keys).
  "items": [
    { "id": "JLS-001", "title": "The team message",
      "tags": { "chapter": "…", "pillars": ["restraint"], "hearts": ["patience"],
                "islamic": "clean" } },
    …
  ],

  // Where to fetch each item's detail shard — gzip-compressed JSON, path relative
  // to index.json. The viewer fetches and decompresses (DecompressionStream).
  "shards": { "JLS-001": "probes/JLS-001.json.gz", … }
}
```

## Per-item shard (e.g. `probes/JLS-001.json.gz`, relative to `index.json`)

The shard is **gzip-compressed JSON** on the wire/disk; decompressed it is:

```jsonc
{
  "item": {
    "id": "JLS-001",
    "title": "The team message",
    "tags": { "chapter": "…", "pillars": […], "hearts": […], "islamic": "clean" },
    "context": "…"                     // optional producer text (proof texts here)
  },

  // One cell per (subject × condition-tuple).
  "cells": [
    {
      "subject": "ansari",
      "conditions": { "pressure": "insistence", "framing": "unstated" },

      // Ordered turns; role ∈ "user" | "assistant". Generic length (4 here:
      // question → response → pressure turn → response).
      "transcript": [
        { "role": "user",      "content": "…" },
        { "role": "assistant", "content": "…" },
        { "role": "user",      "content": "…" },
        { "role": "assistant", "content": "…" }
      ],

      // One verdict per (scope, judge). `band` is on the DISPLAY scale and matches a
      // bands[].value; `bandLabel` is its label. `rationale` MAY be absent (a
      // re-judged override can carry only `summary`). `tags` is optional.
      "verdicts": [
        {
          "judge": "claude-opus-4-8",
          "scope": "full",
          "band": 1,
          "bandLabel": "Perfume",
          "summary": "…",               // short verdict direction
          "rationale": "…",             // optional — viewer tolerates absence
          "tags": { "techniques": ["open door"] }   // optional
        },
        …
      ]
    },
    …
  ]
}
```

---

## Consumption rules (for the viewer)

- Validate `contractVersion` MAJOR; render a fail-soft "unsupported data version" if it
  doesn't match. Ignore unknown fields (forward-compatible).
- Build the question picker from `items`, the two model pickers from `subjects`, one
  selector per `conditionAxes` entry, the band legend from `bands`, and the scope
  toggle from `scopes` — all generically, with no hardcoded JaleesBench strings.
- Lazy-fetch a shard via `shards[itemId]` (relative to `index.json`) when an item is
  selected; **decompress it with `DecompressionStream('gzip')`** (fetch → pipe through
  the stream → `JSON.parse`) and cache the result.
- Locate a cell by `(subject, conditions)`. A missing cell renders "no data for this
  combination".
- Treat all producer/model text (`transcript`, `summary`, `rationale`, `tags`,
  `context`) as **untrusted**: render escaped/plain, never as raw HTML.

## Versioning

`contractVersion` is `MAJOR.MINOR`. The viewer requires a matching MAJOR and ignores
unknown fields. Additive, backward-compatible changes bump MINOR; breaking shape
changes bump MAJOR.

## Producer notes (JaleesBench)

- Bands are emitted on the reported **−1…+1** display scale (the judges' native −2…+2
  band × `SCORE_SCALE` = 0.5). `bandLabel` comes from the native band
  (Burns/Sparks/Inert/Scent/Perfume).
- The `judgments_v2` overlay (re-judged ≥2-band-disagreement cells) is applied before
  export; such records may lack `rationale`, so `rationale` is optional.
- Harness-only fields (`usage`, `raw`, `attempts`, `context_prefix`) are dropped to
  keep shards small.
- Shards are gzip-compressed (`.json.gz`). On JaleesBench's rationale-heavy text gzip
  yields ~3.5×, so the full English set commits at **~62 MB** instead of ~220 MB plain.
  `index.json` is left plain (it is small).
- Output is deterministic — sorted keys, fixed orderings, and gzip `mtime=0` — so
  re-runs are byte-identical (idempotent).
