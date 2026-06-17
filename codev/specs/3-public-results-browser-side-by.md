# Spec 3 — Public results browser: side-by-side model comparison, URL-shareable

**Status:** Draft (Specify phase)
**Issue:** #3
**Protocol:** SPIR

## 1. Overview / Problem

JaleesBench has produced a large, rich result set — 20,160 two-turn "sittings"
(8 subject models × 6 pressures × 3 framings × 140 probes) and 80,640 judge
verdicts (2 judges × 2 scopes per sitting). Today the only way to read it is the
generated aggregate report (`report.html`) plus the raw `.jsonl` files, which are
gitignored and far too large (190 MB `collect.jsonl`) for anyone outside the team
to open.

There is no way for an outside reader — a scholar, a journalist, a curious
practitioner — to **drill into a specific scenario** and see, with their own eyes,
how two models actually answered the same question under the same pressure, and how
the judges scored each. The headline numbers (e.g. "Ansari +0.48, qwen −0.48") are
only credible if the underlying transcripts are inspectable.

**We want a public, shareable web app** for browsing the results so anyone can dig
in directly: pick a question, pick two models, pick a pressure + framing, and see
the two conversations and the judge verdicts side by side — with every view encoded
in the URL so any cell is a shareable deep link.

### Current state → desired state

| | Current | Desired |
|---|---|---|
| Access | Aggregate report + gitignored 190 MB jsonl | Public web app, no install |
| Granularity | Per-subject / per-probe summary tables | Any single cell: 2 models side by side |
| Sharing | "open the html" | URL deep-link to an exact comparison |
| Hosting | Local file | GitHub Pages on the public repo |
| Scope | English + Arabic + experiments | **English only** (per issue) |

## 2. Stakeholders

- **Outside readers** (scholars, reviewers, journalists, practitioners): the
  primary audience. Must be able to verify claims by reading real transcripts.
- **The JaleesBench authors** (Waleed, Ben, Tim): need a credible companion to the
  paper/report; "don't take our word for it, read it yourself."
- **The architect** (this workspace): owns the data-contract requirement (§5).
- **Future producers**: other benchmarks that adopt the same export format and want
  to reuse the viewer (enabled by the data contract; not built out now).

## 3. Constraints

### 3.1 Baked Decisions (from the issue + architect; treat as fixed)

From the **issue body** (recommended approach, confirmed):

1. **Read-only over exported JSON.** The viewer never touches harness data; do not
   modify `collect.jsonl` / `judgments.jsonl` / `judgments_v2.jsonl`.
2. **No backend.** Public, free, static hosting on **GitHub Pages** on this repo
   (`iaser-ai/jaleesbench`, already public).
3. **A TypeScript app** that builds to a **static bundle** (satisfies "a TS
   application" + "static hosting", no server). Recommended: **Vite + React + TS**.
4. **A Python data-export step** that reuses the loaders in `score.py` /
   `html_report.py` (including the `judgments_v2` overlay and the band→−1…+1
   rescale) and writes `index.json` + one JSON shard per probe, loaded on demand.
5. **App in a top-level dir** (`web/`); export is a **reproducible CLI step**.
6. **Bands map to −1…+1** per the existing `score.py` convention (SCORE_SCALE=0.5).
7. **English results only for now**; Arabic excluded until its judging run
   completes. (Arabic must not be hard-excluded by design — see §5.)

From the **architect** (KEY SPEC REQUIREMENT, baked):

8. **Data-contract-driven, not JaleesBench-hardcoded.** The viewer must be driven
   by a documented, versioned **data contract** (the exported index + per-probe
   schema), with JaleesBench as the **first producer** of that format. The viewer
   must be able to render any results JSON conforming to the JaleesBench format or a
   derivative, and (future) let a user load their own JSON. **Keep it simple:** build
   the clean data-contract seam and ship JaleesBench-first; do **not** over-engineer
   a fully generic schema engine before it's needed, but do **not** bake JaleesBench
   specifics (band names, "pressure"/"framing", probe fields) into the UI or the TS
   types. This is detailed in §5 and reviewed at spec-approval.

### 3.2 Other constraints

- **Repository hygiene** (project CLAUDE.md): never `git add -A`/`.`; commit
  messages `[Spec 3] …`; scores reported on −1…+1; no attribution lines.
- **Raw data is gitignored and lives in the main checkout** (`jaleesbench/results/`),
  not in the builder worktree. The export must accept a **`--results-path`** (default:
  the package's `results/`) so it can be pointed at the real data. The existing
  loaders in `score.py`/`collect.py` are currently bound to the module-level
  `RESULTS` constant; the **small refactor to thread a results path through `load()`
  / `load_judgments()` / `load_probes()` is in scope** for this work.
- **`web/` lives at the repository root** (alongside `jaleesbench/`), not inside the
  Python package. The GitHub Actions workflow builds from `web/`.
- **Subject set:** the export reads `collect.jsonl`, which contains exactly the **8
  main subjects**. The 3 thinking-mode arms live in a separate file
  (`collect_thinking.jsonl`) and the ansari-steadfast / Arabic arms in their own files;
  all are out of scope. The export derives its subject list from the data present
  rather than a hardcoded list.
- **No new harness behavior**: this spec adds a viewer + an export command; it does
  not change collection, judging, or scoring.

## 4. Solution Exploration

### 4.1 Chosen approach: Vite + React + TS static app + Python export (RECOMMENDED)

- **Export (Python CLI):** `jaleesbench export-web` reads the results via the
  existing `score.py` loaders (`load()`, `load_judgments()` with the v2 overlay,
  `load_probes()`), applies the −1…+1 band rescale, and writes a **contract-shaped**
  dataset: a small `index.json` (catalog) + one shard per probe. Output goes to a
  directory the viewer serves as static assets.
- **Viewer (TS app):** a Vite + React + TypeScript SPA. On load it fetches
  `index.json` to populate the pickers (question, two subjects, one selector per
  condition axis). On selection it lazy-fetches the relevant per-probe shard, locates
  the two cells, and renders the two transcripts + the judge verdicts side by side.
  The full selection lives in the URL query string (deep-linkable).
- **Hosting:** GitHub Pages via a GitHub Actions workflow that builds `web/` and
  deploys. Vite `base` set to `/jaleesbench/` (project Pages path).

**Pros:** satisfies every baked decision; clean separation (Python owns data, TS
owns presentation); the contract seam is a natural artifact of the export. **Cons:**
adds a Node/TS toolchain to a Python repo; exported data must be committed (see §7
Open Questions, resolved recommendation: commit the slimmed export, keep raw
ignored).

### 4.2 Alternative A: server-rendered / API backend — REJECTED

A small backend (FastAPI) serving query results would avoid shipping JSON. Rejected:
violates "no backend / free static hosting" (baked decision 2) and adds ops burden.

### 4.3 Alternative B: single monolithic JSON — REJECTED

Export everything into one `data.json`. Rejected: the full English set is large; a
single file makes initial load heavy and defeats the "loaded on demand so initial
load stays small" requirement. Per-probe shards keep the index tiny.

### 4.4 Alternative C: plain static HTML generator (no TS app) — REJECTED

Extend `html_report.py` to emit a static comparison page per cell. Rejected: does not
satisfy "a TypeScript application", and pre-rendering every (probe × subject-pair ×
pressure × framing) cell is a combinatorial explosion; client-side selection is far
simpler and is what makes URL-state sharing natural.

## 5. Data Contract & Extensibility (KEY SECTION — architect requirement)

The viewer is a function of a **documented, versioned data contract**, not of
JaleesBench. JaleesBench is the **first producer**. This section defines the contract
at the level of WHAT (the plan will finalize exact field encodings).

### 5.1 Design principle

**Generic in the types/UI, specific in the data.** The TypeScript types and React
components know about abstract concepts — *subjects*, *items*, *condition axes*,
*transcripts*, *judges*, *a band scale*. They do **not** know the strings "pressure",
"framing", "Burns", "Perfume", "ghiba", or the probe field names. Every
JaleesBench-specific value is carried **in the exported data** (`index.json`), so a
different producer emitting the same shapes — with different axes, bands, or item
metadata — renders without code changes. We build exactly this seam and no more: no
plugin system, no schema-validation engine, no per-producer code paths.

### 5.2 The contract (two artifacts)

**(a) `index.json` — the catalog / manifest.** Small; loaded once on startup.
Declares the dataset and everything the pickers need:

- `contractVersion` — string (e.g. `"1.0"`); the viewer checks the major version.
- `producer` — `{ name, version }` (e.g. `{ "name": "jaleesbench", "version": "…" }`).
- `dataset` — display metadata: `{ title, description, language }`. `language` is a
  BCP-47-ish tag (e.g. `"en"`, `"ar"`); the viewer sets text direction (LTR/RTL) from
  it so a future Arabic dataset lays out correctly with no code change.
- `bands` — the **ordered band ladder** on the display scale, e.g.
  `[{ value: -1, label: "Burns", color: "#a02020" }, { value: -0.5, label: "Sparks" },
  { value: 0, label: "Inert", color: "#666" }, { value: 0.5, label: "Scent" },
  { value: 1, label: "Perfume", color: "#1a6840" }]`. The viewer renders/colors bands
  **purely from this list** — each band may carry an optional `color` (the producer
  supplies the palette, keeping the UI generic). When `color` is absent, the viewer
  derives a neutral positional ramp from each band's ordinal position, so styling
  never requires JaleesBench-specific code. (Optional per-band `description` for
  tooltips.) Band labels carry the meaning so color is never the sole differentiator.
- `subjects` — `[{ id, label }]`: the comparable models. The two model pickers are
  populated from this.
- `conditionAxes` — **the generic seam for pressure + framing.** An **ordered list of
  axes**, each `{ key, label, values: [{ id, label, description? }] }`. JaleesBench
  emits two axes: `pressure` (6 values) and `framing` (3 values: unstated/stated/
  guided). The viewer renders one selector per axis by iterating this list — it never
  hardcodes the two axes. A producer with one axis, or three, works unchanged.
- `judges` — `[{ id, label }]`: who scored.
- `scopes` *(optional)* — an ordered list `[{ id, label, default? }]` describing
  per-verdict scopes. JaleesBench emits `full` (after pressure, default) and `turn1`
  (first response only). If a producer omits scopes, verdicts are scope-less.
- `items` — `[{ id, title, tags? }]`: the questions/probes. `title` is shown in the
  picker. `tags` is an **opaque, optional** key→value(s) map for display
  (JaleesBench fills it with `chapter`, `pillars`, `hearts`, `islamic`); the viewer
  shows tags generically and assigns no meaning to specific keys.
- `shards` — how to find each item's detail: a path template or an explicit
  `{ itemId → relativePath }` map (e.g. `probes/JLS-001.json`). Paths are relative to
  `index.json`.

**(b) Per-item shard (one JSON per probe).** Loaded on demand when an item is
selected. Contains the heavy content for that item only:

- `item` — `{ id, title, tags?, context? }`. `context` is optional producer text for
  display (JaleesBench may include `proof_texts` / chapter terrain).
- `cells` — the comparable units. Each cell is one (subject × condition-tuple):
  - `subject` — subject id.
  - `conditions` — a map `{ <axisKey>: <valueId> }` matching `conditionAxes`
    (JaleesBench: `{ pressure, framing }`).
  - `transcript` — an **ordered list of turns** `[{ role, content }]`, role ∈
    `user`/`assistant`. Generic length (JaleesBench: 4 turns — question, response,
    pressure turn, response).
  - `verdicts` — `[{ judge, scope?, band, bandLabel, summary?, rationale?,
    tags? }]`. `band` is on the display scale and matches a `bands[].value`;
    `bandLabel` is its label. `summary` ← JaleesBench `direction`; `rationale` ←
    JaleesBench `rationale` (may be absent for v2-overlaid records — viewer must
    tolerate a missing rationale). `tags` optionally carries `techniques_used`.

The shard is keyed/indexable so the viewer can find a cell by `(subject, conditions)`
in O(1) (e.g. a flat list it indexes client-side, or a nested map). Final encoding is
a plan decision.

### 5.3 How the viewer consumes the contract (generic flow)

1. Fetch `index.json`; validate `contractVersion` major. Build:
   - question picker from `items` (id + title, with `tags` shown),
   - two subject pickers from `subjects`,
   - one selector per `conditionAxes` entry,
   - band legend from `bands`, judge labels from `judges`, scope toggle from `scopes`.
2. On any selection change, lazy-fetch the selected item's shard (cache it).
3. Find cell A = `(subjectA, conditions)` and cell B = `(subjectB, conditions)`.
4. Render the two `transcript`s side by side, and each side's `verdicts` (per judge:
   band chip + label + summary/rationale), defaulting to the `default` scope with the
   other scope available. If a cell is missing, show a clear "no data for this
   combination" state (fail-soft).

### 5.4 JaleesBench-first, others later

JaleesBench is the only producer now, via the `export-web` CLI (§4.1). The contract
is designed so that (a) the Arabic set, once judged, is **another dataset in the same
format** (new `index.json`, `language: "ar"`), and (b) **a future "load your own
JSON" affordance** (point the viewer at any conforming `index.json`) is a small
additive feature — **explicitly out of scope for this spec** but not precluded by any
design choice here. We will **not** build a producer SDK, schema registry, or
multi-dataset switcher now.

### 5.5 Versioning

`contractVersion` is `MAJOR.MINOR`. The viewer requires a matching MAJOR and ignores
unknown fields (forward-compatible). The contract is documented in-repo (a short
`web/CONTRACT.md` or equivalent, finalized in the plan) so future producers have a
spec to target. Breaking shape changes bump MAJOR.

### 5.6 Cross-cutting: untrusted content & load-failure robustness

Because the viewer renders **model-authored text** (transcripts, judge summaries and
rationales, item context) and is intended to eventually load **arbitrary
contract-conforming JSON**, all such content is treated as **untrusted**:

- **Render model/producer text as escaped plain text.** No raw-HTML injection. React's
  default text rendering (which escapes) satisfies this; `dangerouslySetInnerHTML` is
  prohibited for any producer-sourced field. If a later iteration wants markdown
  rendering, it MUST run through a sanitizer (e.g. DOMPurify) with HTML disabled —
  but MVP renders plain text, preserving line breaks via CSS, not markup.
- **Fail soft on bad data assets**, with a visible, non-crashing error state for each:
  (a) `index.json` fetch failure or malformed JSON; (b) incompatible
  `contractVersion` MAJOR (show "unsupported data version"); (c) a missing or
  malformed per-item shard; (d) a referenced subject/judge/axis value absent from the
  data. None of these may throw an unhandled runtime error that blanks the page.

### 5.7 Asset paths

All data and JS/CSS assets are referenced by **paths relative to the deployed app
root**, so the same build works under GitHub Pages' `/jaleesbench/` base and under a
local dev server at `/` (and any future custom domain). Shard paths in `index.shards`
are relative to `index.json`. Vite `base` is configurable; the app must not hardcode
an absolute `/jaleesbench/` prefix in fetch calls.

## 6. Detailed behavior (the viewer UX)

- **Pickers:** question (searchable by id/title across 140 probes), Model A, Model B,
  and one selector per condition axis (Pressure, Framing). Sensible defaults when the
  URL has no state (first item, first two subjects, default/first axis values).
- **Side-by-side panel:** two columns, one per model. Each column shows the two-turn
  conversation (user question → model response → pressure turn → model response),
  clearly delineating user vs assistant turns. The shared turns (the probe question
  and the pressure text) are identical across columns by construction — display them
  so the reader sees both models answered the *same* prompt.
- **Verdicts:** under each column, both judges' verdicts for that cell: band chip
  (colored from the band ladder) + band label (e.g. "Perfume +1") + the judge's
  summary/rationale. Default to the post-pressure (`full`) scope; allow viewing the
  turn-1 verdict. Tolerate a missing rationale (v2 overlay).
- **Band legend:** a small legend rendering the band ladder (Burns…Perfume) from
  `index.bands` so the colors/labels are explained.
- **Same subject on both sides:** permitted (renders two identical columns); the
  pickers do not hard-block it. Default state picks two *different* subjects.
- **URL state (shareable deep link):** the full selection is encoded in the query
  string — `item`, `a` (subjectA), `b` (subjectB), one param per condition axis key
  (`pressure`, `framing`), and `scope` (the verdict scope, default the contract's
  default). Encoding/decoding the axis params is generic (iterate `conditionAxes`).
  Changing any picker updates the URL (history replace); loading a URL restores the
  exact view — **every view, including the scope choice, is a shareable deep link.**
  Example:
  `…/jaleesbench/?item=JLS-001&a=ansari&b=qwen3-235b&pressure=insistence&framing=unstated&scope=full`.
- **Responsive layout:** desktop shows the two columns side by side; on narrow
  (mobile) viewports the comparison falls back to a stacked or tabbed view so it
  remains usable (SHOULD).
- **Content safety & a11y:** all transcript/verdict text is rendered as escaped plain
  text (see §5.6); band meaning is conveyed by label (not color alone), and pickers
  are keyboard-navigable.
- **Empty/edge states:** missing cell → "no data for this combination"; unknown URL
  values (bad probe id, unknown subject/axis value, unsupported version) → fall back
  to defaults / show a clear error without crashing (see §5.6).

## 7. Open Questions

**Critical (resolve before/at spec-approval):**

- **C1 — Commit the exported data?** GitHub Pages serves committed files, and CI
  cannot regenerate the export (it needs the 190 MB+ gitignored raw results). The
  slimmed, English-only export (transcripts + verdicts only, dropping `usage`/`raw`/
  `attempts`/`context_prefix`) is far smaller than the raw set — **estimated ~10–30 MB
  total** across 140 shards (the assistant responses and rationales dominate; shared
  prompt text is small). **Recommendation:** commit the exported `index.json` +
  per-probe shards under `web/` (e.g. `web/public/data/`), keep raw results
  gitignored. Confirm the actual size and acceptable repo-size impact at review.
- **C2 — Deployment mechanism.** GitHub Actions building `web/` and deploying to
  Pages (recommended) vs a `gh-pages` branch. Recommendation: Actions workflow.

**Important (affects design, can be settled in the plan):**

- **I1 — Band scale in the contract:** emit bands on the display scale (−1…+1, per
  baked decision 6) — recommended — and rely on the export to do the ×0.5. The
  contract's `bands` ladder declares the display values.
- **I2 — Shard cell encoding:** flat list vs nested map keyed by subject/conditions
  (plan decision; both satisfy the contract).
- **I5 — Shard prompt de-duplication (optimization, optional):** within a probe the
  turn-1 question is identical across all cells and each pressure turn is identical
  across subjects/framings. The canonical contract keeps the full transcript per cell
  (simplest for the viewer); an optional shard-root shared-prompt table the viewer
  rehydrates is a possible size optimization. Default: inline full transcripts unless
  measured size (C1) warrants the optimization.
- **I3 — Show both scopes or just `full`?** Default `full`, expose `turn1` as a
  secondary view (recommended).
- **I4 — Search/scale of question picker** (140 items): simple searchable
  dropdown/list is sufficient.

**Nice-to-know:**

- N1 — A compact share affordance (copy-link button); URL is already shareable.
- N2 — Showing the per-cell mean band alongside the two judges.
- N3 — Light theming consistent with the existing report (green accent).

## 8. Out of scope

- Arabic results (excluded until judged; contract supports them later).
- The thinking-mode / ansari-steadfast experimental arms (separate files).
- Aggregate charts/leaderboards (that's the existing report's job; this is a
  drill-in tool). A link back to the report is acceptable.
- A "load your own JSON" UI, producer SDK, or multi-dataset switcher (enabled by the
  contract, deliberately not built now).
- Any change to collection/judging/scoring code beyond adding the export command.

## 9. Success Criteria

**Functional (MUST):**

1. A reproducible CLI export command produces a `index.json` + per-probe shards that
   conform to the §5 contract, using the existing loaders incl. the `judgments_v2`
   overlay and the −1…+1 rescale.
2. The static viewer loads `index.json`, lets the user pick a question, two models,
   a pressure, and a framing, and renders the two two-turn transcripts side by side.
3. Both judges' verdicts (band + label + rationale/summary) are shown for each side,
   defaulting to the post-pressure scope, tolerant of a missing rationale.
4. The full selection is encoded in the URL; pasting that URL reproduces the exact
   view (shareable deep link).
5. The app builds to a static bundle and is deployable to GitHub Pages under
   `/jaleesbench/` with no backend.
6. The viewer's types/components contain **no** JaleesBench-specific strings for
   axes, bands, or item metadata — all such values come from the data (verifiable by
   inspection / a reviewer).

**Functional (SHOULD):**

7. Missing cells, malformed/absent URL params, and bad data assets (unreachable or
   malformed `index.json`/shard, unsupported `contractVersion` MAJOR) fail soft with a
   visible, non-crashing error state (§5.6).
8. A band legend explains the Burns…Perfume ladder from the data (colors from
   `index.bands`, with a positional fallback when `color` is absent).
9. A short in-repo contract doc (`CONTRACT.md`) describes the format for future
   producers.
10. The export accepts `--results-path`, defaulting to the package `results/` dir.
11. Responsive fallback (stacked/tabbed) on narrow viewports; band meaning conveyed by
    label, not color alone; pickers keyboard-navigable.

**Non-functional:**

12. Initial load fetches only `index.json` (small); per-probe detail is lazy-loaded.
13. Export is deterministic and re-runnable (idempotent output for the same input).
14. No secrets, no large raw `.jsonl`, no `.vertex-sa.json` committed.
15. **Security:** all producer/model-authored text is rendered escaped/plain; no
    `dangerouslySetInnerHTML` on producer data (§5.6).

**Test scenarios:**

- Export a small subset and assert shard/index conform to the contract (schema-shape
  test on the Python side).
- Round-trip a deep-link URL → state → URL.
- A cell known to be polarizing (e.g. JLS-006 ansari +1 vs a Burns side) renders both
  transcripts and opposed bands.
- A v2-overlaid judgment (no `rationale`) renders without error.
- A malformed/absent shard and an unsupported `contractVersion` each render a
  fail-soft error state, not a blank page.
- Producer text containing HTML/markdown (e.g. `<script>` or `**bold**`) renders as
  literal escaped text, not executed/interpreted.

## 10. Consultation Log

### Iteration 1 — 3-way spec review (gemini / codex / claude)

**Verdicts:** Gemini COMMENT · Codex REQUEST_CHANGES · Claude APPROVE. All three rated
the spec strong/feasible with a well-designed data contract; the changes were
convergent, concrete, and have been incorporated:

- **Security / untrusted content** (Codex + Gemini): added §5.6 — render all
  model/producer text as escaped plain text, prohibit `dangerouslySetInnerHTML` on
  producer data, sanitize if rich rendering is ever added. Added success criterion 15
  and a test scenario.
- **Load-failure robustness** (Codex + Gemini): added §5.6 fail-soft requirements for
  bad `index.json`/shard fetch, malformed JSON, and incompatible `contractVersion`;
  folded into success criterion 7 and test scenarios.
- **Configurable results path** (Codex): §3.2 now mandates `--results-path` and
  explicitly puts the small loader refactor (threading a path through
  `load`/`load_judgments`/`load_probes`) in scope; success criterion 10.
- **Band color in the contract** (Gemini): §5.2 `bands` entries carry an optional
  `color`, with a positional fallback — keeps the UI generic yet colored.
- **Same subject on both sides** (Codex): §6 — permitted, not blocked; default picks
  two different subjects.
- **Mobile responsive + RTL-from-`language` + a11y** (Gemini + Claude): §6 responsive
  fallback (SHOULD), §5.2/§6 set text direction from `dataset.language`, a11y nods;
  success criterion 11.
- **Asset/base path** (Gemini): added §5.7 — relative asset paths, configurable Vite
  `base`, so dev (`/`) and Pages (`/jaleesbench/`) both work.
- **`web/` placement** (Claude): §3.2 fixes `web/` at the repository root.
- **Data-size estimate** (Claude): §7 C1 now estimates ~10–30 MB for the slimmed
  export.
- **Shard prompt de-duplication** (Gemini): captured as optional optimization §7 I5;
  canonical contract keeps full transcripts per cell for viewer simplicity.
- **Subject set / experimental arms** (Claude + Codex): §3.2 clarifies the export
  reads `collect.jsonl` (8 main subjects); thinking/steadfast/Arabic arms are separate
  files and out of scope.
- **Scope in URL** (Claude): §6 adds `scope` to the URL state so every view —
  including the verdict scope — is deep-linkable.

*(A second consultation and/or human feedback at spec-approval will be logged here.)*
