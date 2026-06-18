# jaleesbrowser

A public, zero-install web app for browsing JaleesBench results: pick a question,
pick two models, pick a pressure + framing, and read the two conversations and the
judge verdicts **side by side**. The full selection is encoded in the URL, so every
view is a shareable deep link.

It is a static TypeScript SPA (Vite + React) that reads an exported, **versioned data
contract** — it is generic over *subjects / items / condition axes / a band ladder /
judges*, with JaleesBench as the first producer of that format. See
[`CONTRACT.md`](./CONTRACT.md).

## Layout

```
apps/jaleesbrowser/
  src/                     app source (contract types, DataSource seam, UI)
  public/data/             the exported dataset (committed)
    index.json             catalog/manifest (plain JSON)
    probes/<id>.json.gz    one gzip-compressed shard per probe
  CONTRACT.md              the data-contract reference
```

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

Shards are served as `*.json.gz` and decompressed in the browser via
`DecompressionStream('gzip')`; `index.json` is plain.

## Scope

English results only for now. Arabic is excluded until its judging run completes, but
is not precluded by design — it would be another dataset in the same contract
(`language: "ar"`, which drives RTL layout).
