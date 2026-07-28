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
