# Spec 3 — Public results explorer: compare two models, find where they differ, drill in

**Status:** Draft (Specify — trimmed scope; supersedes the elevated rewrite per architect)
**Issue:** #3
**Protocol:** SPIR

## 1. Overview / Problem

JaleesBench produced a large result set — 20,160 two-turn "sittings" (8 models × 6
pressures × 3 framings × 140 probes) and 80,640 judge verdicts (2 judges × 2 scopes).
The raw `.jsonl` is gitignored and far too large (190 MB) for an outsider to open.

The first build delivered a working **drill-in cell viewer** on GitHub Pages, fed by a
Python `export-web` CLI. That foundation is sound and **carries forward**. This spec adds
exactly what the requester asked, no more: an **intro**, a **"two models → where they
differ most"** view, and presentation polish — built **on** the existing foundation. It
is **not** a leaderboard and **not** a formal versioned contract.

### Carries forward (do not rebuild)
The `jaleesbench export-web` CLI and loaders; the `index.json` + gzip per-probe shard
output; the client-side **`DataSource` seam**; the **drill-in** side-by-side view; fail-
soft behavior, escaped-by-default rendering, relative asset paths, Pages deploy.

### New (this spec)
Intro + paper link · markdown (sanitized) · collapsible long responses · sans-serif ·
light/dark · per-model score header · the **compare-by-divergence** view · presets · a
**compact per-cell score blob** in `index.json` so compare + presets are instant · URL
state for every view.

## 2. Stakeholders
The **newcomer** (scholar/reviewer/journalist/practitioner) who wants to read what the
models actually did and find the revealing cases; the **authors** (a companion to the
paper); the **architect**.

## 3. Constraints

### 3.1 Fixed requirements
1. **Public + zero-install**; **every view is a URL-shareable deep link**.
2. **Read-only, no harness change** (adds only the export command).
3. **English results for now** (Arabic excluded; not precluded by design).
4. **Band scale fidelity** — −1…+1 (`score.py` `SCORE_SCALE` 0.5).
5. **Build ON the existing foundation** — extend, do not discard.
6. **One "beyond JaleesBench" rule (cheap hygiene):** the UI/types use **generic names**
   (subjects, items, condition axes, judges, bands); the specific values (pressure/
   framing/Burns…Perfume) come from the exported data, never hardcoded in components.
   **No formal versioned contract, no producer-declared config, no schema ceremony.**
7. **Untrusted-content safety** (§5.6): escaped-by-default text; markdown only via a
   renderer with raw HTML disabled + sanitized.

### 3.2 Environmental facts
Raw data gitignored (~190 MB) in the main checkout; export reads a configurable
`--results-path`. English `collect.jsonl` has the **8 main subjects**; thinking/
steadfast/Arabic arms are separate files, out of scope. Repo hygiene: explicit
`git add`, `[Spec 3]` commits, no attribution lines.

## 4. The product

A single-page app with a persistent **intro** header and two modes — **detail**
(drill-in) and **compare** — both URL-shareable.

### 4.1 INTRO (top of page)
A concise plain-English panel (collapsible): **what JaleesBench measures** — whether the
AI is a *righteous companion* (al-jalīs al-ṣāliḥ), judged by the **residue its counsel
leaves on the user** (the perfume-seller vs the blacksmith), **not** knowledge or
professed values; the band scale **−1 Burns … +1 Perfume**; **what each control does**
(question, the two models, pressure, framing, scope); and a **link to the paper**
(`docs/paper/jaleesbench-paper.pdf` via its GitHub URL), marked **draft / under review**.

### 4.2 COMPARE — two models, where they differ most (the new view)
"Two people pick two models and find the examples where they differ the most."
- Pick **Model A** and **Model B**.
- A **ranked list of cells** (question × pressure × framing) sorted by
  **|score(A) − score(B)| descending** — each row shows the question, the condition, and
  both scores (e.g. A Perfume vs B Burns).
- **One click on a row → the drill-in** for that exact cell.
- Computed from the in-memory score blob — **instant, no shard loads**.
- *(No "agree" section, no win/tally summary — just the differ-most ranking.)*

### 4.3 DRILL-IN — the detail view (done right)
Select a **question → two models → pressure + framing**; see **both responses**, then
**both judges' verdicts**:
- **Per-model score header** on each column: e.g. `glm-5.1 (+0.75 initial → +0.5
  post-pressure)` — the mean of the 2 judges, turn-1 (initial) vs full (post-pressure),
  on the −1…+1 scale.
- Two-turn **transcripts** rendered as **markdown** (sanitized — §5.6), **collapsible**:
  long responses show ~the first 10 lines, click to expand/collapse; turns row-aligned.
- Both judges' **verdicts** per side (band chip + label + summary + rationale, rationale
  markdown + collapsible), default post-pressure scope, tolerant of a missing rationale.
- The item's tags (chapter/pillars/hearts/islamic) + proof-text context; a **band
  legend** from the data.

### 4.4 PRESETS
Curated deep-links, computed in the export, surfaced as a menu:
- **Polarizing — models did poorly / split** — the widest cross-model spread cells (one
  near Perfume, another near Burns); the entry links the **max-score model as A vs the
  min-score model as B**.
- **Where the judges differed** — cells where the two judges' **native band values
  differ by ≥2** (the `judgments_v2` re-judge signal); the entry links that model vs a
  contrast model.
Each entry is a deep-link to a compare or detail view. Deterministic (fixed thresholds,
sorted by magnitude with item/condition tie-breaks, capped, one per item for variety).

### 4.5 POLISH
- **Light/dark toggle**, persisted in `localStorage`, default `prefers-color-scheme`.
- **Sans-serif** typography throughout.
- **Responsive**; **every view shareable by URL** (mode + that view's state).

## 5. Data & rendering

### 5.1 Foundation reused
The export still writes `index.json` (plain) + one gzip `.json.gz` shard per probe
(transcripts + verdicts), loaded lazily on drill-in via the `DataSource` seam. No formal
contract doc; the **existing `CONTRACT.md` is removed** (the format is self-evident and a
short note lives in the app README).

### 5.2 NEW — a compact per-cell score blob in `index.json`
A numbers-only blob so the **compare** ranking and **presets** are instant without
loading shards: **subject × item × pressure × framing × scope → mean band** (mean of the
cell's judge bands, display scale; `null` if absent).

```jsonc
"scores": {
  "order": ["subject", "item", "pressure", "framing", "scope"], // index's ordered lists
  "shape": [8, 140, 6, 3, 2],
  "data": [ /* flat row-major: number | null */ ]               // ~40k numbers, ~250 KB
}
```
The UI reads it generically from the index's existing ordered lists — just numbers, no
versioned schema, no producer-declared metrics. `index.json` also gains: `presets`
(§4.4), a `paper` link (§4.1), and per-subject overall means for the score header's
optional overall figure (or computed from the blob).

### 5.3 Compare divergence (client-side, from the blob)
For chosen A, B: for every `(item × pressure × framing)` cell, `score(A) − score(B)` at
the **default scope** (`scopes[].default` = full); rank by `|·|` descending. Cells
**null for either model are excluded**. List is top-N (plan constant) with "show more";
ties broken by item id then condition order.

### 5.4 Drill-in score header
Per column, from the shard's verdicts (or the score blob): **initial** = mean of the 2
judges at turn-1; **post** = mean at full; both on the −1…+1 scale; `—` if absent.

### 5.5 Presets (export-side)
Computed in `export-web` from the loaded judgments/sittings (§4.4 semantics). A preset
with no qualifying entries is omitted.

### 5.6 Untrusted content, markdown, fail-soft (kept)
- **Default escaped plain text** for any non-markdown field; `dangerouslySetInnerHTML`
  prohibited on raw producer data.
- **Markdown** (transcript responses, judge rationales/summaries): `markdown-it`
  `html:false` + **DOMPurify**; a literal `<script>` renders inert. **Links:** only
  `http`/`https`/`mailto` schemes allowed; `javascript:` (and others) stripped; external
  links get `rel="noopener noreferrer"` + `target="_blank"`.
- **Fail-soft** on every bad data asset (index/shard fetch failure, malformed JSON,
  missing cell, absent reference) — a visible, non-crashing message, never a blank page.

### 5.7 Asset paths (kept)
Assets referenced relative to the app root (configurable `base`) so the build works at
the Pages project path and locally. Shards are gzip — fetch and decompress only when the
bytes are still gzip (host `Content-Encoding: gzip` may pre-decompress).

## 6. URL state
A `view`/mode param + per-view state; changing a control updates the URL
(`replaceState`); loading restores the view; `popstate` restores back/forward. Axis-
generic (axis params by key).
- `?view=compare&a=ansari&b=qwen3-235b` — the divergence ranking.
- `?view=detail&item=JLS-001&a=ansari&b=qwen3-235b&pressure=insistence&framing=unstated&scope=full`
  — the drill-in (back-compatible with the MVP param names).
- Presets resolve to one of the above. **Default landing: detail** (first item, first two
  subjects, default condition + scope). Invalid params → nearest valid default, no crash.

## 7. Open Questions
- **I1 — Compare list size N** — recommend ~50 with "show more".
- **I2 — Score-header overall** — optionally show the model's overall mean beside the
  per-cell initial→post (cheap from the blob); priority is the per-cell figure.
- **I3 — Markdown lib** — `markdown-it` (`html:false`, linkify) + DOMPurify.

## 8. Out of scope
- A **leaderboard / overview** surface and its metrics (cut).
- The **"agree"** section and A-vs-B **summary/tally** in compare (cut).
- A **formal versioned contract**, `CONTRACT.md`, producer-declared metrics, or genericity
  for hypothetical future producers (cut — only the cheap "don't hardcode" hygiene
  remains, §3.1.6).
- Arabic results; thinking/steadfast arms; a backend; statistical inference; any change
  to collection/judging/scoring beyond the export command.

## 9. Success Criteria

**MUST:**
1. `export-web` emits `index.json` (now incl. the compact **`scores`** blob, **`presets`**,
   `paper`, per-subject score data) + gzip per-probe shards, using the existing loaders
   (v2 overlay + −1…+1 rescale). `CONTRACT.md` removed.
2. **Intro** explains the construct + controls and links the (draft) paper.
3. **Compare**: pick A + B → a divergence-ranked list (|score(A)−score(B)| desc); a row
   click opens the drill-in. Instant, no shard loads. Null-either cells excluded.
4. **Drill-in** renders both responses (markdown, sanitized; collapsible) + per-model
   **score header** (initial → post) + both judges' verdicts.
5. **Presets** menu offers polarizing/models-did-poorly and judges-differed deep-links.
6. **Every view** (compare / detail / preset) is encoded in the URL and restored on load.
7. **No JaleesBench-specific strings** in the types/components — values come from the data.
8. **Light/dark** persisted (localStorage, prefers-color-scheme default); **sans-serif**;
   responsive.

**SHOULD:** fail-soft on bad assets/params; band legend from data; markdown raw-HTML
disabled + link-scheme allowlist; deterministic/idempotent export; no secrets/raw jsonl
committed.

**Test scenarios:** compare divergence ranking (desc, null-either excluded, tie-break);
URL round-trip for each view; markdown — literal `<script>` inert, `**bold**` rendered,
`javascript:` link stripped, `https`/`mailto` allowed; collapsible expand/collapse;
score-header math (mean of 2 judges, turn1/full); a preset deep-link resolves; v2 verdict
(no rationale) renders.

## 10. Consultation Log

### Trim (architect, post-elevation)
The elevated spec over-built (architect's own additions). Cut: the **overview/
leaderboard** surface + its metrics; the compare **"agree"/summary**; the **versioned-
contract ceremony** (version bump, producer-declared metrics config, `CONTRACT.md`,
graceful-degrade prose). "Beyond JaleesBench" reduced to one cheap rule — don't hardcode
JaleesBench strings in the UI/types (§3.1.6). **Kept** exactly the requester's asks:
drill-in done right, markdown/collapsible/sans-serif/light-dark, per-model score header,
the **compare-by-divergence** view, presets, intro + paper link, public + URL state, the
DataSource seam, and the **score blob as plain numbers** (for fast compare/presets, not a
contract). Net: skin + the divergence view on the existing foundation.

*(Earlier iterations: the MVP and the elevated rewrite passed 3-way review; this trim is
streamlined per architect — re-presented at spec-approval for a fast clear.)*
