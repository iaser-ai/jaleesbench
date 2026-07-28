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

## 2026-07-28 — Plan approved (option 1); Phase 1 land_pipeline built

Waleed approved plan-approval; validation decision = option 1 (no bench
validation this project). Implementation started.

Phase 1 done in the worktree: `apps/companion-pipeline/` uv project —
seed's ~1,480 lines ported into config-driven modules (shared `timing.py`
used by BOTH assembly and captions; fail-fast `config.py`; TTS adapter;
cards with per-language CSS + dir; BiDi caption wrapping; recorder +
3 drivers parameterized by language config; upload channel-guard
foundation). EN config verbatim from seed; 3 EN clips + shipped srt
committed as inputs/parity baseline.

**EN parity rebuild PASSED**: rebuilt youtube-chatgpt.mp4 (1080p h264,
69.1s) + srt — 9/9 cues, identical text, starts within ~0.2–1.0s of
shipped (TTS drift only; even the same two clamped segments). 29 pipeline
unit tests + 73 jaleesbench tests green.

Discovery worth noting: the shipped EN chatgpt timeline itself contains
two clamp-pushed segments (offsets 8.3/12.3 vs a ~19s intro VO) — the
`***` markers are working as designed, not a regression.

## 2026-07-28 — Phase 1 unanimously approved (3 review iterations);
## Phase 2 tts_spike: samples generated, WAITING ON HUMAN LISTEN TEST

Phase 1 took 3 review iterations (Codex found real items each round:
env-configurable rec-profile/CDP, honest upload stub, `all` command,
fail-fast config tests, handoff scaffold — all fixed; final round
unanimous APPROVE). Porch advanced to tts_spike.

Phase 2 work done: `companion spike-tts` command (runs through the real
tts.gemini_generate path); ar/ur/id config skeletons (RTL dirs, Naskh/
Nastaliq card CSS with tall line-heights, per-language style prompts,
seeded spellouts; PENDING markers on voice + prompt-dependent fields);
12 samples generated (3 langs × Sulafat/Achird/Charon/Puck).

**KEY FINDING: Gemini TTS produced Urdu audio without error** — the
flight risk has narrowed from "may not work at all" to "is the quality
acceptable", which is the human listen test's call.

**BLOCKED (by design) on human listen test**: architect asked to listen
to out/spike/*.wav and pick a voice per language. Voice record table in
apps/companion-pipeline/reference/tts-spike.md.

## 2026-07-28 — Listen test DONE: Puck × 3; Urdu flight risk CLOSED

Waleed (human ears, via Finder): **Puck for all three languages** —
rationale: voice consistency with the shipped EN videos. Urdu quality on
Gemini TTS accepted; NO fallback chain needed. Recorded in tts-spike.md;
voice=Puck set in all three configs; cache prefixes renamed to
{ar,ur,id}-puck1 so any future voice change can't reuse stale TTS cache.
Phase 2 unblocked → porch done → 3-way review.

## 2026-07-28 — Phase 3 translated_prompts: translations done, matrix 6/9,
## Gemini cells escalated

Phase 2 approved (Gemini/Claude APPROVE, Codex COMMENT → resolved with
validate_skeleton()). Phase 3 work:

- Translations of GUIDE_MIN v3: ar 1,160 / ur 1,318 / id 1,499 chars —
  all ≤1,500. Drafted by builder, cross-checked independently by Gemini
  AND Codex (consult general mode), all reconciled edits applied
  (record: apps/companion-pipeline/reference/translation-review.md).
  Notable: Urdu عطر فروش idiom, id re-trimmed twice to fit budget.
- Configs updated with real prompt_chars + gemini part bounds; prompt-page
  handoff package built (handoff/prompt-page/ with per-language prompt +
  two-part split files).
- LIVE entry matrix vs real assistant UIs: ChatGPT 3/3 PASS, Claude 3/3
  PASS, Gemini 3 cells INCONCLUSIVE (no error-13 seen, but backgrounded-
  window automation couldn't confirm entries — the seed's documented
  visibility gotcha; 2 attempts, stopped per the 2-strikes rule).
- DISCOVERY for the runbook: Claude read-after-write lag is MINUTES —
  false persistence failures until you poll ~3-4 min.
- ACCOUNT STATE (rule honored): ChatGPT restored EN 1,492 ✓ verified;
  Claude restored EN 1,492 ✓ verified (after a mid-run state where the
  id translation had propagated — caught and corrected); Gemini
  saved-info needs MANUAL verification (expected 2 EN entries; strays
  possible from the two attempts).

**WAITING ON ARCHITECT**: Gemini saved-info eyeball + choice on closing
the 3 Gemini cells (visible-window retry now vs Phase 4 on-camera
verification).

## 2026-07-28 — Architect decision: Gemini cells defer to Phase 4 opener

Option (b) ACCEPTED with condition: the 3 Gemini cells close as the FIRST
act of Phase 4 (visible window, per-language, ar first) BEFORE any mass
recording — a rewriter rejection must trigger translation-shortening
before takes are filmed. Recorded as the documented deviation from the
9/9 criterion in translation-review.md. Waleed checking his Gemini
saved-info for strays himself. Phase 3 → porch done → 3-way review.

Review round 1 on Phase 3: Gemini APPROVE; Codex REQUEST_CHANGES with a
REAL catch — my prompt.txt files carried trailing newlines (byte-for-byte
copies would be 1161/1319/1500, blowing id's fit claim). Fixed: files
byte-exact; load_language now validates prompt_chars == len(prompt);
tests assert exactness + handoff-package byte-identity (59 green).

Cross-workspace lesson for the cohort: **builders cannot afx-send to
other workspaces** (NOT_FOUND even for active ones — 'iaser.ai' was
active) — route cross-workspace messages through your architect, who
relayed the prompt-page notice verbatim.

## 2026-07-28 — Phase 3 unanimously approved (iter 2); Phase 4 recordings
## opened with locale-route probes; TWO DEPENDENCIES SURFACED

Phase 3 closed 3×APPROVE. iaser.ai architect logged the prompt-page
notice and added two Phase 8 package-format requirements (localized
section slugs; explicit per-language YouTube-ID statements) — recorded
in plan + handoff/README.

Phase 4 probes (read-only, no settings writes, no screen takeover):
**Gemini ?hl= VERIFIED for ar/ur/id** — ar+ur render full RTL-mirrored
UIs. ChatGPT/Claude ignore ?hl → route = relaunch rec-Chrome with
--lang=<code> (+ possibly ChatGPT account language setting, temporary
with restore). README updated with the route table + per-language
launch command.

**WAITING ON ARCHITECT for two things**:
1. Visible-window session go-ahead for the Gemini-cells closure (first
   act per the Phase 3 deferral condition — ar first, before any takes).
2. Prompt-page staging: on-camera takes copy the translated prompt from
   the LIVE page (drivers assert clipboard == prompt_chars); iaser.ai
   must stage/publish per-language prompt pages (even unlisted paths)
   before recording — relay request sent.

## 2026-07-28 — Prompt pages STAGED (iaser.ai); wired into pipeline;
## HOLD on takes until Waleed's explicit go

iaser.ai staged + byte-verified unlisted pages: iaser.ai/{ar,ur,id}/prompt
(3 pre blocks each: full + gemini part1/2; plain 'Copy' buttons ×3 —
NOT 'Copy prompt' like EN — and each flashes the copied char count:
that flash is the on-camera honesty check for takes). Probed read-only,
wired into configs (real URLs, copy_button_label now config-driven) and
drivers. Translation revisions route through the architect for their
re-vendor. 59 tests green.

**HOLD**: no visible-window session, no takes, until Waleed's baseline
check + explicit go. Remaining Phase 4 work (Gemini cells closure →
per-language recording sessions with Chrome --lang relaunches) is
screen-dependent and waits.

## 2026-07-28 — Gemini cells CLOSED (2nd session, amended rule); one
## finding escalated

First visible session ran under EN UI → HARD STOP from architect →
amended rule: verification must rehearse take conditions (?hl= UIs);
EN-UI cells VOID. No fault assigned; account was verified clean.

Second session (?hl=ar/ur/id, RTL mirrored, Waleed observing):
**ALL THREE CELLS PASS** — two-part paste accepted in every language,
no error-13. End state EMPTY (Delete All + tonal confirm), screenshot-
verified. EN entries NOT reinstalled (Waleed's explicit baseline).

FINDING escalated: Gemini's rewriter LANGUAGE-SWITCHED Arabic part2
into English (ur/id stayed in-language; ar part1 verbatim). Hypothesis:
bare-bullet openings get English summarization; Arabic prose lead-ins
survive. Recommended fix (b): Arabic lead-in line for part2 → via
architect → iaser.ai re-vendor. Automation gotchas recorded in README
(mat-tonal-button confirms, kebab rows, Delete All).

Waiting: architect decision on the ar-part2 fix + recording-session
scheduling (--lang Chrome relaunches).
