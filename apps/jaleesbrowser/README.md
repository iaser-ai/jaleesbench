# jaleesbrowser

A public, zero-install web app for exploring JaleesBench results: read what two models
actually said side by side, find the questions where they differ most, and drill into
the judge verdicts. Every view is encoded in the URL as a shareable deep link.

It is a static TypeScript SPA (Vite + React). The UI is kept generic — it uses
*subjects / items / condition axes / a band ladder / judges* — so the
JaleesBench-specific values (pressure/framing/Burns…) come from the exported data, not
the components. There is no formal versioned contract; the data shapes are documented
below.

## Layout

```
apps/jaleesbrowser/
  src/                     app source (data types, DataSource seam, UI)
  public/data/             the exported dataset (committed)
    index.json             catalog + compact per-cell score blob + presets (plain JSON)
    probes/<id>.json.gz    one gzip-compressed shard per probe (transcripts + verdicts)
```

## Data format

`export-web` writes `index.json` (plain) + one gzip shard per probe:

- **`index.json`** — `dataset`, `bands`, `subjects` (+ overall means), `conditionAxes`
  (the generic pressure/framing seam), `judges`, `scopes`, `items`, `shards` (itemId →
  path), a compact **`scores`** blob (`{order, shape, data}` — flat per-cell mean bands
  so compare + presets are instant), **`presets`** (curated deep-links), and a
  **`paper`** link. Just data — no versioned schema.
- **shards** — `{ item, cells[] }`; each cell has the two-turn `transcript` and the
  per-judge `verdicts`. Loaded lazily, only when a drill-in opens.

## Develop

```bash
cd apps/jaleesbrowser
npm install
npm run dev        # http://localhost:5173
npm test           # Vitest (jsdom)
npm run build      # type-check + production bundle into dist/
npm run preview    # serve the production build locally
```

## Regenerate the data

The viewer's data is produced by the Python harness from the (gitignored) raw
results. The raw `collect.jsonl` / `judgments.jsonl` are large and never committed;
the slimmed, gzip-compressed export (~60 MB) **is** committed so static hosting and CI
need no access to the raw data.

```bash
# from the repo root, with the raw results available locally:
cd jaleesbench
uv run jaleesbench export-web \
  --results-path <path-to-results> \
  --out ../apps/jaleesbrowser/public/data
#   --limit N   # optional: export only the first N probes (handy for a dev fixture)
```

The export is deterministic (sorted keys, fixed orderings, gzip `mtime=0`), so
re-running it on unchanged inputs produces byte-identical files.

## Deploy

GitHub Pages, via `.github/workflows/pages.yml` (push to `main` touching
`apps/jaleesbrowser/**`, or manual dispatch). The workflow only **builds** the
committed app + data — it does not regenerate the export. The Vite `base` is `./`
(relative), so the bundle works at the project Pages path
(`https://<org>.github.io/jaleesbench/`) with no hardcoded prefix.

Shards are served as `*.json.gz`; the viewer decompresses them, detecting whether the
host already applied `Content-Encoding: gzip` (gzip magic byte). `index.json` is plain.

## Scope

English results only for now. Arabic is excluded until its judging run completes, but is
not precluded by design — it would be another dataset in the same format
(`language: "ar"`, which drives RTL layout).
