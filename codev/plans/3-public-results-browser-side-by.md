# Implementation Plan: public-results-browser-side-by

## Metadata
- **ID**: plan-2026-06-17-public-results-browser
- **Status**: draft
- **Specification**: `codev/specs/3-public-results-browser-side-by.md`
- **Created**: 2026-06-17

## Executive Summary

Build the public results browser as the spec's recommended approach (spec §4.E): a
**TypeScript SPA** (React + Vite) at `apps/jaleesbrowser/`, fed by a **Python
`export-web` CLI** that emits a contract-shaped (spec §5) `index.json` + **per-probe
shards**, hosted **fully static on GitHub Pages**. The data contract is the seam: the
UI is generic over *subjects / items / condition axes / a band ladder / judges*, and
all JaleesBench specifics live in the exported data.

Work is split into five independently-committable phases, producer-first:

1. **Data layer** — the Python export + contract doc (defines the canonical shape).
2. **App scaffold + DataSource seam + contract types** — the app boots and loads the
   index through a thin data-source abstraction.
3. **Generic pickers + URL deep-link state** — selection UI driven from the index,
   round-tripped through the URL.
4. **Side-by-side comparison + verdicts + band legend** — the core UX.
5. **Static build, GitHub Pages deploy & real-data export** — ship it.

Each phase commits independently **on one branch**; per the issue's PR strategy, the
PR opens during/after the final implement phase (no per-phase PRs unless the architect
requests one).

## Open Decisions for plan-approval (recommendations, NOT mandates)

Presented like the spec's §4 open decisions — the requester decides at plan-approval;
the plan proceeds on the recommended path so the phases are concrete, and notes the
fallback if a decision is redirected.

### D1 — Thin client-side DataSource seam (architect-raised) — RECOMMENDED

Introduce a **thin data-source interface** the UI depends on:

```ts
interface DataSource {
  loadIndex(): Promise<ContractIndex>;
  loadItem(itemId: string): Promise<ItemShard>;
}
```

with a **single implementation now** — `StaticFileDataSource` (fetches `index.json`
and `data/<shard>` over HTTP). The UI never calls `fetch` directly; it depends only on
the interface. **Build ONLY the seam + the static-file impl. Do NOT build a DB adapter,
API client, or query layer now (YAGNI).** A future DB/API-backed source becomes a
localized drop-in (one new class implementing the same two methods) without touching
the UI. **Recommendation: adopt the seam.** Cost is ~one small interface + one class;
benefit is that the spec §4.B "backend stays on the table" option becomes a contained
change rather than a UI rewrite. *Fallback if redirected:* the UI calls a couple of
fetch helpers directly (Phase 2 shrinks slightly).

### D2 — Stack assumptions carried from spec §4 (confirm or redirect)

The spec recommended, and this plan assumes: **React + Vite + TS** (D-A1), **static
on GitHub Pages** (D-B1), **per-probe shards** (D-C1), **Python `export-web` CLI**
reusing the loaders (D-D1). These were recommendations, not decisions — confirm at
plan-approval. Redirecting any of them changes the corresponding phase(s) but not the
data contract (spec §5) or the fixed requirements (spec §3).

### D3 — Shard cell encoding (plan-level, spec §7 I2/I5)

**Recommendation:** each shard stores a flat `cells` array; the client indexes it by
`(subject, conditions)` into a Map on load. Keep full transcripts inline (no
prompt-dedup) unless the measured export size (spec §7 C1) is uncomfortable — dedup
stays an easy follow-up since it is internal to the export + DataSource.

## Success Metrics

Validates against spec §9. Phase-mapped:

- [ ] Export produces contract-conforming `index.json` + per-probe shards using the
      existing loaders incl. `judgments_v2` overlay and −1…+1 rescale (§9.1) — Phase 1.
- [ ] Viewer lets the user pick question + two models + pressure + framing and renders
      both two-turn transcripts side by side (§9.2) — Phases 3–4.
- [ ] Both judges' verdicts (band + label + rationale/summary) per side, default
      post-pressure scope, tolerant of missing rationale (§9.3) — Phase 4.
- [ ] Full selection encoded in URL; paste reproduces the view (§9.4) — Phase 3.
- [ ] Public, zero-install, no backend; static bundle deployable to GitHub Pages at
      the project path (§9.5) — Phase 5.
- [ ] No JaleesBench-specific strings in types/components — all from data (§9.6) — all
      app phases; verified in Phase 4 review.
- [ ] Fail-soft on missing cells / bad URL params / bad data assets (§9.7) — Phases 3–4.
- [ ] Band legend from data; CONTRACT.md; `--results-path`; responsive/RTL/a11y;
      security/escaped text (§9.8–§9.11, §9.15) — Phases 1, 4.
- [ ] Lazy per-probe loading; deterministic export; no secrets/raw-jsonl committed
      (§9.12–§9.14) — Phases 1–2, 5.

## Phases (Machine Readable)

<!-- REQUIRED: porch uses this JSON to track phase progress. Update when adding/removing phases. -->

```json
{
  "phases": [
    {"id": "phase_1_export", "title": "Data contract + Python export CLI"},
    {"id": "phase_2_scaffold", "title": "App scaffold, contract types & DataSource seam"},
    {"id": "phase_3_pickers_url", "title": "Generic pickers + URL deep-link state"},
    {"id": "phase_4_compare", "title": "Side-by-side comparison, verdicts & band legend"},
    {"id": "phase_5_deploy", "title": "Static build, GitHub Pages deploy & real-data export"}
  ]
}
```

## Phase Breakdown

### Phase 1: Data contract + Python export CLI
**Dependencies**: None

#### Objectives
- Produce the canonical, contract-shaped dataset (spec §5) from the existing results,
  reusing the battle-tested loaders (v2 overlay + −1…+1 rescale).
- Document the contract so the app (and future producers) have a fixed target.

#### Files
- `jaleesbench/jaleesbench/export_web.py` (new) — the exporter.
- `jaleesbench/jaleesbench/cli.py` (edit) — add `export-web` Typer command
  (`--results-path`, `--out`, `--limit`).
- `jaleesbench/jaleesbench/score.py` (edit) — thread an optional `results_path` into
  `load()` / `load_judgments()` (default keeps the module-level `RESULTS`).
- `jaleesbench/jaleesbench/collect.py` (edit) — allow `load_probes()` + a results-path
  helper so the exporter reads the right dirs (probes come from bundled `DATA`,
  transcripts/judgments from `--results-path`).
- `jaleesbench/tests/test_export_web.py` (new) — schema-shape + semantics tests.
- `apps/jaleesbrowser/CONTRACT.md` (new) — the versioned contract reference.

#### Implementation Details
- `export_web(results_path, out_dir, limit=None)`:
  - Load sittings (`collect.jsonl`), judgments (overlaid via `load_judgments`), probes
    (`load_probes`). Derive `subjects` from the data present (8 main subjects);
    `conditionAxes` = `pressure` (6) + `framing` (3); `judges` (2); `scopes` =
    `full` (default) + `turn1`; `bands` = the −1…+1 ladder with labels + colors from
    `BAND_NAMES` / the report palette.
  - Write `index.json`: `contractVersion "1.0"`, `producer`, `dataset {title,
    description, language:"en"}`, `bands`, `subjects`, `conditionAxes`, `judges`,
    `scopes`, `items[{id,title,tags:{chapter,pillars,hearts,islamic}}]`, `shards`.
  - Write one shard per probe `data/probes/<id>.json`: `item{id,title,tags,context?}`
    + `cells[]` (subject, conditions, transcript[turns], verdicts[{judge,scope,band
    (display),bandLabel,summary←direction,rationale?,tags:{techniques}}]).
  - **Slim**: drop `usage`/`raw`/`attempts`/`context_prefix`. Deterministic ordering
    (sorted keys) so re-runs are idempotent.
- `--results-path` defaults to the package `results/`; for the real run it points at
  the main checkout (`/Users/mwk/Development/fftn/taqwabench/jaleesbench/results`)
  whose data is gitignored and absent from the worktree.

#### Acceptance Criteria
- [ ] `jaleesbench export-web --results-path <dir> --out <dir> --limit 2` writes a
      valid `index.json` + 2 shards.
- [ ] A v2-overlaid judgment (no `rationale`) exports without error (rationale omitted).
- [ ] Bands are on the display scale (−1…+1); a known cell matches the report.
- [ ] Loaders still work with no path arg (defaults unchanged) — no regression.
- [ ] CONTRACT.md documents every `index.json` + shard field and the version rule.

#### Test Plan
- **Unit**: export a 1–2 probe subset from a tiny synthetic results fixture; assert
  index/shard shapes, band rescale, v2 missing-rationale tolerance, idempotent output.
- **Manual**: run against real results; eyeball one shard vs the report.

#### Rollback Strategy
New module + additive CLI command + backward-compatible loader params; revert the
commit.

#### Risks
- **Risk**: loader refactor regresses the report. **Mitigation**: optional param with
  unchanged default; run `jaleesbench report` smoke once.
- **Risk**: export size larger than the ~10–30 MB estimate. **Mitigation**: measure in
  Phase 5; prompt-dedup (D3) available as a contained follow-up.

---

### Phase 2: App scaffold, contract types & DataSource seam
**Dependencies**: Phase 1 (canonical shape + a committed mini-fixture)

#### Objectives
- Stand up the Vite + React + TS app at `apps/jaleesbrowser/`.
- Encode the contract as TS types and introduce the **DataSource seam** (D1) with the
  static-file impl as the only implementation.
- Boot the app, load the index via the DataSource, render a minimal smoke view.

#### Files
- `apps/jaleesbrowser/package.json`, `vite.config.ts`, `tsconfig.json`, `index.html`,
  `.gitignore` (new) — scaffold (Vite `base` build-configurable, relative asset paths).
- `apps/jaleesbrowser/src/main.tsx`, `src/App.tsx` (new) — entry + minimal shell.
- `apps/jaleesbrowser/src/contract.ts` (new) — TS types for index + shard (generic:
  no JaleesBench string literals).
- `apps/jaleesbrowser/src/datasource.ts` (new) — `DataSource` interface +
  `StaticFileDataSource` (fetch + JSON parse + version check). **No DB/API/query layer.**
- `apps/jaleesbrowser/src/datasource.test.ts` (new) — unit tests against a fixture.
- `apps/jaleesbrowser/public/data/` (new) — committed **mini-fixture** (1–2 probes)
  produced by Phase 1's exporter, for dev + tests.

#### Implementation Details
- Vitest as the test runner (ships with the Vite ecosystem).
- `StaticFileDataSource(baseUrl)` resolves `index.json` and shard paths relative to the
  app base; checks `contractVersion` MAJOR and throws a typed `UnsupportedVersionError`
  the UI renders fail-soft (Phase 3/4).
- `contract.ts` types mirror spec §5 exactly and are the only place the shard/index
  shapes are named.

#### Acceptance Criteria
- [ ] `npm install && npm run dev` boots; app fetches the fixture index via the
      DataSource and shows counts (e.g. "N questions · M subjects").
- [ ] `npm run build` produces a static bundle; `npm test` passes.
- [ ] UI code imports only `DataSource` (no direct `fetch`).

#### Test Plan
- **Unit**: `StaticFileDataSource.loadIndex/loadItem` against the fixture; version-
  mismatch throws; malformed JSON rejects.
- **Manual**: dev server shows the smoke view.

#### Rollback Strategy
Self-contained new directory; revert the commit (no changes outside `apps/`).

#### Risks
- **Risk**: Node/TS toolchain noise in a Python repo. **Mitigation**: confined to
  `apps/jaleesbrowser/`; `.gitignore` excludes `node_modules`/`dist`.

---

### Phase 3: Generic pickers + URL deep-link state
**Dependencies**: Phase 2

#### Objectives
- Build the selection UI generically from the index (question, model A, model B, one
  selector per `conditionAxes`, scope toggle).
- Encode the full selection in the URL and restore it on load; fail soft on bad params.

#### Files
- `apps/jaleesbrowser/src/urlstate.ts` (new) + `urlstate.test.ts` (new) — encode/decode
  `{item, a, b, <axisKey>…, scope}` ↔ query string; generic over axes.
- `apps/jaleesbrowser/src/components/Pickers.tsx` (new) — the selectors.
- `apps/jaleesbrowser/src/App.tsx` (edit) — wire pickers ⇄ URL; compute defaults.

#### Implementation Details
- Defaults when params absent: first item, first two *distinct* subjects, each axis's
  default/first value, default scope. Same-subject A=B permitted.
- Unknown/invalid param values fall back to defaults without crashing (spec §6/§5.6).
- URL updates via `history.replaceState`; axis params read by iterating
  `index.conditionAxes` (no hardcoded "pressure"/"framing").

#### Acceptance Criteria
- [ ] Changing any picker updates the URL; reloading restores the exact selection.
- [ ] A crafted URL with a bad probe id / unknown subject / unknown axis value loads
      defaults, no crash.
- [ ] Selectors are rendered purely from index metadata (no literal axis/band strings).

#### Test Plan
- **Unit**: `urlstate` round-trip (state→query→state) incl. extra/missing/invalid
  params; default derivation.
- **Manual**: paste a deep link → exact view.

#### Rollback Strategy
Revert the commit; Phase 2 smoke view remains.

#### Risks
- **Risk**: axis-generic URL encoding edge cases. **Mitigation**: round-trip property
  tests over the fixture's axes.

---

### Phase 4: Side-by-side comparison, verdicts & band legend
**Dependencies**: Phase 3

#### Objectives
- The core UX: lazy-load the selected probe's shard via the DataSource and render the
  two models' two-turn transcripts side by side with both judges' verdicts.
- Band legend from the data; escaped text; responsive/RTL/a11y; fail-soft states.

#### Files
- `apps/jaleesbrowser/src/components/Comparison.tsx`, `Transcript.tsx`,
  `Verdicts.tsx`, `BandLegend.tsx` (new).
- `apps/jaleesbrowser/src/format.ts` (new) + `format.test.ts` — band lookup (value→
  label/color, positional fallback), cell indexing by `(subject, conditions)`.
- `apps/jaleesbrowser/src/App.tsx` (edit) — wire the comparison panel + shard cache.
- `apps/jaleesbrowser/src/styles.css` (new) — layout incl. responsive stacking.

#### Implementation Details
- Lazy-fetch shard on item change (cache by item id). Index `cells` into a Map.
- Each column: the 4 turns (user/assistant delineated); shared user turns identical by
  construction. Below: per judge a band chip (color from `index.bands`, positional
  fallback) + label (e.g. "Perfume +1") + summary/rationale; default `full` scope,
  toggle to `turn1`; tolerate missing rationale.
- **Security**: all producer text rendered as escaped plain text (React default;
  `dangerouslySetInnerHTML` prohibited); line breaks via CSS `white-space`.
- **a11y/RTL**: band meaning by label not color alone; keyboard-navigable; `dir` from
  `dataset.language`. Missing cell → "no data for this combination".
- Responsive: side-by-side on desktop, stacked/tabbed on narrow viewports.

#### Acceptance Criteria
- [ ] Selecting a question + two models + pressure + framing renders both transcripts
      + both judges' verdicts.
- [ ] A polarizing cell (e.g. JLS-006: one side +1, other −1) shows opposed bands.
- [ ] A v2 verdict (no rationale) renders without error.
- [ ] Producer text containing `<script>` / `**bold**` renders as literal text.
- [ ] Missing cell and unsupported `contractVersion` show fail-soft states.

#### Test Plan
- **Unit**: `format` band lookup + fallback; cell indexing.
- **Component**: render Comparison against fixture shard — polarizing cell, missing
  rationale, XSS-literal, missing cell.
- **Manual**: walk several real cells in dev.

#### Rollback Strategy
Revert the commit; Phases 2–3 remain functional (pickers + URL, no panel).

#### Risks
- **Risk**: accidental JaleesBench hardcoding in components. **Mitigation**: success
  criterion §9.6 is a review checklist item; grep for literal axis/band strings.

---

### Phase 5: Static build, GitHub Pages deploy & real-data export
**Dependencies**: Phase 4 (assuming D2 static+Pages is confirmed)

#### Objectives
- Produce the real committed dataset and ship the app publicly with no backend.

#### Files
- `.github/workflows/pages.yml` (new) — build `apps/jaleesbrowser/` and deploy to
  Pages (builds the committed app + data; does **not** regenerate the export).
- `apps/jaleesbrowser/README.md` (new) — how to export data, dev, build, deploy.
- `apps/jaleesbrowser/public/data/*` (replace fixture with the **full English export**)
  — committed slimmed data (raw results stay gitignored).
- `apps/jaleesbrowser/vite.config.ts` (edit) — finalize `base` for the Pages path.

#### Implementation Details
- Run `jaleesbench export-web --results-path <main-checkout results> --out
  apps/jaleesbrowser/public/data` locally (raw data isn't in CI); commit the output.
- Measure committed size; if uncomfortable vs spec §7 C1, apply D3 prompt-dedup.
- Actions workflow: `npm ci && npm run build` then `actions/deploy-pages`. Confirm Pages
  base path matches the repo (`/jaleesbench/`).

#### Acceptance Criteria
- [ ] `npm run build` succeeds with the production base path; assets load via relative
      paths.
- [ ] Committed `data/` is the full English set; no raw `.jsonl`, no secrets,
      no `.vertex-sa.json`.
- [ ] Workflow is valid; a deploy publishes a browsable site (verified post-merge in
      the verify phase).
- [ ] README documents the end-to-end reproduce steps.

#### Test Plan
- **Manual**: production build + local `vite preview` at the base path; click through
  deep links. Validate the workflow YAML.
- **Post-merge**: confirm the live Pages URL in the verify phase.

#### Rollback Strategy
Revert the workflow + data commit; the app still builds/runs locally.

#### Risks
- **Risk**: Pages base-path mismatch → broken asset URLs. **Mitigation**: relative
  paths (spec §5.7) + `vite preview` at the base before merge.
- **Risk**: committed data bloats the repo. **Mitigation**: slim export + size check +
  optional dedup.
- **Risk**: D2 redirected to a non-Pages host/backend. **Mitigation**: Phase 5 is the
  only host-specific phase; only this phase changes.

## Dependency Map
```
Phase 1 (export) ──→ Phase 2 (scaffold+seam) ──→ Phase 3 (pickers+URL) ──→ Phase 4 (compare) ──→ Phase 5 (deploy)
```
Strictly linear: each phase builds on the previous. Phase 1 also feeds the committed
mini-fixture that Phases 2–4 test against; Phase 5 swaps in the full export.

## Risk Analysis

### Technical Risks
| Risk | Probability | Impact | Mitigation |
|------|------------|--------|------------|
| Loader refactor regresses the report | L | M | Optional param, unchanged default, report smoke |
| JaleesBench specifics leak into UI/types | M | M | §9.6 review check; grep literals; types in `contract.ts` only |
| Export size > estimate | M | L | Measure Phase 5; D3 prompt-dedup follow-up |
| Pages base-path asset breakage | M | M | Relative paths (§5.7) + `vite preview` pre-merge |
| Toolchain friction (Node in Python repo) | L | L | Confined to `apps/jaleesbrowser/`; gitignored build artifacts |

### Process Risks
- **D1/D2 redirected at plan-approval**: the DataSource seam (D1) localizes any
  backend change to one class; the host decision (D2) is isolated to Phase 5. Either
  redirect touches few phases.

## Testing Strategy
- **Python**: pytest schema-shape + semantics tests for the export (Phase 1).
- **TS**: Vitest unit tests for DataSource, urlstate, format; component tests for the
  comparison panel against a committed fixture (Phases 2–4).
- **Manual/integration**: dev walk-throughs + a production `vite preview` at the base
  path; live Pages check in the verify phase.
- All test data is a small committed fixture — the suite never needs the 190 MB raw
  results, so it runs in CI.
