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
