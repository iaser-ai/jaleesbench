# Spec 3 — Public results EXPLORER: orient → leaderboard → divergence compare → drill-in

**Status:** Draft (Specify phase — elevated rewrite, supersedes the MVP "cell viewer" spec)
**Issue:** #3
**Protocol:** SPIR

## 1. Overview / Problem

JaleesBench has produced a rich result set — 20,160 two-turn "sittings" (8 subject
models × 6 pressures × 3 framings × 140 probes) and 80,640 judge verdicts (2 judges ×
2 scopes per sitting). The raw `.jsonl` is gitignored and far too large (190 MB) for an
outsider to open.

The first build delivered a working **drill-in cell viewer** (pick a question + two
models + pressure + framing → side-by-side transcripts + verdicts, URL-shareable, on
GitHub Pages, fed by a Python `export-web` CLI emitting a versioned data contract). That
foundation is sound and **carries forward**. But on review it is **too low**: a person
who just discovered this dataset cannot *understand* it — they land on a blank picker
and must already know what to look for.

**This spec elevates the tool to an exploration instrument.** A newcomer should, in
order: **orient** (what is this measuring?), see an **overview** (who is good company,
who burns you, what pressure does), **compare two models ranked by where they differ
most** (the centerpiece), and **drill in** to the transcripts and verdicts behind any
cell — with **every view shareable by URL**.

### What carries forward (do NOT rebuild)
- The Python **`jaleesbench export-web`** CLI and the loaders it reuses.
- The **versioned data contract** (`index.json` + per-probe shards) and `CONTRACT.md`.
- The client-side **`DataSource` seam** (static-file impl).
- The **drill-in detail view** (side-by-side transcripts + both judges' verdicts).
- Fail-soft behavior, escaped-by-default rendering, relative asset paths, GitHub Pages
  deploy.

### What is new (this spec)
- An **orient** panel, an **overview leaderboard**, and a **divergence-ranked compare**
  surface — the newcomer's path.
- A **compact score matrix** in `index.json` (numbers only) so the app
  ranks/leaderboards/compares **instantly, without loading any shard**.
- **Markdown** (safely sanitized) + **collapsible** long responses + **sans-serif** +
  **per-model score headers** in the drill-in.
- **Guided presets**, **light/dark mode**, and **URL state for every surface**
  (leaderboard / compare / ranking / detail).

## 2. Stakeholders

- **The newcomer** (primary): a scholar, reviewer, journalist, or curious practitioner
  who just found the dataset and wants to *understand* it, then verify by reading
  transcripts. The whole design serves this path.
- **The JaleesBench authors** (Waleed, Ben, Tim): a credible companion to the paper.
- **The architect**: owns the data-contract + score-matrix architecture.
- **Future producers**: other benchmarks adopting the same contract.

## 3. Constraints

### 3.1 Fixed requirements

1. **Public + zero-install**, anyone with the link — no install/login/backend to run.
2. **Every view is a URL-shareable deep link** — including the leaderboard, a compare
   (A vs B) ranking, and a drill-in detail.
3. **Read-only, no harness change** — never modifies `collect.jsonl` /
   `judgments.jsonl` / `judgments_v2.jsonl`; adds only the export command.
4. **English results for now** (Arabic excluded until judged; not precluded by design).
5. **Data-contract generality** (architect KEY requirement, carried forward): the viewer
   is generic over subjects / items / condition axes / a band ladder / judges; all
   product-specific values live in the exported data. Build the clean seam; do not
   over-engineer a schema engine.
6. **Band scale fidelity**: bands reported on **−1…+1** (`score.py` `SCORE_SCALE` 0.5).
7. **Build ON the existing foundation** (§1) — extend, do not discard.
8. **Untrusted content safety (§5.6)**: model/producer text rendered escaped-by-default;
   **markdown** is rendered only through a sanitizer with **raw HTML disabled** (no raw
   HTML execution). This is the "later iteration" §5.6 anticipated.

### 3.2 Fixed environmental facts
- Raw data is gitignored, ~190 MB, in the main checkout; the export reads a configurable
  `--results-path` (CI cannot regenerate).
- The English set (`collect.jsonl`) has exactly the **8 main subjects**; thinking/
  steadfast/Arabic arms are separate files, out of scope.
- Repo hygiene (project CLAUDE.md): explicit `git add`, `[Spec 3]` commits, no
  attribution lines.

## 4. The product — four surfaces + presets + polish

A single-page app with a persistent **orient** header and three switchable surfaces
(**overview**, **compare**, **detail**). The newcomer's path is overview → compare →
detail; each surface deep-links to the next.

### 4.1 ORIENT (always at the top)
A concise plain-English panel (collapsible, but open by default on first visit):
- **What JaleesBench measures**: whether the AI is a *righteous companion* (al-jalīs
  al-ṣāliḥ) — judged by the **residue its counsel leaves on the user** (the
  perfume-seller vs the blacksmith), **not** knowledge or professed values.
- **The axes**: 140 questions · 8 models · 6 pressures × 3 framings · 2 judges ·
  band scale **−1 Burns … +1 Perfume**.
- **What each control does** (question, the two models, pressure, framing, scope).
- A **link to the paper** (`docs/paper/jaleesbench-paper.pdf`, via its GitHub URL),
  clearly marked **draft / under review, not yet published**.

### 4.2 OVERVIEW — the leaderboard (landing surface)
Not a blank picker. A **model leaderboard** computed instantly from the score matrix.
**The metrics are producer-declared** (`index.leaderboard.metrics`, §5.4) so the UI
stays generic — it computes each metric over matrix *slices* without hardcoding axis
values. JaleesBench declares three (their JaleesBench-specific meaning lives in the
data, not the code):
- **Jalees Score** — `mean` over the (Unstated framing, after-pressure) slice: the
  paper's headline, what a user actually receives. Models are ranked by this primary
  metric.
- **Recognition gap** — `delta`: mean(Stated) − mean(Unstated) at full scope — how much
  better the model is once it knows it serves a practising Muslim.
- **Pressure effect** — `delta`: full − turn-1 (Unstated) — how far the model moves
  when pushed (negative = caves).
A newcomer immediately sees who is good company, who burns you, and what pressure does.
Each model row **preselects that model as Model A in compare** (Model B defaults to the
next-ranked model); the row also links to that model's first drill-in.

### 4.3 COMPARE — two models ranked by divergence (THE CENTERPIECE)
"Two people pick two models and find the examples where they differ the most."
- Pick **Model A** and **Model B**.
- A **ranked list of cells** (question × pressure × framing) where A and B **differ
  most** (e.g. A Perfume vs B Burns) — sorted by |score(A) − score(B)| descending — each
  row showing the question, the condition, and both scores.
- A section for where they **agree** (smallest divergence), and an **A-vs-B summary**
  (how many cells each "wins", mean A vs mean B, biggest gaps).
- **One click on a row → the drill-in detail** for that exact cell.
- Computed entirely from the in-memory score matrix — **instant, no shard loads**.

### 4.4 DRILL-IN — the detail view (the current view, done right)
Side-by-side, Model A vs Model B, for the selected question + pressure + framing:
- **Per-model score header** on each column: e.g. `glm-5.1 (+0.75 initial → +0.5
  post-pressure)` — the mean of the 2 judges, turn-1 (initial) vs full (post-pressure),
  on the −1…+1 scale. (Optionally also the model's overall-bench mean.)
- The two-turn **transcripts** rendered as **markdown** (safely sanitized — §5.6),
  **collapsible**: long responses show ~the first 10 lines with a click to
  expand/collapse. Turns row-aligned across columns.
- Both judges' **verdicts** per side (band chip + label + summary + rationale, rationale
  markdown + collapsible), defaulting to the post-pressure scope, tolerant of a missing
  rationale.
- The item's tags (chapter/pillars/hearts/islamic) and proof-text context.
- A **band legend** explaining Burns…Perfume from the data.

### 4.5 GUIDED PRESETS
Curated deep-links, computed in the export and surfaced as a menu:
- **Where the judges disagreed most** — cells with a ≥2-band judge split (the
  `judgments_v2` re-judge signal captures exactly these).
- **Where two models diverged most** — the widest cross-model spread cells.
- **The polarizing set** — one model Perfume (+1), another Burns (−1) on the identical
  situation.
Each preset entry is a deep-link to a specific compare or detail view.

### 4.6 POLISH
- **Light/dark toggle**, persisted in `localStorage`, defaulting to
  `prefers-color-scheme`.
- **Sans-serif** typography throughout.
- **Responsive**: usable on mobile (the compare list and detail stack/adapt).
- **Every view shareable by URL** — a `view` parameter plus that view's state
  (leaderboard sort, compared A/B, ranking, or the full detail selection).

## 5. Data contract & architecture (the enabler)

The viewer is a function of a **documented, versioned data contract**. The elevated
surfaces (overview/compare) are powered by one new idea: a **compact score matrix** in
`index.json` so the app aggregates instantly without touching shards.

### 5.1 Design principle
**Generic in the types/UI, specific in the data.** Types and components know *subjects /
items / condition axes / a band ladder / judges / a score matrix*; they do not know
"pressure", "framing", "Burns", or probe field names. Every JaleesBench-specific value
lives in the data. The new aggregate surfaces degrade gracefully: a producer that omits
the score matrix (or presets) still gets the drill-in viewer.

### 5.2 The contract artifacts

**(a) `index.json` — the catalog + aggregate layer.** Small enough to load once on
startup; powers orient, leaderboard, and compare with **no shard loads**. Fields
(carried-forward unless marked NEW):
- `contractVersion` — bumped to **`"1.1"`** (additive; viewer requires matching MAJOR,
  ignores unknown fields).
- `producer`, `dataset {title, description, language}`, `bands[]` (display scale,
  label, optional color), `judges[]`, `scopes[]` (default flag), `conditionAxes[]`
  (the generic pressure/framing seam), `items[{id,title,tags?}]`, `shards{itemId→path}`.
- `subjects[]` — `{id, label, scores?}` where **NEW** `scores` = `{initial, post}`, the
  model's overall mean band (turn-1 / full) for the score header's optional overall.
- **NEW `scoreMatrix`** — the compact numeric core (§5.3).
- **NEW `leaderboard`** — producer-declared overview metrics (§5.3).
- **NEW `presets[]`** — curated deep-links (§5.4).
- **NEW `paper`** *(optional)* — `{url, label, draft: true}` for the orient link.

**(b) Per-item shard (gzip `.json.gz`, lazy on drill-in)** — unchanged: `item{…,
context?}` + `cells[]` (subject, conditions, transcript[turns], verdicts[{judge, scope,
band, bandLabel, summary?, rationale?, tags?}]). Heavy text loads only when a detail is
opened.

### 5.3 The score matrix (NEW — the key piece)
A compact, numbers-only tensor: **subject × item × (each condition axis) × scope → mean
band** (mean of that cell's judge bands, display scale; `null` if the cell is absent).

```jsonc
"scoreMatrix": {
  "order": ["subject", "item", "pressure", "framing", "scope"], // subject, item, axisKeys…, scope
  "shape": [8, 140, 6, 3, 2],                                    // lengths, matching index lists
  "data": [ /* flat, row-major: number | null */ ]
}
```
- `order` references the index's ordered lists (`subjects`, `items`, each
  `conditionAxes[k].values`, `scopes`) — fully generic, no hardcoded axis names.
- `data` is row-major flat (last axis fastest). The viewer computes a cell's offset from
  the shape; `null` marks a missing cell.
- Size: 8·140·6·3·2 = 40,320 numbers ≈ ~200–300 KB plain (≈ tens of KB gzipped on the
  wire) — a one-time load that makes overview/compare instant.

**Derived client-side from the matrix (no shards), driven by producer config:**
- **Leaderboard** uses `index.leaderboard.metrics` (below) — the UI computes each metric
  per subject over matrix slices generically (no hardcoded axis values).
- **Compare divergence**: for chosen A, B, for every (item × condition-tuple) cell at the
  default scope, `score(A) − score(B)`; rank by |·| for "differ most", by small |·| for
  "agree"; aggregate for the A-vs-B summary. (Axis-generic — no hardcoded axis names.)

**NEW `index.leaderboard` (producer-declared metrics — keeps the UI generic):**
```jsonc
"leaderboard": {
  "primaryKey": "jalees",                 // metric to rank/sort by default
  "metrics": [
    { "key":"jalees", "label":"Jalees Score", "kind":"mean",
      "where": { "framing":"unstated", "scope":"full" } },
    { "key":"recognition", "label":"Recognition gap", "kind":"delta",
      "from": { "framing":"unstated", "scope":"full" },
      "to":   { "framing":"stated",   "scope":"full" } },
    { "key":"pressure", "label":"Pressure effect", "kind":"delta",
      "from": { "framing":"unstated", "scope":"turn1" },
      "to":   { "framing":"unstated", "scope":"full" } }
  ]
}
```
- A *slice* (`where`/`from`/`to`) is a partial constraint mapping axis keys (and the
  special key `scope`) to value ids; unconstrained axes are free. The UI matches matrix
  cells against it without knowing the axis names.
- `kind:"mean"` → per subject, mean band over cells matching `where`.
  `kind:"delta"` → per subject, mean(`to`) − mean(`from`).
- Only two kinds (`mean`, `delta`) — deliberately not a formula DSL. JaleesBench supplies
  these defs; a producer omitting `leaderboard` simply has no overview surface.

### 5.3a Aggregation semantics (explicit, for reproducibility/testing)
- **Null cells are excluded** from every mean (mean over present cells in the slice); a
  metric with zero present cells for a subject renders `—`.
- **Compare divergence** considers only cells where **both** A and B are non-null; a cell
  missing for either model is omitted from the ranking and the win/agree tally.
- **Wins / agree / ties**: A "wins" a cell if `score(A) − score(B) > ε`; B wins if
  `< −ε`; otherwise it is an "agree" (tie). `ε = 0.001` on the display scale. The
  "differ most" list is the top-N by `|score(A) − score(B)|` (descending, ties broken by
  item then condition order); "agree" is the smallest-|Δ| set. N is a plan-level constant
  (recommend ~50, with a "show more").
- **Presets** are computed in the export from the matrix/verdicts; a preset with no
  qualifying entries is omitted. Each preset caps entries (plan constant) and is
  deterministic (fixed thresholds + ordering).

### 5.4 Presets (NEW)
`presets[]` = `[{ key, label, description, entries[] }]`; each entry =
`{ label, params }` where `params` is a flat URL-param map the viewer feeds through the
same decoder (so axis keys stay generic). JaleesBench emits at least: judges-disagreed
(≥2-band split), models-diverged (widest spread), polarizing (Perfume↔Burns).

### 5.5 Consumption, versioning, robustness (carried forward)
- The viewer builds orient/leaderboard/compare from `index.json` (incl. `scoreMatrix`),
  and lazy-loads a shard only on drill-in. If `scoreMatrix` is absent (a minimal
  producer), the overview/compare surfaces are hidden and the app degrades to drill-in.
- `contractVersion` MAJOR-gated; unknown fields ignored; **§5.6** (untrusted content) and
  **§5.7** (relative asset paths) unchanged.

### 5.6 Cross-cutting: untrusted content, markdown, load-failure robustness
- **Default: escaped plain text.** Any field NOT explicitly markdown-rendered is escaped
  (React default); `dangerouslySetInnerHTML` is prohibited on raw producer data.
- **Markdown (sanctioned):** transcript responses and judge rationales/summaries are
  rendered as **markdown through a renderer with raw HTML disabled** (`markdown-it`
  `html:false`) **and sanitized** (DOMPurify) before injection — no raw-HTML execution.
  A literal `<script>` in producer text renders as inert text.
  - **Links:** only `http`, `https`, and `mailto` URL schemes are allowed; `javascript:`
    (and any other scheme) is stripped. External links render with
    `rel="noopener noreferrer"` and `target="_blank"`.
- **Fail-soft** on every bad data asset (index/shard fetch failure, malformed JSON,
  unsupported `contractVersion`, missing cell, absent subject/judge/axis/matrix ref) —
  a visible, non-crashing message, never a blank page.

### 5.7 Asset paths (carried forward)
All assets referenced relative to the app root (configurable `base`), so the build works
under the GitHub Pages project path and locally without a hardcoded prefix. Shards are
gzip — fetch and decompress only when the bytes are still gzip (host
`Content-Encoding: gzip` may pre-decompress).

## 6. Detailed behavior + URL state

- **URL is the single source of view state.** A `view` param selects the surface, plus
  per-view params; changing any control updates the URL (`history.replaceState`);
  loading a URL restores the exact view; back/forward restores via `popstate`. Generic
  over `conditionAxes` (axis params read/written by key).
  - `?view=overview&sort=jalees` — leaderboard (+ sort key).
  - `?view=compare&a=ansari&b=qwen3-235b` — divergence ranking for A vs B.
  - `?view=detail&item=JLS-001&a=ansari&b=qwen3-235b&pressure=insistence&framing=unstated&scope=full`
    — drill-in. (Back-compatible with the MVP's param names.)
  - Presets resolve to one of the above.
- **Defaults / fail-soft:** no params → overview. Invalid params → nearest valid default
  (e.g. unknown subject → first; unknown view → overview), never a crash.
- **Navigation rules (explicit):**
  - An **overview row** → `view=compare` with that model as `a`; `b` defaults to the
    next-ranked distinct model (the top model if the row *is* the next-ranked). The row
    also offers a direct drill-in (its first cell at the default condition + scope).
  - A **compare row** (a divergence/agree entry) → `view=detail` for that exact
    `item × condition × (a,b)`, default scope.
  - The **orient** panel is open on a visitor's first load and collapsed thereafter,
    persisted via a `localStorage` flag (`orient-seen`); a deep-linked non-overview view
    starts with orient collapsed. The toggle is always available.
  - Compare "differ most" / "agree" lists are top-N (plan constant) with a "show more";
    ties broken deterministically (item id, then condition order). See §5.3a.
- **Drill-in specifics:** per-model score header (initial → post), markdown +
  collapsible transcripts (≈10-line clamp, expand/collapse), both judges' verdicts
  (default full scope, turn-1 available), band legend, item tags + context, turns
  row-aligned, RTL from `dataset.language`, keyboard-navigable controls.

## 7. Open Questions

**Important (settle in plan):**
- **I1 — Matrix slice for the leaderboard headline.** Recommend the paper's Jalees Score
  (full, unstated) as the primary, with recognition gap + pressure effect as columns.
- **I2 — Compare ranking scope.** Recommend ranking on `full` scope divergence;
  optionally toggle to turn-1.
- **I3 — Matrix size.** ~200–300 KB plain in `index.json`; acceptable for a one-time
  load (gzipped on the wire). If it ever bloats, the matrix could move to a separate
  lazily-loaded `matrix.json` — keep that option open.
- **I4 — Markdown library.** Recommend `markdown-it` (`html:false`, linkify) + DOMPurify.

**Nice-to-know:** N1 — sparkline per model in the leaderboard; N2 — copy-link button;
N3 — "share this comparison" affordance.

## 8. Out of scope
- Arabic results, thinking/steadfast experimental arms.
- A backend / API, a "load your own JSON" UI, a producer SDK.
- Statistical inference (CIs, significance) beyond the existing single-run means.
- Any change to collection/judging/scoring code beyond the export command.

## 9. Success Criteria

**Functional (MUST):**
1. The reproducible `export-web` CLI emits a `1.1` contract — `index.json` (incl.
   `scoreMatrix`, `leaderboard`, `subjects[].scores`, `presets`) + gzip per-probe shards
   — using the existing loaders (v2 overlay + −1…+1 rescale).
2. **Orient** panel explains the construct, axes, controls, and links the (draft) paper.
3. **Overview leaderboard** ranks models by the producer-declared primary metric, with
   the other declared metrics as columns — computed generically from the matrix
   (no hardcoded axis values), instant, no shard loads. Null cells excluded (§5.3a).
4. **Compare**: pick A + B → a divergence-ranked list of cells (most-differ + agree +
   A-vs-B summary); a row click opens the drill-in. Instant, no shard loads.
5. **Drill-in** renders side-by-side transcripts (markdown, sanitized; collapsible) +
   per-model score header (initial → post) + both judges' verdicts.
6. **Presets** menu offers the curated deep-links (judges-disagreed, models-diverged,
   polarizing).
7. **Every view** (overview / compare / detail / preset) is encoded in the URL and
   restored on load.
8. **No JaleesBench-specific strings** in the types/components — all from data (§9.6
   carried). Matrix consumed generically via `order`/`shape`.
9. **Light/dark** toggle persisted (localStorage, prefers-color-scheme default);
   sans-serif; responsive.

**SHOULD:** fail-soft on all bad assets/params incl. absent matrix (degrade to
drill-in); band legend from data; `CONTRACT.md` updated; markdown raw-HTML disabled +
sanitized; graceful when a producer omits matrix/presets.

**Non-functional:** initial load = `index.json` only (no shards) for orient/leaderboard/
compare; shards lazy on drill-in; deterministic/idempotent export; no secrets/raw jsonl
committed; security per §5.6.

**Test scenarios:** matrix offset/round-trip; leaderboard metric computation from
producer `metrics` defs (mean + delta over slices, nulls excluded); divergence
ranking/win-agree/tie (ε) with cells missing for one model excluded; URL round-trip for
each `view`; a polarizing cell shows opposed bands; a v2 verdict (no rationale) renders;
literal `<script>` renders inert and `**bold**` renders as markdown; a `javascript:`
link is stripped, `https`/`mailto` allowed; absent matrix → overview/compare hidden,
drill-in still works; preset deep-link resolves.

## 10. Consultation Log

### Elevated rewrite (architect PR-gate feedback)
The MVP "cell viewer" was judged too low. This spec was rewritten to an **exploration
tool** — orient → leaderboard → divergence-ranked compare → drill-in — built **on** the
existing foundation (export, contract, DataSource seam, drill-in all carry forward). Key
architectural addition: a **compact score matrix** in `index.json` so overview/compare
are instant without shard loads. Contract bumped 1.0 → **1.1** (additive: `scoreMatrix`,
`subjects[].scores`, `presets`, `paper`), with graceful degradation when absent. The 7
requester asks (markdown, collapsible, sans-serif, score header, presets, intro+paper,
light/dark) are folded into §4/§5/§6.

### Iteration 2 — 3-way review of the elevated spec (Claude APPROVE · Codex/Gemini REQUEST_CHANGES)

Both REQUEST_CHANGES were chiefly that **the committed plan is still the MVP plan** —
expected: the plan is rewritten in the *next* (Plan) phase, after spec-approval; this is
the spec review. The substantive **spec-level** points were addressed:
- **Genericity contradiction** (Codex): the leaderboard metrics no longer hardcode
  JaleesBench axis values — they are **producer-declared** in `index.leaderboard.metrics`
  (mean/delta over matrix slices, §5.3), so the UI computes them generically. The
  divergence compare was already axis-generic.
- **Aggregation semantics** (Codex): added §5.3a — null exclusion, both-non-null for
  compare, wins/agree/ties with `ε`, top-N + deterministic tie-breaks, sparse-preset
  omission.
- **Navigation/state ambiguity** (Codex): §6 now specifies overview→compare preselect,
  compare-row→detail, orient first-visit persistence, and list sort/limit.
- **Concrete markdown link safety** (Codex): §5.6 allowlists `http`/`https`/`mailto`,
  strips `javascript:`, and sets `rel=noopener`/`target` on external links.

*(Human feedback at spec-approval will be logged here. The implementation **plan** is
rewritten to this elevated spec in the Plan phase.)*
