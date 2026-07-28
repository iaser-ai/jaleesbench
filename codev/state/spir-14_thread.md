# spir-14 thread — Multilingual companion-prompt assets (AR / UR / ID)

## 2026-07-28 — Session start, Specify phase

Spawned in strict mode for issue #14. Porch says phase = specify; spec file
doesn't exist yet, so I'm authoring it.

Read the seed material at `tmp/companion-video-pipeline/` (main checkout):
PIPELINE.md is a solid runbook — 5 stages (record clips → TTS → assemble →
SRT → upload), ~1,480 lines of Python across recorder/build/srt/upload
scripts, plus the shipped EN outputs (3 videos + srt + gifs source clips).

Key spec-shaping observations:
- Everything language-dependent funnels through a small surface:
  `STYLE` + voice name + VO text in `build_video.py:cfgs()`, `CARD_HTML`
  for intro/outro cards, spell-out mappings in `make_srt.py`, and the
  YouTube "Video language" field in the upload flow.
- Six open questions in the issue, none decided — spec must propose
  answers but keep them visibly open for the human at the spec gate
  (Waleed's standing preference: don't bake recommendations as decided).
- Known risk to surface: Gemini TTS language coverage for Urdu is
  uncertain (Arabic + Indonesian were in the documented language list as
  of my knowledge; Urdu was not) — needs an early listen-test spike.
- RTL (ar, ur) touches cards, SRT, and possibly recorded UI language.
- Article lives in the iaser.ai repo — cross-workspace coordination is a
  dependency, not something this repo can ship alone.

Next: write `codev/specs/14-multilingual-companion-prompt-.md`, then
`porch done 14` → 3-way consultation → spec-approval gate.

## 2026-07-28 — Spec drafted, reviewed, at spec-approval gate

Spec written and taken through the 3-way: Gemini APPROVE, Codex
REQUEST_CHANGES, Claude COMMENT. All feedback incorporated (commit
`cbd83e2`); rebuttal at
`codev/projects/14-multilingual-companion-prompt-/14-specify-iter1-rebuttals.md`.

Notable additions from review: Urdu-TTS failure decision rule with named
fallback providers (ElevenLabs / Azure / OpenAI); storage policy (EN clips
committed directly ~2 MB, outputs gitignored, no git-lfs); secrets/
machine-locality hygiene requirements; mechanical YouTube channel preflight
guard; article handoff package format; BiDi marks + Nastaliq card CSS for
RTL; tightened re-runnability criterion (full non-EN build from clean
checkout).

Six open questions stay OPEN with proposals for the human at the gate —
Q1 (prompt stays English) / Q3 (UIs recorded in English) / Q6 (reuse EN
clips) are coupled and decided together; gate decisions get folded into
§4/§6 before planning.

**NOW AT GATE: spec-approval. Waiting for human.**

## 2026-07-28 — Gate approved with binding decisions; spec revised; plan at gate

Waleed approved spec-approval with all six questions DECIDED (issue #14
gate comment): translated prompts per language; Gemini TTS default;
fresh target-language UI recordings (investigate `?hl=` routes); articles
handed off as proposed; browser-automation uploads; north star =
highest-quality videos. Spec rewritten to the SPIR template with decisions
folded in (commit `663b931`). New requirement surfaced by Q1: translated
prompts must fit ~1,500-char entry fields. One question deliberately open
for the plan gate: JaleesBench validation of translated prompts (3 costed
options in spec).

Plan drafted (8 phases after review split): land pipeline w/ EN parity →
TTS spike → translated prompts → 9 recordings → localized content →
9 builds + QA → guarded uploads → article handoffs. 3-way review: Gemini
APPROVE, Claude APPROVE, Codex REQUEST_CHANGES — all four Codex points
fixed (seed-access prerequisite incl. `../../tmp/` path from worktree,
handoff/ vs out/ contradiction, Phase-5 split, pinned EN article
snapshot). Commit `45d1654`.

**NOW AT GATE: plan-approval. Waiting for human. The gate also carries
the JaleesBench-validation decision (recommend: light validation for ar,
spot-checks for ur/id).**
