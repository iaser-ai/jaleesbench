# Implementation Plan: public-results-browser-side-by (trimmed)

## Metadata
- **ID**: plan-2026-06-18-results-explorer-trimmed
- **Status**: draft
- **Specification**: `codev/specs/3-public-results-browser-side-by.md`
- **Created**: 2026-06-18

## Executive Summary

Additive work **on the existing foundation** (the MVP drill-in viewer + `export-web` CLI
are already implemented and committed on this branch). Per the trimmed spec, add: a
compact per-cell **score blob** + **presets** in `index.json` (and remove `CONTRACT.md` /
the contract ceremony); **markdown + collapsible + sans-serif + a per-model score
header** in the drill-in; a **compare-by-divergence** view with URL view-state; and a
**presets menu + intro/paper panel + light/dark** toggle.

Four focused, independently-committable phases on the existing branch (single PR #4):

```json
{
  "phases": [
    {"id": "phase_1_scores_presets", "title": "Export: per-cell score blob + presets + paper; remove CONTRACT.md"},
    {"id": "phase_2_drillin_polish", "title": "Drill-in: markdown + collapsible + sans-serif + score header"},
    {"id": "phase_3_compare_view", "title": "Compare-by-divergence view + URL view-state"},
    {"id": "phase_4_presets_intro_theme", "title": "Presets menu + intro/paper panel + light/dark"}
  ]
}
```

## Success Metrics
Validates spec §9. Mapped: §9.1 → Phase 1; §9.2,§9.5 (intro/presets) → Phase 4;
§9.3 (compare) → Phase 3; §9.4 (drill-in polish + score header) → Phase 2; §9.6 (URL
every view) → Phases 3–4; §9.7 (no hardcoded strings) → all; §9.8 (theme/sans-serif) →
Phase 4.

## Notes carried from the foundation
- `apps/jaleesbrowser/` exists (Vite + React + TS, `DataSource` seam, drill-in
  `Comparison`/`Verdicts`/`BandLegend`/`ItemHeader`, `Pickers`, `urlstate`, `format`).
- `jaleesbench export-web` exists; loaders take `--results-path`.
- Keep `contractVersion` at `"1.0"` (no bump); the existing `DataSource` version check
  stays (lenient). No formal contract doc.

---

### Phase 1: Export — per-cell score blob + presets + paper; remove CONTRACT.md
**Dependencies**: none (extends `export_web.py`)

#### Objectives
Add the data the compare view + presets + score header need, as plain numbers; drop the
contract ceremony.

#### Files
- `jaleesbench/jaleesbench/export_web.py` (edit) — emit into `index.json`: `scores`
  (`{order, shape, data}` flat row-major mean band per subject×item×pressure×framing×
  scope, `null` if absent), `presets` (polarizing/models-poorly + judges-differed,
  §4.4/§5.5 semantics, deterministic, **empty sets omitted**), `paper`
  (`{url, label, draft:true}`), and per-subject `overall` means. Keep
  `contractVersion "1.0"`. **Clean stale "versioned contract" / `CONTRACT.md` wording**
  from the module + function docstrings/comments.
- `apps/jaleesbrowser/src/contract.ts` (edit) — extend `ContractIndex` with typed
  `scores`, `presets`, `paper`, and `subjects[].overall` (so Phases 2–4 have typed
  access; avoids shape drift). These are plain optional fields (no schema ceremony).
- `jaleesbench/tests/test_export_web.py` (edit) — assert the `scores` blob shape/values
  (incl. a `null`), preset structure + determinism + empty-omission, `paper` field.
- `apps/jaleesbrowser/CONTRACT.md` (**delete**); fold a short "data format" note into
  `apps/jaleesbrowser/README.md` (edit).
- Regenerate `apps/jaleesbrowser/public/data/` (full export with the new fields).

#### Acceptance / Tests
- [ ] `scores.data` length = product(shape); a known cell's value = mean of its judge
      bands (display scale); missing cell → `null`.
- [ ] `presets` has both sets; entries are deep-link param maps; re-run is byte-identical.
- [ ] `paper.url` points at the repo PDF (GitHub blob URL), `draft: true`.
- [ ] Python suite green; no `CONTRACT.md`.

---

### Phase 2: Drill-in — markdown + collapsible + sans-serif + score header
**Dependencies**: Phase 1 (score blob for the header)

#### Files
- `apps/jaleesbrowser/package.json` (edit) — add `markdown-it` + `dompurify` (+ types).
- `apps/jaleesbrowser/src/markdown.ts` (new) + `markdown.test.ts` — `renderMarkdown`:
  `markdown-it({html:false, linkify:true})` → DOMPurify sanitize; link scheme allowlist
  (`http`/`https`/`mailto`), strip `javascript:`, external `rel=noopener target=_blank`.
- `apps/jaleesbrowser/src/components/Markdown.tsx` (new) — renders sanitized markdown.
- `apps/jaleesbrowser/src/components/Collapsible.tsx` (new) + test — clamps to ~10 lines,
  expand/collapse toggle when content overflows.
- `apps/jaleesbrowser/src/components/Comparison.tsx` (edit) — transcript turns via
  `Markdown` + `Collapsible`; **per-model score header** computed **from the shard's
  verdicts** (mean of the 2 judges at turn-1 / full — the `scores` blob reader arrives in
  Phase 3; the drill-in already has the verdicts), e.g.
  `glm-5.1 (+0.75 initial → +0.5 post-pressure)`.
- `apps/jaleesbrowser/src/components/Verdicts.tsx` (edit) — rationale/summary via
  `Markdown` + `Collapsible`.
- `apps/jaleesbrowser/src/styles.css` (edit) — sans-serif throughout; collapsible/score-
  header styles.

#### Acceptance / Tests
- [ ] `**bold**` renders as markdown; literal `<script>` inert; `javascript:` link
      stripped; `https`/`mailto` allowed (markdown.test).
- [ ] Long content collapses to ~10 lines with a working expand/collapse (Collapsible.test).
- [ ] Score header shows `… (+x initial → +y post-pressure)` from the data (component test).
- [ ] Build + app tests green; font is sans-serif.

---

### Phase 3: Compare-by-divergence view + URL view-state
**Dependencies**: Phases 1–2

#### Files
- `apps/jaleesbrowser/src/scores.ts` (new) + test — read the `scores` blob generically
  (offset from `order`/`shape`); `divergenceRanking(index, a, b)` → cells sorted by
  `|score(A)−score(B)|` desc at the default scope, null-either excluded, tie-break
  item/condition.
- `apps/jaleesbrowser/src/urlstate.ts` (edit) + test — a `view` param (`detail` |
  `compare`); encode/decode per-view state; default landing `detail`; an unknown/invalid
  `view` falls back to `detail`.
- `apps/jaleesbrowser/src/components/Compare.tsx` (new) + test — A/B pickers + the ranked
  list (question, condition, both scores), **top-N = 50 with a "show more"** (spec §5.3/
  I1); a row click → `view=detail` for that cell.
- `apps/jaleesbrowser/src/App.tsx` (edit) — render `detail` vs `compare` by `view`; mode
  toggle; wire row-click navigation. **Gate the shard-load effect to `view==='detail'`**
  so compare never fetches a shard (spec: compare is instant from `index.json`).

#### Acceptance / Tests
- [ ] `divergenceRanking` orders by |Δ| desc, excludes null-either cells, deterministic
      tie-break, top-N + show-more (unit).
- [ ] `?view=compare&a=..&b=..` restores the compare view; an invalid `view` → detail; a
      row click deep-links to `view=detail`; round-trip (test).
- [ ] Compare renders instantly from the index — **no shard fetch in compare mode**
      (assert the DataSource `loadItem` is not called; the shard-load effect is gated to
      detail).

---

### Phase 4: Presets menu + intro/paper panel + light/dark
**Dependencies**: Phase 3

#### Files
- `apps/jaleesbrowser/src/components/IntroPanel.tsx` (new) + test — the construct +
  controls explanation; **paper link** (draft); collapsible, first-visit-open via
  `localStorage`.
- `apps/jaleesbrowser/src/components/Presets.tsx` (new) + test — menu from
  `index.presets`; selecting an entry applies its params (via the URL decoder).
- `apps/jaleesbrowser/src/theme.ts` (new) + test — light/dark state, persisted
  (`localStorage`), default `prefers-color-scheme` (guard `matchMedia` for jsdom);
  applies `data-theme`.
- `apps/jaleesbrowser/src/components/ThemeToggle.tsx` (new) — the toggle button.
- `apps/jaleesbrowser/src/App.tsx` (edit) — mount Intro + Presets + ThemeToggle.
- `apps/jaleesbrowser/src/styles.css` (edit) — light/dark CSS variables; intro/presets.

#### Acceptance / Tests
- [ ] Intro renders + links the (draft) paper; collapses; first-visit persistence.
- [ ] Presets menu lists both sets; selecting applies the deep-link.
- [ ] Theme toggles, persists to `localStorage`, defaults from `prefers-color-scheme`;
      `matchMedia` absent → light, no crash.
- [ ] Build + app tests green; production `vite preview` sanity (incl. gzip serving).

---

## Risk Analysis
| Risk | Mit |
|---|---|
| Markdown XSS | markdown-it `html:false` + DOMPurify + scheme allowlist; tested |
| `matchMedia`/`DecompressionStream` absent in jsdom | optional-chain / Node provides them; guarded + tested |
| Score-blob size in index.json | ~250 KB plain (gzipped on wire); acceptable one-time load |
| Hardcoded JaleesBench strings creep in | values read from data; review check |

## Testing Strategy
Python: pytest for the export (blob/presets/paper). TS: Vitest unit (markdown, scores/
divergence, urlstate `view`, theme) + component tests (Collapsible, Compare, Presets,
Intro, score header) against committed fixture/synthetic data. Manual: `vite preview`
walk-through incl. gzip serving. No test needs the raw 190 MB data.
