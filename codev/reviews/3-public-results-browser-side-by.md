# Review: public-results-browser-side-by

## Summary

A public, zero-install web app (`apps/jaleesbrowser/`) for browsing JaleesBench
results: pick a question, pick two models, pick a pressure + framing, and read the two
two-turn conversations and both judges' verdicts **side by side**, with the full
selection encoded in the URL as a shareable deep link. Hosted statically on GitHub
Pages, fed by a Python `export-web` CLI that emits a **documented, versioned data
contract** (a plain `index.json` + gzip-compressed per-probe shards). The viewer is
**generic over the contract** — it knows about subjects, items, condition axes, a band
ladder, judges, transcripts, and verdicts, but no JaleesBench-specific strings — so
JaleesBench is simply the first producer of the format.

Delivered as 5 sequential implement phases on one branch:
1. **Data contract + Python `export-web` CLI** (reuses `score.py` loaders incl. the
   `judgments_v2` overlay + −1…+1 rescale; gzip shards; deterministic/idempotent).
2. **App scaffold + contract types + DataSource seam** (Vite + React + TS).
3. **Generic pickers + URL deep-link state**.
4. **Side-by-side comparison + verdicts + band legend**.
5. **Static build, GitHub Pages workflow + full data export**.

## Spec Compliance

All spec §9 success criteria met:

- [x] **§9.1** Reproducible `export-web` CLI emits a contract-conforming index + shards
  using the existing loaders (v2 overlay + rescale).
- [x] **§9.2** Viewer lets the user pick question + two models + pressure + framing and
  renders both two-turn transcripts side by side.
- [x] **§9.3** Both judges' verdicts (band + label + rationale/summary) per side,
  default post-pressure scope, tolerant of a missing rationale.
- [x] **§9.4** Full selection (incl. scope) encoded in the URL; pasting reproduces the
  view (deep link).
- [x] **§9.5** Public, zero-install, no backend; static bundle deployable to GitHub
  Pages at the project path (relative `base`).
- [x] **§9.6** No JaleesBench-specific strings in the types/components — all axis/band/
  item values come from the data (verifiable by inspection; `contract.ts` is the only
  place the shapes are named).
- [x] **§9.7** Fail-soft on missing cells, bad URL params, and bad data assets (index/
  shard fetch failure, malformed JSON, unsupported `contractVersion`).
- [x] **§9.8** Band legend rendered from `index.bands` (with positional color fallback).
- [x] **§9.9** `CONTRACT.md` documents the format for future producers.
- [x] **§9.10** `export-web` accepts `--results-path`.
- [x] **§9.11** Responsive (subgrid alignment + stacked fallback); band meaning by
  label not color alone; keyboard-navigable pickers; RTL from `dataset.language`.
- [x] **§9.12** Initial load fetches only `index.json`; shards are lazy + cached.
- [x] **§9.13** Export is deterministic/idempotent (sorted keys, fixed orderings, gzip
  `mtime=0`).
- [x] **§9.14** No secrets, no raw `.jsonl`, no `.vertex-sa.json` committed (verified).
- [x] **§9.15** All producer text rendered escaped/plain; no `dangerouslySetInnerHTML`.

The architect's KEY requirement — a contract-driven viewer, not JaleesBench-hardcoded —
is realized via §5's `index.json` + per-item shard schema and the `conditionAxes`
seam (the UI iterates axes from the data; pressure/framing are never hardcoded).

## Deviations from Plan

- **Shard subdirectory `data/probes/` → `probes/`** (Phase 2 integration): the exporter
  originally nested shards under `<out>/data/probes/`, which produced a redundant
  `data/data/probes/` in the served URL when the export root is `public/data/`. Changed
  to `<out>/probes/` (shard paths `probes/<id>.json.gz`, relative to `index.json`).
  Export, tests, CONTRACT.md, and the plan were updated.
- **`collect.py` left unedited** (Phase 1): the plan listed it as a file to edit, but
  threading `results_path` through `score.py`'s `load()`/`load_judgments()` was
  sufficient — `load_probes()` already takes a `path` and reads bundled `DATA`. Noted
  and confirmed correct by reviewers.
- **Export size + gzip** (Phase 1): the plan estimated ~10–30 MB committed; the real
  export measured ~220 MB plain. Per architect decision, shards are gzip-compressed
  (`.json.gz`, index plain) → ~61 MB committed, full fidelity. The plan (D3) was
  updated to record the measurement and decision.
- **DataSource gzip-serving robustness** (Phase 5): a `vite preview` check revealed that
  some static hosts serve `.json.gz` with `Content-Encoding: gzip` (the runtime then
  decompresses transparently), which broke an unconditional `DecompressionStream`. The
  `loadItem` path now decompresses only when the bytes still carry the gzip magic
  (`0x1f 0x8b`), else parses directly — robust across hosts.

## Lessons Learned

### What Went Well
- **The data contract paid for itself.** Making the viewer generic (subjects / items /
  `conditionAxes` / band ladder / judges) was barely more work than hardcoding, and it
  forced a clean export/UI boundary. The `conditionAxes` abstraction cleanly generalizes
  pressure/framing without the UI knowing either name.
- **Reusing the Python loaders** (`load`, `load_judgments` with the v2 overlay, the
  rescale) kept a single source of truth — the export agrees with the report by
  construction, and the loader refactor was a backward-compatible optional param.
- **The DataSource seam** kept the UI decoupled from fetching; moving the concrete impl
  to the composition root (`main.tsx`) made the seam real and testable with fakes.
- **`vite preview` before merge caught a real production bug** (the gzip double-decompress)
  that unit tests alone would not have — the served-bytes behavior is host-specific.

### Challenges Encountered
- **Export size** was ~10× the estimate; resolved with gzip shards (architect-approved)
  rather than dropping content. Plain-JSON diffability was traded for size, which is fine
  since the gzip shards aren't human-diffed anyway.
- **Gzip-on-the-wire ambiguity**: hosts disagree on whether `.gz` is content or
  transfer encoding. Resolved with magic-byte detection so the client is correct either
  way.
- **Testing-library label ambiguity**: wrapping two controls (filter input + select) in
  one `<label>` named both; fixed by using a caption `<span>` + per-control `aria-label`.

### What Would Be Done Differently
- Measure real export size during the spec/plan phase (a 1-probe dry run) rather than
  estimating — it would have surfaced the gzip decision before plan-approval.
- Decide the served data layout (`public/data/` vs export `<out>` semantics) up front to
  avoid the `data/probes/` → `probes/` adjustment mid-stream.

### Methodology Improvements
- The per-phase 3-way review + rebuttal loop worked well; reviewers caught real issues
  (untrusted-content rendering, fail-soft gaps, the seam not being honored, the missing
  absent-reference test). The Gemini consult sandbox intermittently saw an empty
  workspace on the Python/early phases (false "files missing" REQUEST_CHANGES); worth a
  tooling note so builders don't chase phantom changes.

## Technical Debt
- **npm audit**: 5 advisories in dev-only tooling (transitive build deps); the runtime
  bundle is just React. Not fixed to avoid `audit fix --force` breakage; revisit on a
  toolchain bump.
- **Optional "(unknown id)" marker**: data-internal absent subject/judge ids render as
  the raw id (defensive-only path that never fires on contract-valid data). An explicit
  "(unknown id)" marker is a trivial follow-up if desired.
- **Committed data size** (~61 MB): acceptable per architect, but if it grows, options
  remain (finer sharding, dropping turn-1 rationales, or a small backend — the
  DataSource seam localizes that change).

## Consultation Feedback

Spec, plan, and all 5 implement phases passed 3-way review (Gemini / Codex / Claude).
Notable accepted changes across iterations: data-contract de-baking (spec), untrusted-
content escaping + fail-soft (spec/plan/Phase 4), `--results-path` + loader refactor,
band `color` in the contract, scope-in-URL, the DataSource seam injection at the
composition root, the gzip size decision + serving-robustness fix, and a render-level
absent-reference fallback test. One Codex point was partially rebutted (the defensive
`?? id` fallback is itself the visible, non-crashing state) and accepted on re-review.

## Architecture Updates

- **New top-level `apps/` directory** with the first app, `apps/jaleesbrowser/` — a Vite
  + React + TypeScript static SPA. This is the repo's first front-end and Node toolchain
  (previously Python-only); it is self-contained (build artifacts gitignored).
- **New data-contract seam.** `apps/jaleesbrowser/CONTRACT.md` defines a versioned
  viewer format (`index.json` catalog + gzip per-probe shards). The harness gains a
  `jaleesbench export-web` CLI (`export_web.py`) that is the first producer; the loaders
  in `score.py` (`load`/`load_judgments`) now take an optional `results_path`.
- **Client-side `DataSource` interface** decouples the UI from data access (static-file
  impl only today); a future DB/API source is a localized drop-in.
- **GitHub Pages deploy** via `.github/workflows/pages.yml` — the repo's first CI/CD
  workflow. Builds the committed app + data; never regenerates the (gitignored) export.
- The exported viewer data (~61 MB gzip) is **committed** under
  `apps/jaleesbrowser/public/data/`; raw results stay gitignored.

## Lessons Learned Updates

- **Gzip on the wire is host-dependent.** A `.gz` static asset may be served as content
  (raw bytes) or with `Content-Encoding: gzip` (runtime auto-decompresses). Client code
  that decompresses must detect the gzip magic (`0x1f 0x8b`) and skip decompression when
  the bytes are already plaintext. Verify with `vite preview` (or the real host) before
  merge — unit tests with mocked fetch won't surface this.
- **Generic-in-types, specific-in-data** is a cheap, high-leverage pattern: model the
  abstract shape (subjects/items/axes/bands/judges) in code and carry all
  product-specific values in the exported data. The UI generalizes to new producers for
  near-zero extra cost.
- **Measure derived-artifact size early.** A 1-item dry-run of the exporter would have
  surfaced the ~10× size miss (and the gzip decision) before plan-approval.
- **Consult-sandbox false negatives:** the Gemini consultation occasionally saw an empty
  workspace and reported "files missing" — verify against `git`/the other reviewers
  before chasing phantom changes.

## Flaky Tests
None. The Python suite (52) and the app suite (33) are deterministic; the export and
app data tests use small committed fixtures / the real index, never the raw 190 MB data.
