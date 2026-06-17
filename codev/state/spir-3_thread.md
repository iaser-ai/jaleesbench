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
