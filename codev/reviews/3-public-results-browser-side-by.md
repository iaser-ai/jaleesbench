# Review: public-results-browser-side-by

## Summary

A public, zero-install web app (`apps/jaleesbrowser/`) for **exploring** JaleesBench
results. A newcomer can orient (what the benchmark measures), **compare two models and
see the questions where they differ most**, and **drill in** to the side-by-side
transcripts and both judges' verdicts — every view URL-shareable, on GitHub Pages, with
no backend. Fed by a Python `jaleesbench export-web` CLI.

The work shipped in two arcs:
1. **Foundation** (5 phases): the export CLI + data shapes (`index.json` + gzip per-probe
   shards), the client-side `DataSource` seam, and the drill-in detail view.
2. **The explorer** (4 phases, this trimmed scope): a compact per-cell **score blob** +
   **presets** in `index.json`; **markdown** (sanitized) + **collapsible** responses +
   **sans-serif** + a per-model **score header** in the drill-in; the
   **compare-by-divergence** view with URL view-state; and a **presets menu + intro/paper
   panel + light/dark** toggle.

(The scope traveled: an MVP "cell viewer" was elevated to an exploration vision, then
trimmed by the architect to exactly the requester's asks — no leaderboard, no versioned-
contract ceremony. This review reflects the final, trimmed result.)

## Spec Compliance

All trimmed-spec §9 criteria met (verified, incl. an end-to-end `vite preview` run on the
real 140-probe dataset):

- [x] **§9.1** `export-web` emits `index.json` (incl. the compact `scores` blob, `presets`,
  `paper`, per-subject `overall`) + gzip per-probe shards, via the existing loaders
  (v2 overlay + −1…+1 rescale). `CONTRACT.md` removed.
- [x] **§9.2** Intro panel explains the construct + controls and links the (draft) paper.
- [x] **§9.3** Compare: pick A+B → cells ranked by |score(A)−score(B)| desc; a row click
  opens the drill-in. Instant from the index, **no shard loads** (verified: `loadItem`
  not called in compare mode). Null-either cells excluded; declared-order tie-break;
  top-50 + show-more.
- [x] **§9.4** Drill-in renders both responses (markdown, sanitized; collapsible) + a
  per-model score header (`… initial → … post-pressure`, mean of 2 judges) + both judges'
  verdicts.
- [x] **§9.5** Presets menu offers the polarizing/models-split and judges-differed
  deep-links (12 each on the real data).
- [x] **§9.6** Every view (compare / detail / preset) is URL-encoded and restored;
  compare links are canonical.
- [x] **§9.7** No JaleesBench-specific strings in the types/components — axis values,
  band names, and the score-header scope labels all come from the data (the score-blob
  is consumed generically via `order`/`shape`).
- [x] **§9.8** Light/dark persisted (localStorage, `prefers-color-scheme` default);
  sans-serif; responsive.

## Deviations from Plan

- **Score-header wording in data, not code** (Phase 2 review): the export's scope labels
  carry `post-pressure`/`initial`, so the header reads them from `index.scopes` rather
  than hardcoding JaleesBench terms.
- **localStorage polyfill** (Phase 4): jsdom in this env provides no `window.localStorage`,
  so tests needed an in-memory polyfill (`vitest.setup.ts`) and the app uses a guarded
  `storage.ts` (also robust to private-mode/blocked storage in production).
- **gzip-serving robustness** (carried from the foundation): the `DataSource` decompresses
  a shard only when the bytes are still gzip (`0x1f 0x8b`), since some hosts apply
  `Content-Encoding: gzip` and pre-decompress.

## Lessons Learned

### What Went Well
- **Building on the foundation** paid off: the explorer was additive — the score blob +
  three view-surfaces reused the export, the `DataSource` seam, and the drill-in
  untouched in spirit.
- **Generic-in-types, specific-in-data** held all the way through: the compare ranking,
  the score header, and the presets are all axis-generic; JaleesBench specifics live in
  `index.json`. Reviewers used §9.6 as a real guardrail (caught two hardcoding slips).
- **The compact score matrix** makes overview/compare instant: the divergence ranking
  over 2,520 cells computes from the in-memory index with zero shard fetches.
- **`vite preview` before merge** repeatedly caught what unit tests couldn't — the gzip
  `Content-Encoding` double-decompress, and the real-data sanity of the divergence
  ranking (top cell Δ=2.00, ansari Perfume vs qwen Burns).

### Challenges Encountered
- **Scope churn** (MVP → elevated → trimmed): handled by rolling the protocol back to
  Specify and re-gating, keeping the foundation intact each time.
- **jsdom gaps** (no `localStorage`, no layout for `scrollHeight`/`matchMedia`): solved
  with a setup polyfill + stubs, and guarded production code.
- **Markdown safety**: `markdown-it` (`html:false`) + DOMPurify + a link-scheme allowlist;
  a `tel:`/`javascript:` test proves disallowed schemes are stripped.

### What Would Be Done Differently
- Pin the served data layout and measure export size during planning (both surfaced
  mid-implementation: the `data/probes/`→`probes/` cleanup and the gzip size decision).

### Methodology Improvements
- The per-phase 3-way review + rebuttal loop caught real bugs (NUL byte making a source
  file binary; lexical-vs-declared tie-break; non-canonical compare URLs). The Gemini
  consult sandbox intermittently saw an empty workspace (false "files missing") — worth a
  tooling note so builders don't chase phantoms.

## Architecture Updates

- **New explorer surfaces** in `apps/jaleesbrowser/`: a compare-by-divergence view, an
  intro/orient panel, a presets menu, and light/dark theming — on top of the existing
  drill-in. View state (`detail`/`compare`) is in the URL.
- **`index.json` now carries aggregate data**: a compact numbers-only `scores` blob
  (`{order, shape, data}`, subject×item×axes×scope → mean band), `presets` (curated
  deep-links), `paper`, and per-subject `overall` means — so the compare ranking is
  instant without shard loads. No versioned-contract ceremony; shapes are documented in
  the app README.
- **Removed** the formal `CONTRACT.md` and the version-bump/producer-config apparatus;
  the one retained "beyond JaleesBench" rule is that the UI/types stay generic.
- New client modules: `scores.ts` (blob reader + divergence), `markdown.ts` (sanitized
  render), `theme.ts` + `storage.ts`, and the `Compare`/`IntroPanel`/`Presets`/
  `ThemeToggle`/`Markdown`/`Collapsible` components.

## Lessons Learned Updates

- **A compact numeric "score matrix" in the catalog file** turns a per-item-shard viewer
  into an instant aggregate explorer (ranking/compare) for a few hundred KB — a reusable
  pattern when the heavy detail is sharded but cross-item views are wanted.
- **gzip-on-the-wire is host-dependent** (content vs `Content-Encoding`); detect the gzip
  magic byte and skip decompression when already plaintext.
- **jsdom lacks `localStorage`, layout (`scrollHeight`), and `matchMedia`**: polyfill
  `localStorage` in the Vitest setup, stub `scrollHeight`/`matchMedia` per test, and guard
  the production code so it degrades gracefully.
- **Keep product-specific words in the data**: even UI labels like "post-pressure" belong
  in the exported data (scope labels), not components, to honor a generic UI.

## Technical Debt

- **npm audit**: 5 advisories in dev-only build tooling (the runtime bundle is React +
  markdown-it + DOMPurify). Not auto-fixed to avoid `audit fix --force` breakage; revisit
  on a toolchain bump.
- **Committed data ~61 MB** (gzip), architect-approved; if it grows, finer sharding or a
  small backend remain options (localized by the `DataSource` seam).
- **Compare divergence is full-scope only**; a turn-1 toggle is a noted optional follow-up.

## Consultation Feedback

The (trimmed) spec, the light plan, and all four implement phases passed 3-way review
(Gemini / Codex / Claude). Notable accepted changes: producer-declared… (cut on trim);
score-header labels sourced from data; declared-order tie-break; canonical per-view URLs
+ top-50/show-more tests; the `localStorage` polyfill + guarded storage; and the gzip
serving + NUL-byte fixes carried from the foundation.

## Flaky Tests
None. Python suite (57) and the app suite (65) are deterministic; tests use small
committed fixtures / synthetic data and never the raw 190 MB results.
