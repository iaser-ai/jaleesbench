# spir-3 thread — Public results browser (issue #3)

Protocol: SPIR (strict). Worktree: `.builders/spir-3`, branch `builder/spir-3`.

## 2026-06-17 — Specify phase started

Porch state: `specify`, iteration 1. No spec existed; I'm authoring it (this
strict setup has the builder write the artifact, then `porch done` triggers the
3-way consult + spec-approval gate).

### Architect baked decision (received via afx mid-startup)
**Data-contract requirement** — the viewer must be driven by a documented,
versioned DATA CONTRACT (exported index + per-probe schema), with JaleesBench as
the FIRST producer. NOT hardcoded to JaleesBench's fields/dimensions. Keep it
simple: build the clean data-contract seam, ship JaleesBench-first; don't
over-engineer a generic schema engine, don't bake JaleesBench specifics into
UI/types. Captured as a "Data Contract & Extensibility" section in the spec
(spec-approval will review it).

### Data model mapped (from score.py / html_report.py / collect.py + live data)
- Raw data lives in the MAIN checkout `jaleesbench/results/` (gitignored, 190MB
  collect.jsonl) — NOT in this worktree. The Python export must read from there.
- Grid: 8 subjects × 6 pressures × 3 framings × 140 probes = 20,160 sittings;
  2 judges × 2 scopes (full/turn1) = 80,640 judgments. Per probe: 144 sittings,
  576 judgments. Fully populated.
- Sitting: subject, probe_id, pressure, framing, turns[user,asst,user,asst], usage.
- Judgment: subject, probe_id, pressure, framing, judge, scope, band(-2..+2),
  direction, rationale, techniques_used. judgments_v2.jsonl overlays by identity
  (subject,probe_id,pressure,framing,judge,scope); v2 lacks `rationale`.
- Bands: -2 Burns / -1 Sparks / 0 Inert / +1 Scent / +2 Perfume; reported ×0.5
  → −1…+1 (SCORE_SCALE in score.py).
- Probe: id, title, chapter, pillars[], hearts[], islamic(clean/leaky/intrinsic),
  proof_texts, turn1, pressure_turns{pressure->text}.
- Judges: claude-opus-4-8, gemini-3.1-pro-preview.
- Repo iaser-ai/jaleesbench is PUBLIC; Pages base path = /jaleesbench/. Node 26.

Next: write spec, commit, `porch done 3`, then STOP at spec-approval gate +
notify architect.

### Spec drafted + 3-way review done
Spec committed (c2adf66). `porch done 3` → verification; ran 3-way consult.
Verdicts: **Gemini COMMENT · Codex REQUEST_CHANGES · Claude APPROVE** — all
strong, convergent asks. Incorporated all: §5.6 untrusted-content + fail-soft
load errors; `--results-path` + loader refactor in scope; band `color` in
contract; same-subject allowed; responsive + RTL-from-language + a11y; §5.7
relative asset paths; `web/` at repo root; ~10–30MB export size; scope added to
URL. Consultation Log §10 records each. Next: commit reviewed spec, `porch next`,
then expect spec-approval gate → STOP + notify architect (gate is the user's
call, never auto-approve).

### spec-approval feedback (architect) — de-bake the solution; NOT approved
Reached spec-approval gate (porch gate 3), notified architect. Architect did NOT
approve: §3 over-baked the SOLUTION. Requester asked for a tech RECOMMENDATION and
is OPEN to alternatives — TS/Vite/React/Pages/no-backend/shards were NOT their
decision. (New memory exists: "dont-bake-my-recommendations".)
Revised:
- §3 now = FIXED REQUIREMENTS ONLY (public+zero-install; URL deep links; side-by-
  side 2-model + both judges' verdicts; read-only/no harness change; English now;
  §5 data-contract generality; −1…+1 band fidelity) + environmental facts.
- §4 now weighs 4 genuine OPEN decisions (A presentation, B hosting, C data layout,
  D export mechanism) on merit, each a *reasoned recommendation* (no pre-stamped
  REJECTED; backend kept on the table). Summary recommendation in §4.E.
- App location → apps/jaleesbrowser/ (architect inline note; name flagged as
  suggestion given contract producer-neutrality).
- ALL substantive review fixes retained (§5 contract, §5.6, --results-path, band
  color, scope-in-URL, responsive/RTL/a11y).
- §9 crit 5 generalized off hard-Pages; §5.7/§7 reference recommendations not bakes.
Gate still pending (WAITING FOR HUMAN APPROVAL). Commit + re-notify architect; do
NOT porch approve.

## 2026-06-17 — Plan phase

spec-approval APPROVED by human (architect). `porch next` → plan phase.
Architect added a new OPEN plan decision to carry: a thin client-side **DataSource
seam** (`loadIndex()`/`loadItem(id)`) the UI depends on, static-file fetcher the
ONLY impl now; NO DB adapter/API client/query layer (YAGNI). Recommend it; requester
decides at plan-approval.

Wrote plan (5 linear phases): 1 export CLI+contract → 2 scaffold+DataSource seam+
types → 3 pickers+URL state → 4 side-by-side compare+verdicts+legend → 5 static
build+Pages deploy+real export. Machine-readable phases JSON present; porch checks
(plan_exists / has_phases_json / min_two_phases=5) all PASS. Open decisions section:
D1 DataSource seam (architect, recommended), D2 stack assumptions from spec §4
(confirm/redirect), D3 shard encoding. PR strategy: phases = git commits on ONE
branch, single PR after final implement phase.
Next: commit plan, `porch done 3` → 3-way plan consult → expect plan-approval gate
→ STOP + notify architect.

### Plan 3-way review done
`porch done 3` (checks pass) → consult. Verdicts: **Gemini APPROVE · Codex
REQUEST_CHANGES · Claude APPROVE** (Claude verified loaders/v2/SCORE_SCALE against
code — all correct). Incorporated all: searchable question picker (P3); full
fail-soft enumeration index/shard fetch+malformed+version+missing-cell+absent-ref
(P4); explicit DOM test stack vitest+jsdom+@testing-library (P2); band colors
DEFINED in exporter (BAND_NAMES is html_report.py:17, no 5-color palette exists)
(P1); collect.py precision = only RESULTS needs overriding (P1); Vite base "./"
relative (P2/P5); turn-row alignment across columns (P4); container-level RTL (P4).
Consultation Log added to plan. Next: commit, rebuttal, porch done → plan-approval
gate → STOP + notify architect (never auto-approve).

## 2026-06-18 — Implement phase, Phase 1 (phase_1_export)

plan-approval APPROVED. `porch next` → implement / phase_1_export.

### Merge race (resolved)
Architect msg1 said `git fetch origin && git merge origin/main` to get the
uv/pytest check override (protocol.json). I did it (merge commit cd44030). Then
msg2 said "DISREGARD, do NOT merge". Then msg3 resolved: LEAVE the merge as-is (no
revert), it correctly points the implement check at uv/pytest. **PAUSE before
`porch done 3`** — architect will confirm how the check resolves (maybe a cleaner
.codev/config.json swap). Do NOT run the implement check yet.

### Phase 1 built (UNCOMMITTED — porch commits after review)
- score.py: threaded optional `results_path` into load()/load_judgments()
  (default RESULTS unchanged → existing tests still pass; monkeypatch-friendly).
  collect.py NOT touched (threading via score.py suffices; load_probes already
  takes a path arg + reads bundled DATA). Minor deviation from plan's file list,
  intent met.
- export_web.py (new): `export_web(results_path, out_dir, limit)` → contract-shaped
  index.json + data/probes/<id>.json. Generic (subjects/items/conditionAxes/bands/
  judges/scopes). Slim (drops usage/raw/attempts/context_prefix). Deterministic
  (sort_keys, fixed orderings) → idempotent. Bands display scale −1…+1; 5-color
  ramp defined here (BAND_LADDER). v2 missing-rationale tolerated. Fail-loud on
  unexpected band.
- cli.py: added `export-web` command (--out, --results-path, --limit).
- tests/test_export_web.py (new): 8 tests. **Full suite 52 passed** (uv run pytest).
- apps/jaleesbrowser/CONTRACT.md (new): versioned contract reference.
- Real-data smoke (--limit 2): valid index + 144-cell shards, 4 turns, 4 verdicts.

### ⚠️ SIZE FINDING (needs architect decision)
Real smoke: 2 shards = 3.2 MB → ~1.6 MB/probe → **~220 MB for 140 probes**, ~10×
the plan/spec §7-C1 ~10–30 MB estimate. Bulk = 576 judge rationales/probe +
transcripts (can't drop without losing the feature). Prompt-dedup (D3) won't fix
it (prompts are a small fraction). Real levers: gzip-committed shards (+DataSource
decompress) ≈ ~30 MB; or finer sharding (per probe×subject — reduces per-fetch not
total); or drop turn-1 rationales (~halve); or accept. This is the spec's "confirm
repo-size impact at review" checkpoint, arriving early. **Flagged to architect;
paused for their call** (also affects Phase 2 DataSource + Phase 5 commit).

PAUSED before `porch done 3` per architect. Two items for architect: (1) confirm
implement-check mechanism, (2) size strategy decision.

### Both decisions resolved (architect)
(1) Run implement check normally — merged override makes it uv/pytest + pass.
(2) SIZE → GZIP: shards written as gzip `.json.gz`; index.json plain; shards
paths point at `.json.gz`; StaticFileDataSource decompresses via
DecompressionStream('gzip'). Amended export_web.py (`_write_json_gz`,
mtime=0 → idempotent), tests (read via gzip.decompress), CONTRACT.md.
Re-smoke (limit 4): ~445KB/gzipped shard → **~62 MB committed** for 140 probes
(gzip ~3.5× here — rationale-heavy text — not 7×; still 3.5× better than 220MB,
per-fetch ~445KB/probe fine). 52 tests pass. UNBLOCKED → running `porch done 3`
(implement check + 3-way impl review).

### Phase 1 impl check + 3-way review
Committed phase 1 (6b29c77) so consult sees full diff. `porch done 3` implement
check (uv/pytest via override) PASSED. 3-way impl consult:
**Gemini APPROVE (sandbox saw no files — plan-based) · Codex REQUEST_CHANGES ·
Claude APPROVE (verified code, 52 pass)**. Codex asks (both doc reconciliation):
(1) plan + Phase 2 DataSource still said plain-JSON shards — reconciled plan to
gzip (D1/D3/P1/P2/P5 + consult-log); (2) CONTRACT.md said ~30MB/~7× — fixed to
~62MB/~3.5%. Claude minor: summary emitted null when direction absent → now
conditional (matches rationale). Rebuttal written. Tests still 52 pass. Next:
commit review fixes, `porch done 3` → expect phase advance to phase_2_scaffold.

### Phase 1 APPROVED (iter 2 unanimous) → Phase 2
Committed review fixes (680c1e1). porch done → iter-2 re-consult (porch generated
iter2-context.md from rebuttal). **iter 2: Gemini/Codex/Claude ALL APPROVE.** porch
advanced to **phase_2_scaffold** iteration 1. Note: porch implement check stays
`uv run --directory jaleesbench pytest -q` (Python) for every phase per architect —
the TS build+Vitest are verified by me (phase acceptance) + Pages CI.

## 2026-06-18 — Phase 2 (phase_2_scaffold)
Vite+React+TS app at apps/jaleesbrowser/: contract.ts (types), datasource.ts
(DataSource interface + StaticFileDataSource w/ gzip DecompressionStream + version
check), minimal App smoke view, Vitest+jsdom+@testing-library. Mini-fixture in
public/data/. Verify TS build+test myself.

### Phase 2 built + verified
Scaffold: package.json (React18/Vite6/Vitest2/TS5.7), tsconfig (base ./, strict),
vite.config (base:"./", jsdom test env), vitest.setup, index.html, .gitignore
(node_modules/dist). src/: contract.ts (generic types, no JB strings),
datasource.ts (DataSource iface + StaticFileDataSource: gzip via
DecompressionStream + version check + UnsupportedVersionError), App.tsx (smoke:
counts from index), main.tsx, datasource.test.ts (6: index load/version/malformed/
non-OK/gunzip/missing-id — gzips via CompressionStream to stay web-standard),
App.test.tsx (2: renders counts via fake DataSource; fail-soft alert).
**npm run build (tsc+vite) ✓; npm test 8/8 ✓; dist uses relative ./assets/.**
Integration cleanup: exporter shard dir `data/probes/`→`probes/` (avoids double
`data/` in served URL); updated export_web.py + test_export_web.py + CONTRACT.md +
plan. Fixture regenerated (public/data/index.json + probes/JLS-001.json.gz, 464KB).
Full python suite 52 ✓. npm audit: 5 vulns in dev tooling (transitive) — not
touching runtime bundle (just React); left as-is (audit fix --force risks breakage).
Next: commit Phase 2, porch done → 3-way review.

### Phase 2 3-way review (iter 1)
Committed eb816e0, porch done (check pass), consult: **Claude APPROVE · Codex
REQUEST_CHANGES · Gemini REQUEST_CHANGES (false positive — empty consult sandbox
again, same as P1)**. Codex (both fixed): (1) App.tsx instantiated concrete
StaticFileDataSource → moved to main.tsx (composition root), App takes required
`dataSource: DataSource` prop, imports only the interface type — seam now real;
(2) datasource.test.ts used stale `data/probes/` synthetic path + didn't test real
fixture → fixed synthetic path to `probes/`, added URL-resolution assertion
(baseUrl ./data/ + probes/… → /data/probes/…), added committed-fixture test
(asserts v1 + relative probes/ paths). Build ✓, **9 app tests** ✓. Gemini rebutted
(files exist, committed, Claude verified them). Next: commit fixes, porch done → iter2.

### Phase 2 APPROVED (iter 2 unanimous) → Phase 3
iter 2: all three APPROVE. porch advanced to phase_3_pickers_url.

## 2026-06-18 — Phase 3 (phase_3_pickers_url)
Built: urlstate.ts (Selection type; defaultSelection/decodeSelection/encodeSelection
— generic over conditionAxes, fail-soft: invalid params → defaults), urlstate.test.ts
(7: defaults, round-trip, generic axis encoding, missing→default, invalid→default,
same-subject a=b, no-scopes). Pickers.tsx (searchable question picker + 2 model
selects + one select per axis + scope select — ALL from index, no JB strings).
App.tsx rewired: decode URL on load, replaceState on change, popstate restore,
selection summary (Phase 4 replaces w/ comparison). App.test.tsx (6): default
pickers, URL write on change, deep-link restore, invalid deep-link→defaults,
question filter, fail-soft. Fixed: question block was a <label> wrapping BOTH filter
input + select → ambiguous getByLabelText; made it a <div> w/ caption span + per-
control aria-labels. **Build ✓, 20 app tests ✓, python 52 ✓.** Next: commit, porch
done → 3-way review.

### Phase 3 APPROVED (iter 1 unanimous, no issues) → Phase 4

## 2026-06-18 — Phase 4 (phase_4_compare) — core UX
Built: format.ts (bandColor w/ producer color + positional fallback ramp; signed();
cellKey/indexCells — cells indexed by subject+axis-values in axis order) +
format.test (4). components/: BandLegend.tsx (BandChip + legend from index.bands),
Verdicts.tsx (per-judge band chip+label+summary+rationale, scope-filtered, missing
rationale tolerated, escaped text), Comparison.tsx (2-col grid, column-grouped DOM +
CSS subgrid for turn row-alignment, TurnCell w/ white-space:pre-wrap, missing cell →
"no data"), Comparison.test (6: both columns, polarizing +1/-1, missing rationale,
XSS literal <script>, scope filter, missing cell). styles.css (grid/subgrid,
responsive stack @720px, band chips). App.tsx: lazy shard load cached by item id +
dir from dataset.language (RTL) + BandLegend + Comparison + shard fail-soft alert.
App.test +2 (legend+comparison mount; shard-fail fail-soft). main.tsx imports
styles.css. **Build ✓ (emits CSS), 31 tests / 5 files ✓.** Next: commit, porch done.

### Phase 4 3-way review (iter 1)
**Claude APPROVE · Gemini APPROVE · Codex REQUEST_CHANGES.** Codex: absent
subject/judge/axis refs (1) judgeLabel/subjectLabel `?? id` silent, (2) not tested.
Response: added render-level test (URL ?a=ghost → comparison shows default "ansari",
not "ghost"; bad axis → default) — 32 tests ✓. Rebutted #1: selection-level absent
refs ARE handled in decodeSelection (correct layer, guaranteed valid by render time);
`?? id` is defensive-only (never fires on contract-valid data since exporter derives
subjects/judges from same data) + showing the id IS the visible non-crashing state;
judges aren't a selection axis so no "default" to substitute. Offered "(unknown id)"
marker as trivial follow-up if architect prefers. Next: commit, porch done → iter2.

### Phase 4 APPROVED (iter 2 unanimous) → Phase 5

## 2026-06-18 — Phase 5 (phase_5_deploy) — ship it
- Generated FULL English export → apps/jaleesbrowser/public/data: index.json +
  **140 gzipped shards, 61 MB** committed (matches ~62MB projection). Raw data stays
  gitignored. Clean (140 .gz + 1 .json, no secrets/jsonl).
- .github/workflows/pages.yml: build apps/jaleesbrowser (npm ci + npm run build) +
  deploy via actions/deploy-pages on push to main (paths apps/jaleesbrowser/**) or
  manual dispatch. Builds committed app+data, does NOT regenerate export.
- README.md: dev/build/test/regenerate-data/deploy docs.
- **⚠️ BUG caught by `vite preview` check (plan-mandated):** server serves .json.gz
  with `Content-Encoding: gzip` → fetch AUTO-decompresses → my DecompressionStream
  double-decompressed → Z_DATA_ERROR. Hosts differ (Pages may/may not). FIX: DataSource
  now reads arrayBuffer, decompresses ONLY if bytes still start with gzip magic
  0x1f8b, else parses directly (handles both transparent-decompress + raw-gz hosts).
  Added datasource.test for the pre-decompressed case. CONTRACT.md consumption note
  updated. Re-verified end-to-end via vite preview: gzipped-on-wire=false → parsed
  direct, 140 items, 144 cells, bands OK.
- Build ✓ (relative ./assets/ + 140 shards in dist), **33 tests ✓**.
Next: commit, porch done → 3-way review → PR.

### Phase 5 APPROVED (iter 1 unanimous, no issues) → REVIEW phase
All 5 implement phases done. porch → review phase. Wrote
codev/reviews/3-public-results-browser-side-by.md (spec compliance §9.1-15 all met,
deviations: data/probes→probes, collect.py unedited, gzip size, gzip-serving fix;
lessons; debt; consult summary; no flaky). Next: commit review, porch done → review
consult → PR gate (human). PR = single PR after final implement phase (per PR strategy).

### PR opened (#4) + review 3-way (iter 1)
Wrote review doc (+ Architecture Updates + Lessons Learned Updates sections for porch
checks). Pushed branch, opened **PR #4**, recorded via porch done --pr 4. Review checks
pass. Review consult: **Claude APPROVE · Codex COMMENT · Gemini REQUEST_CHANGES.**
- Gemini (FIXED): format.ts committed as BINARY — stray NUL byte (0x00) at cellKey
  `.join()` separator! Valid UTF-8 so build tolerated, but git→binary (undiffable).
  Replaced NUL → "|". Verified 0 NUL in committed blob, git grep finds it. Scanned all
  src — only format.ts affected (other NULs are legit .gz/.node binaries).
- Codex (COMMENT, ADDRESSED): items[].tags + item.context exported but never rendered
  (spec §5.3). Added generic ItemHeader.tsx (title + opaque tags as <dl> + context in
  <details>, escaped) above comparison + ItemHeader.test (2). Wired into App + styles.
Build ✓, **35 tests** ✓ (Python 52 ✓). Rebuttal written. Next: commit, push, porch
done → iter2 re-consult → PR gate (HUMAN — never auto-approve).

### PR-gate feedback (architect/requester reviewed live app) — 7 revisions, NOT approved
Implementing on builder/spir-3, update PR #4, re-present at pr gate:
1. Markdown for responses + rationales (markdown-it html:false + DOMPurify; keep §5.6).
2. Collapsible response boxes (~10 lines, expand/collapse) for responses + long rationales.
3. Sans-serif font throughout.
4. Per-model score header per column: "model (+0.75 initial, +0.5 post pressure)" =
   mean of 2 judges, turn1(initial) + full(post), −1…+1. Optional overall avg.
5. Preset example sets (computed in export → index.json presets): (a) models split/
   poorly (widest cross-model spread), (b) judges disagreed (≥2-band). Menu in UI.
   Data confirms: 3231 ≥2-disagree cells, 1176 spread≥3 native.
6. Intro/explanation panel + link to paper (docs/paper/jaleesbench-paper.pdf via GitHub
   blob URL; DRAFT under review).
7. Light/dark toggle, persisted localStorage, default prefers-color-scheme.
Keep contract/DataSource seam/fail-soft/escaped-non-markdown. Bump contract 1.0→1.1
(additive: presets + subjects[].scores). Update spec/plan/contract.

### SUPERSEDED → ELEVATED VISION (architect msg 2) — rolled back to specify
Architect STOPPED the 7-item plan: MVP is a "cell viewer", not an EXPLORATION tool.
Raise the bar. Build ON existing foundation (export/contract/DataSource/drill-in carry
forward — don't discard). **porch rollback 3 specify** done (review→specify). Rewrote
spec to elevated vision:
- 4 surfaces: (1) ORIENT panel (construct/axes/controls/paper link), (2) OVERVIEW
  leaderboard (Jalees Score + recognition gap + pressure effect), (3) COMPARE =
  CENTERPIECE (pick A+B → cells ranked by divergence + agree + summary → click → detail),
  (4) DRILL-IN (markdown+collapsible+sans-serif+score header+verdicts). + PRESETS +
  light/dark + URL-state-for-every-view.
- KEY ARCH: compact **scoreMatrix** in index.json (subject×item×pressure×framing×scope →
  mean band, ~40320 nums ~250KB) so overview/compare are INSTANT, no shard loads; heavy
  transcripts lazy on drill-in only. subjects[].scores + presets + paper added.
- Contract 1.0→1.1 additive; graceful degrade if matrix absent. §5.6 markdown sanctioned
  (markdown-it html:false + DOMPurify). PR #4 NOT approved.
Next: commit spec, porch done → consult → spec-approval gate (re-present elevated vision).
