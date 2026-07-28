# Specification: Multilingual companion-prompt assets (Arabic, Urdu, Bahasa Indonesia) on a reproducible pipeline

<!--
SPEC vs PLAN BOUNDARY: this spec defines WHAT and WHY. CLI command shapes,
directory layout, and stage-by-stage implementation live in the plan.
-->

## Metadata
- **ID**: spec-2026-07-28-multilingual-companion-prompt
- **Status**: revised after spec-approval gate — binding decisions folded in
- **Created**: 2026-07-28
- **Issue**: #14
- **Protocol**: SPIR

## Clarifying Questions Asked

The issue posed six open questions, explicitly undecided. The draft spec
carried proposals with counterpoints; all six were **decided by Waleed at the
spec-approval gate** (issue #14 gate comment, 2026-07-28). These decisions
are binding:

| # | Question | Decision |
|---|---|---|
| Q1 | Does the prompt ship translated per language? | **YES — translated per language.** "Don't ask people to paste something they don't understand." |
| Q2 | TTS engine/voice per language? | **Gemini TTS stays the default** engine/voice family; listen-test spike as specced; fallback chain only if a language fails the listen test. |
| Q3 | Are assistant UIs recorded in the target language? | **YES — recorded in the target language** (accepted that this triples recording work). Investigate the `?hl=`/locale-parameter route (plan-level HOW). |
| Q4 | Where do localized articles live; who publishes? | **As proposed**: authored here, handed to the iaser.ai workspace; done = acknowledged handoff. |
| Q5 | Upload mechanics? | **Browser automation.** (Data API rejected because unverified-app uploads via `videos.insert` are permanently locked private — not an API-capability issue.) |
| Q6 | Reuse EN recordings vs fresh? | **FRESH recordings per language** (follows Q1+Q3). EN clips remain the reference; the recording stage's per-language path is exercised for real. |

**North star (Waleed, verbatim intent): focus on producing the
highest-quality videos. Where quality and effort trade off, quality wins.**

One sub-question opened by Q1 remains open for the human at the next gate:
whether/how translated prompts get JaleesBench validation (§ Open Questions,
with options and costs).

## Problem Statement

The English companion-prompt launch produced a full outreach suite — an
article on iaser.ai, per-assistant UI walkthrough recordings, and three
narrated videos (ChatGPT / Claude / Gemini) with exact-timeline captions,
uploaded Private to the iaser-ai YouTube channel. The production process was
a one-off: ~1,480 lines of working Python plus a runbook (`PIPELINE.md`)
rescued into gitignored `tmp/companion-video-pipeline/`, outside version
control and hardcoded to English.

The audiences the companion prompt most needs to reach include large
Muslim-majority populations whose languages are Arabic, Urdu, and Bahasa
Indonesia. Producing those language suites by hand would re-derive the whole
process three more times; the process knowledge would decay again.

## Current State

- The EN pipeline exists only as rescued seed material in gitignored `tmp/`:
  recording harness + per-assistant drivers (Playwright over CDP), a TTS +
  assembly script (Gemini TTS, ffmpeg), an SRT generator sharing the same
  timing logic, and upload notes/scripts (Playwright against YouTube
  Studio). Everything language-dependent — voice, style prompt, VO text,
  card HTML, spell-out tables — is hardcoded EN inline.
- EN assets shipped: article at iaser.ai/articles/jaleesbench-companion-prompt;
  three videos Private pending review (youtu.be/f5gvS4_pa1I ChatGPT,
  youtu.be/YCu0NDjxbY4 Claude, youtu.be/aN3ICiEx-pI Gemini) with `.srt`
  captions.
- The canonical prompt is **GUIDE_MIN v3** (1,492 chars, English), public at
  s.iaser.ai/prompt.
- No Arabic/Urdu/Indonesian assets exist. No re-runnable pipeline exists.

## Desired State

1. **The pipeline is a first-class, in-repo, re-runnable system**: all
   per-language content lives in data/config, not code; adding language N+1
   means adding one config + translations and re-running. The `PIPELINE.md`
   process knowledge (recording rules, wedged-Chrome recovery, upload
   gotchas) ships as its documentation.
2. **Three new language suites exist (ar, ur, id), mirroring EN**, each:
   - a **translated companion prompt** (the prompt itself ships in the
     target language — Q1),
   - a localized article source + walkthrough GIFs/screenshots, handed to
     the iaser.ai workspace,
   - three narrated videos (ChatGPT / Claude / Gemini) with **UI recorded in
     the target language** (Q3, Q6 — fresh recordings), localized narration
     (Gemini TTS — Q2) and intro/outro cards, exact-timeline `.srt`,
   - uploaded **Private** to the iaser-ai YouTube channel
     (`UCF1yEgoyLfbgTUpeMn2ruqA`) with correct Video language and captions
     attached (browser automation — Q5).
3. Total new videos: **9** (3 languages × 3 assistants), built to the
   highest-quality bar (north star).

## Stakeholders

- **Primary users**: Arabic-, Urdu-, and Bahasa Indonesia-speaking audiences
  — the outreach targets.
- **Business owner / decision authority**: Waleed (iaser-ai) — reviews and
  publishes videos; decided the gate questions.
- **Secondary**: the iaser.ai workspace architect — owns the article site
  and the prompt page; receives handoffs (articles, translated prompt text).
- **Technical team / maintainers**: this builder now; anyone re-running the
  pipeline for language four or a prompt v4 refresh later.

## Success Criteria

- [ ] **Pipeline landed in-repo** with README runbook; the EN config
      rebuilds the shipped ChatGPT video + `.srt` reproducing the EN
      timeline. Parity, mechanically: same segment count, same VO text,
      same configured offsets, SRT cue starts matching the shipped EN
      `.srt` within TTS-duration drift; waveforms/exact durations may
      differ (TTS is nondeterministic) — byte-identity not required.
- [ ] **Translated prompts** for ar/ur/id produced and reviewed (same
      review bar as narration, below); each fits the assistants' entry
      constraints (EN GUIDE_MIN at 1,492 chars sits just under ChatGPT's
      ~1,500-char custom-instruction field; translations must too);
      the Gemini two-part paste workaround re-verified **per language**;
      translated prompt text delivered to the iaser.ai workspace for the
      prompt page.
- [ ] **Language configs** for ar, ur, id: voice (listen-test approved),
      style prompt, translated VO, RTL-correct cards, spell-out tables.
- [ ] **9 fresh target-language UI recordings** (3 assistants × 3
      languages) showing the real flow — prompt page copy → assistant
      settings → paste → save → verification exchange — with the assistant
      UI displayed in the target language.
- [ ] **9 videos + 9 `.srt`** built with no timeline collisions (the
      existing `***` collision check), uploaded **Private** to the iaser-ai
      channel — each upload passing the channel preflight guard — with
      correct Video language and captions attached; video IDs recorded and
      sent to the architect for review.
- [ ] **3 localized article sources** (+ GIFs/screenshots) delivered to the
      iaser.ai workspace in the agreed handoff package format; handoff
      acknowledged.
- [ ] **Re-runnability demonstrated, not asserted**: one full non-EN build
      path (TTS → assembly → captions for at least one language) runs from
      a clean checkout following only the README; stages with unavoidable
      manual prerequisites (record: logged-in Chrome profile; upload: same
      + channel access) have those prerequisites verified as accurately
      documented.
- [ ] **Translation review recorded** for each language and each artifact
      class (prompt, narration, article) — minimum bar: a strong-model
      cross-check against the EN source; competent human speaker review
      preferred where available. Who/what checked each is recorded.
- [ ] **RTL spot-checks pass**: Arabic/Urdu cards render correctly
      (direction, fonts — Nastaliq for Urdu without vertical clipping —
      embedded LTR URLs), YouTube caption display verified on the uploaded
      videos including BiDi behavior around LTR tokens.
- [ ] Documentation updated (pipeline README; arch docs per protocol R
      phase).

*(Template's ">90% test coverage" criterion: N/A as a blanket number — this
is a media pipeline whose outputs are judged by human review; automated
tests cover the timing/caption/config logic, per Test Scenarios below.)*

## Constraints

### Technical Constraints
- **Fixed by gate decisions**: translated prompts (Q1); Gemini TTS default
  (Q2); target-language UI recordings, fresh per language (Q3/Q6);
  browser-automation uploads (Q5); articles authored here, published by the
  iaser.ai workspace (Q4).
- **Quality north star**: highest-quality videos; quality beats effort.
- Uploads go **only** to the iaser-ai channel, **always Private**; never
  the Google login's default (personal) channel. Enforced mechanically:
  channel-pinned Studio URLs plus a preflight asserting the active channel
  ID on-page before the upload flow; mismatch aborts.
- Recording requires a Chrome profile logged into the three assistants and
  the YouTube-owning Google account; TTS requires `GEMINI_API_KEY`
  (repo-root `.env`). `ffmpeg`/`ffprobe` on PATH.
- **Storage policy**: UI clips (EN reference + new per-language recordings)
  are committed directly as pipeline inputs (single-digit MB each; repo is
  canonical source; no git-lfs — repo has none configured). Generated
  artifacts (TTS caches, card PNGs, assembled videos, `.srt`) are
  regenerable outputs, gitignored. Article-bound GIFs/screenshots travel in
  the handoff package.
- **Secrets/machine-locality hygiene**: no hardcoded user/machine paths
  (profile dir, ports, output dirs come from config/env); secret setup
  documented; no credentials, cookies, or browser-profile artifacts ever
  committed.
- **RTL mechanics** (ar, ur): card templates accept per-language CSS
  overrides (font family, line-height, size, `dir`) — Nastaliq's tall
  vertical metrics clip in an EN-tuned layout; caption generation wraps
  embedded LTR tokens (URLs, brand names) in Unicode BiDi marks
  (U+200E/U+200F) inside RTL cues.
- Repo hygiene: explicit `git add`, `[Spec 14]` commit prefixes, no
  attribution lines; Python via `uv`; CLIs use Typer.

### Business Constraints
- Videos remain Private until Waleed reviews and publishes.
- The article site and prompt page belong to the iaser.ai workspace —
  this project's boundary is an acknowledged handoff, not publication.
- Translated prompts are outreach artifacts of a bench-validated EN
  original; the validation question for translations is explicitly open
  (§ Open Questions) and its resolution is a human decision.

## Assumptions

- The EN seed scripts still run against current assistant UIs (they did on
  2026-07-27); UI drift is handled as it surfaces during fresh recordings.
- Assistant UIs can be displayed in ar/ur/id — via `?hl=` (known for
  Gemini) or account/browser-locale settings (ChatGPT/Claude); the exact
  route is plan-level investigation. If an assistant cannot render a target
  language UI, that surfaces as a blocker to the architect, not a silent
  fallback.
- Gemini TTS can produce acceptable ar/id; **Urdu is the flight risk** —
  the documented language list has included Arabic and Indonesian but not
  (as of this author's knowledge) Urdu. The listen-test spike is the first
  implementation act and can invalidate downstream assumptions.
  **Decision rule if a language fails the Gemini TTS listen test**: evaluate
  the fallback chain — ElevenLabs multilingual, Azure Speech (dedicated
  `ur-PK`/`ur-IN` voices), OpenAI TTS — same listen test; if none passes,
  escalate to the architect as a scope decision. Other languages proceed
  regardless; engine+voice live in per-language config, so a provider swap
  is an adapter, not a redesign.
- The Gemini entry-rewriter error (13) that forced the EN two-part paste
  is presumed present in all languages until re-verified per language.
- The iaser.ai workspace will cooperate on handoffs (articles, prompt
  page); its publication timeline is outside this project's control.

## Solution Approaches

### Approach 1: Single data-driven pipeline, per-language config (CHOSEN)
**Description**: Land the EN seed as one pipeline whose stages take a
language parameter; everything language-dependent (prompt text, voice,
style, VO scripts + offsets, card text/CSS, spell-outs, YouTube metadata,
text direction) lives in per-language config/data. EN is the reference
config and regression baseline.

**Pros**: adding a language is config + translations, not code; single
timing/caption engine keeps EN's hard-won ffmpeg/SRT fixes for every
language; EN parity rebuild acts as a regression test; process knowledge
consolidates in one README.
**Cons**: upfront refactor of working one-off scripts (risk of breaking
what worked); config schema must anticipate per-language variance (RTL,
fonts, per-assistant locale routes).
**Estimated Complexity**: Medium · **Risk Level**: Medium

### Approach 2: Fork the EN scripts per language
**Description**: Copy the seed three times; hand-edit VO text, voice, cards
per copy.

**Pros**: fastest first asset; zero refactor risk to the EN flow.
**Cons**: violates the issue's core requirement (re-runnable pipeline);
four diverging copies of timing logic; every future fix ×4; process
knowledge decays again.
**Estimated Complexity**: Low (short-term) · **Risk Level**: High
(long-term). **Rejected** — the issue names the pipeline as the deliverable.

### Approach 3: Full i18n framework / external localization tooling
**Description**: Adopt a localization toolchain (message catalogs,
translation-management service) around the pipeline.

**Pros**: scales to many languages/translators; structured review flows.
**Cons**: heavy machinery for 3 languages × ~10 strings-groups; the
"catalog" here is long-form VO scripts and articles, which TMS tooling fits
poorly; adds dependencies and learning cost with no quality gain.
**Estimated Complexity**: High · **Risk Level**: Medium. **Rejected** —
over-engineering at this scale.

## Open Questions

### Critical (blocks final delivery decision — for the human at the next gate)
- [ ] **JaleesBench validation of translated prompts** (opened by Q1's
      decision). The EN prompt is bench-validated; translations are new
      artifacts. Options, with costs:
      1. **No bench validation** — qualitative spot-checks only (the
         recorded verification exchanges double as smoke tests). Cost: ~0.
         Risk: we ship prompts whose measured effect is unknown.
      2. **Light validation** — run a reduced probe subset with/without the
         translated prompt per language and confirm a directionally
         positive effect. JaleesBench already has an Arabic arm to draw on;
         ur/id probe subsets would need translation of a small probe
         sample. Cost: modest API + judge spend per language, a few days'
         effort; ur/id probe translation is new work.
      3. **Full validation** — full JaleesBench run per translated prompt.
         Cost: high (full harness runs + judging ×3 languages, plus full
         probe translation for ur/id); likely its own follow-up project.
      *Recommendation (open, not decided): option 2 for Arabic (arm
      exists), option 1 for ur/id in this project, with option 3 as
      follow-up if results warrant.*

### Important (affects design — resolved during plan/implementation)
- [ ] Per-assistant route to a target-language UI (`?hl=` vs account
      setting vs browser locale) — plan-level investigation (Q3 rider).
- [ ] Whether translated prompts fit every assistant's entry constraints
      in all three languages (char limits, Gemini rewriter) — verified
      empirically early; failure = shorten translation, not silently trim.
- [ ] Which Gemini TTS voice per language passes the listen test (and
      whether Urdu needs the fallback chain).

### Nice-to-Know (optimization)
- [ ] Whether narration segment offsets need per-language retiming (ar/ur/id
      VO runs longer than EN for the same content) or the clamping rules
      absorb it.
- [ ] Whether YouTube auto-translates Private video metadata for review
      convenience (cosmetic).

## Performance Requirements
- **Video output**: 1080p, matching the EN suite's format and quality bar.
- **North star**: production quality of the videos outranks throughput or
  effort; no latency/throughput/SLO requirements apply. Otherwise **N/A**
  (offline batch pipeline, human-in-the-loop).

## Security Considerations
- No credentials, cookies, or browser-profile artifacts in the repo
  (gitignore coverage verified as part of landing the pipeline).
- `GEMINI_API_KEY` stays in gitignored `.env`; README documents setup
  without embedding secrets.
- Upload guard (Constraints) is the control against the high-impact
  failure mode of touching the wrong YouTube channel.
- Recorded clips must not capture unrelated personal account content
  (recordings reviewed before commit).

## Test Scenarios

### Functional
1. **EN parity rebuild** (happy path): EN config → build + captions →
   timeline matches shipped EN structure per the mechanical parity
   definition; collision check clean.
2. **Non-EN clean-checkout build**: fresh clone, README-only setup, one
   full ar/ur/id build path (TTS → assembly → captions) succeeds.
3. **Collision guard**: a config with overlapping segment offsets is
   clamped non-overlapping (unit-testable timing logic, shared by video
   and SRT).
4. **RTL caption generation**: RTL cue containing an LTR URL + brand name
   carries correct BiDi marks; readable-text mapping (spell-out →
   `s.iaser.ai/prompt`) works in each language.
5. **Card rendering**: ar (Naskh) and ur (Nastaliq) cards render with
   correct direction and fonts, no vertical clipping (visual check
   against reference renders).
6. **Channel preflight**: upload flow aborts when the asserted channel ID
   is absent/mismatched; proceeds only on `UCF1yEgoyLfbgTUpeMn2ruqA`.
7. **Two-part paste**: per language, the translated prompt enters Gemini
   successfully via the two-part flow (error-13 workaround holds).
8. **Prompt length**: each translated prompt fits each assistant's entry
   field (empirical check per assistant × language).

### Non-Functional
1. **Listen tests**: per language, candidate voices × sample narration,
   human listen-check recorded (spike output).
2. **Quality review**: each finished video reviewed start-to-finish before
   upload (narration sync, card timing, UI legibility) — north-star gate.
3. Load/perf/security scans: **N/A** (offline pipeline; no service
   surface).

## Dependencies
- **External services**: Gemini TTS API (+ fallback chain if needed:
  ElevenLabs / Azure Speech / OpenAI TTS); YouTube Studio (browser
  automation); the three assistant products (chatgpt.com, claude.ai,
  gemini.google.com) whose UIs are recorded.
- **Internal/cross-workspace**: iaser.ai workspace (article publication,
  prompt page updates for translated prompts); JaleesBench harness +
  Arabic arm (only if the validation question resolves to option 2/3).
- **Libraries/tooling**: Playwright (CDP against installed Chrome),
  ffmpeg/ffprobe, uv/Typer, headless-Chrome HTML→PNG card rendering,
  Noto Naskh Arabic / Noto Nastaliq Urdu fonts.
- **Seed material**: `tmp/companion-video-pipeline/` (main checkout) —
  scripts, runbook, EN outputs.

## References
- Issue #14 (requirements + gate comment with binding decisions).
- Seed runbook: `tmp/companion-video-pipeline/PIPELINE.md` (main checkout).
- EN article: https://iaser.ai/articles/jaleesbench-companion-prompt
- EN videos (Private): youtu.be/f5gvS4_pa1I · youtu.be/YCu0NDjxbY4 ·
  youtu.be/aN3ICiEx-pI
- Canonical prompt: GUIDE_MIN v3, s.iaser.ai/prompt
- iaser-ai YouTube channel: `UCF1yEgoyLfbgTUpeMn2ruqA`

## Risks and Mitigation
| Risk | Probability | Impact | Mitigation Strategy |
|------|------------|--------|-------------------|
| Gemini TTS lacks acceptable Urdu | High | High | Listen-test spike first; fallback chain (ElevenLabs → Azure `ur-PK` → OpenAI); architect scope escalation if all fail; other languages unaffected |
| Translated prompt exceeds an assistant's entry limit | Medium | High | Empirical length/format check per assistant × language early; translation shortened deliberately, never silently trimmed |
| Target-language UI route unavailable for an assistant | Medium | Medium | Investigate `?hl=`/account/browser-locale per assistant early in recording work; blocker escalated, no silent English fallback |
| Fresh recordings hit assistant UI drift/fragility (×9 recordings) | Medium | Medium | Seed runbook's recording rules; record per-assistant sequentially; verification frame per take |
| RTL rendering defects (cards, captions) | Medium | Medium | Per-language CSS overrides; BiDi marks; explicit spot-check criteria on real uploads |
| Refactor breaks the working EN flow | Medium | Medium | EN parity rebuild is a standing regression test |
| Wedged-Chrome / upload flow failures | Medium | Low | Documented recovery (restart profile, resume drafts); channel preflight guard |
| Translation quality inadequate | Medium | High | Minimum strong-model cross-check per artifact; human speaker review preferred; reviewer recorded per language |
| Cross-workspace handoff stalls | Low | Medium | Boundary = acknowledged handoff; early `afx send` coordination; architect escalation |

## Expert Consultation
**Date**: 2026-07-28 · **Models**: Gemini (APPROVE), Codex
(REQUEST_CHANGES), Claude (COMMENT) — round 1 on the pre-gate draft.

**Sections updated from consultation** (all feedback accepted; details in
`codev/projects/14-multilingual-companion-prompt-/14-specify-iter1-rebuttals.md`):
- Assumptions/Risks: Urdu TTS failure decision rule + named fallback chain
  (Codex, Gemini).
- Constraints: storage policy for binary inputs (Codex, Claude);
  secrets/machine-locality hygiene (Codex); mechanical channel guard
  (Codex); RTL card CSS overrides + BiDi caption marks (Gemini).
- Success criteria: mechanical EN-parity definition (Claude); tightened
  clean-checkout re-runnability (Codex); explicit translation-review
  minimum bar (Claude).
- Stakeholder handoff: article package format made testable (Codex).

Post-gate revision (this document): all six open questions resolved per
Waleed's binding gate decisions; restructured to the SPIR spec template;
plan-level detail (CLI shapes, directory layout) moved out to the upcoming
plan.

## Approval
- [x] Expert AI consultation complete (round 1)
- [x] Stakeholder sign-off: **spec-approval gate APPROVED by Waleed,
      2026-07-28, with binding decisions** (issue #14 gate comment)
- [ ] Plan-approval gate (next)

## Notes
The article handoff package format agreed in review: one directory per
language — `index.md` with frontmatter (`title`, `lang`, `dir` ltr/rtl,
`slug` mirroring the EN article, video IDs) plus referenced images/GIFs at
relative paths, structure mirroring the EN article section-for-section;
delivered and acknowledged via `afx send` to the iaser.ai workspace
architect. With Q1 decided, the handoff also includes the translated prompt
text for the prompt page. Exact in-repo staging location for the package is
a plan decision.
