# Spec 14 — Multilingual companion-prompt assets (Arabic, Urdu, Bahasa Indonesia) on a reproducible pipeline

**Status:** Draft (Specify)
**Issue:** #14
**Protocol:** SPIR

## 1. Overview / Problem

The English companion-prompt launch produced a full outreach asset suite: an
article on iaser.ai, per-assistant UI walkthrough recordings (GIFs/screenshots),
and three narrated videos (ChatGPT / Claude / Gemini) with exact-timeline
captions, uploaded Private to the iaser-ai YouTube channel. That production run
was a one-off: the scripts and the hard-won process knowledge were rescued into
`tmp/companion-video-pipeline/` (main checkout) — a directory of ~1,480 lines of
Python plus `PIPELINE.md`, sitting outside version control.

This project does two things, in order:

1. **Land the rescued EN pipeline in-repo** as a first-class, re-runnable
   pipeline — so a script tweak, a prompt change, or a new language regenerates
   all assets without re-deriving the process.
2. **Use that pipeline to produce the same asset suite in Arabic, Urdu, and
   Bahasa Indonesia** — the three languages, mirroring the EN originals.

The pipeline is the durable deliverable; the three language suites are both the
payload and the proof that the pipeline is genuinely reproducible.

## 2. Stakeholders

- **Waleed / iaser-ai** — reviews and publishes the videos (uploads are always
  Private until reviewed); owns the messaging.
- **iaser.ai workspace architect** — owns the article site; localized articles
  land in that repo, not this one. Cross-workspace coordination is a hard
  dependency for the article deliverable.
- **Arabic / Urdu / Bahasa Indonesia-speaking audiences** — the point of the
  project: reaching Muslim-majority audiences in their own languages.
- **Future maintainers** — anyone re-running the pipeline for language four or
  for a prompt v4 refresh.

## 3. Constraints

### 3.1 Fixed requirements (from issue #14)

1. **Asset suite per language, mirroring EN**: article writeup, per-assistant
   UI walkthrough recordings (GIFs/screenshots), narrated videos for
   ChatGPT / Claude / Gemini with exact-timeline `.srt` captions.
2. **Videos upload Private** to the iaser-ai YouTube channel
   (`UCF1yEgoyLfbgTUpeMn2ruqA`) for human review. Never to the Google login's
   default (personal) channel.
3. **Re-runnable end to end**: a new language or a script/prompt tweak
   regenerates all assets without re-deriving the process.
4. **The rescued EN pipeline lands in-repo as part of this project.** Seed:
   `tmp/companion-video-pipeline/` — `PIPELINE.md` documents every stage and
   gotcha (recording rules, TTS spell-outs, ffmpeg timing rules, upload flow).
5. Canonical prompt is **GUIDE_MIN v3** (1,492 chars), public at
   s.iaser.ai/prompt.

### 3.2 Environmental facts

- The five pipeline stages and their language-dependent surface (from reading
  the seed scripts): **(1) record clips** — Playwright-over-CDP harness +
  per-assistant drivers, language-neutral unless we record UIs in the target
  language; **(2) TTS** — Gemini `gemini-3.1-flash-tts-preview`, voice `Puck`
  (EN-tuned), style prompt, VO text, and pronunciation spell-outs are all
  per-language; **(3) assembly** — ffmpeg timing logic is language-neutral,
  but intro/outro `CARD_HTML` needs `dir="rtl"` + font work for Arabic/Urdu;
  **(4) SRT** — timing logic shared with assembly; spell-out→readable-text
  mappings are per-language; **(5) upload** — YouTube "Video language" field
  per language; flow otherwise identical.
- Gemini's entry rewriter rejects the full prompt (error 13); EN used a
  **two-part paste** workaround. Presumed language-independent; must be
  re-verified per language if the prompt ships translated.
- The EN videos are Private pending review: youtu.be/f5gvS4_pa1I (ChatGPT),
  youtu.be/YCu0NDjxbY4 (Claude), youtu.be/aN3ICiEx-pI (Gemini).
- Recording requires a Chrome profile logged into the three assistants and the
  YouTube-owning Google account; `GEMINI_API_KEY` in repo-root `.env`.
- Repo hygiene: explicit `git add`, `[Spec 14]` commit prefixes, no
  attribution lines. Python work uses `uv`; CLIs use Typer.

### 3.3 Known risks (must be de-risked early)

- **Urdu TTS coverage.** Gemini TTS's documented language list has included
  Arabic and Indonesian but (as of the author's knowledge) **not Urdu**. If
  `gemini-3.1-flash-tts-preview` cannot produce acceptable Urdu, the Urdu
  suite needs an alternative TTS provider or a scope decision. A listen-test
  spike for all three languages is the first implementation act after plan
  approval — it can invalidate assumptions the rest of the work builds on.
- **RTL correctness** (Arabic, Urdu): cards, fonts (Naskh for Arabic,
  **Nastaliq** for Urdu — Urdu readers do not accept Naskh well), SRT
  rendering on YouTube, mixed-direction text (URLs like `s.iaser.ai/prompt`
  embedded in RTL sentences).
- **Cross-workspace article dependency**: this repo cannot ship the article;
  it can only deliver publishable localized article source + assets to the
  iaser.ai workspace.
- **Translation quality**: ar/ur/id narration and article text need review by
  a competent speaker (human or at minimum a strong-model cross-check);
  outreach content in broken Urdu is worse than none.

## 4. The product

### 4.1 The pipeline (in-repo, language-parameterized)

The seed scripts, restructured and landed in-repo (proposed home:
`apps/companion-pipeline/` — sibling of `apps/jaleesbrowser`, since this is
outreach tooling, not the bench harness), as a small uv project with a Typer
CLI. One command per stage plus an orchestrating `all`, each taking a
`--lang` parameter:

```
companion-pipeline record   --lang en|ar|ur|id   # capture UI clips (when needed)
companion-pipeline build    --lang ...           # TTS + assemble videos
companion-pipeline captions --lang ...           # emit .srt
companion-pipeline upload   --lang ...           # upload Private + captions
```

All per-language content lives in **data, not code**: a per-language config
(voice, TTS style prompt, VO scripts with segment offsets, card HTML/text,
spell-out and readable-text mappings, YouTube titles/descriptions/language
tag, text direction). Adding language N+1 = adding one config + translations,
then re-running. The EN config is the reference implementation, reproduced
from the seed verbatim (same VO text, same timings) so EN output parity is
the pipeline's regression test.

`PIPELINE.md`'s runbook content (recording rules, wedged-Chrome recovery,
upload gotchas) lands as the pipeline's README — the process knowledge is
part of the deliverable.

### 4.2 The per-language asset suites (ar, ur, id)

For each language, mirroring EN:

| Asset | Notes |
|---|---|
| Localized article source | Written here, delivered to the iaser.ai workspace (see Q4) |
| Walkthrough GIFs/screenshots | Per assistant, for the article |
| 3 narrated videos (1080p) | ChatGPT / Claude / Gemini, localized narration + intro/outro cards |
| Exact-timeline `.srt` per video | Same timing engine as audio |
| YouTube uploads | Private, iaser-ai channel, correct Video-language, captions attached |

Total new videos: 9 (3 languages × 3 assistants), plus captions and uploads.

## 5. Open questions — proposed resolutions (OPEN, for decision at spec-approval)

None of these are decided. Each has a proposal with rationale; the human
decides at the gate. Q1, Q3, and Q6 are coupled — they should be decided
together.

**Q1 — Does the companion prompt ship translated per language, or stay
English with a localized article?**
*Proposal:* the prompt itself **stays English** (GUIDE_MIN v3 unchanged).
It is the bench-validated artifact; a translated prompt is a different
artifact whose behavior JaleesBench has not measured, and it multiplies the
validation surface (does the Gemini two-part paste still work? does the
assistant's behavior shift?). The article, narration, cards, and captions
localize *around* the English prompt: "paste this English prompt; your
assistant will still respond in your language." Counterpoint worth weighing:
an English wall of text may feel alien to the target audience, and assistants
configured with an English system-style prompt sometimes drift toward English
replies. If translated prompts are wanted later, that's a follow-up project
with its own validation.

**Q2 — TTS voice per language?**
*Proposal:* keep Gemini TTS as the engine; run a **listen-test spike** as the
first implementation phase: for each of ar/ur/id, generate the same short
narration sample with 2–3 candidate voices, human listen-check, record the
chosen voice + style prompt + initial spell-out table in the language config.
Urdu is the flight risk (§3.3); if Gemini TTS can't do it, the spike reports
options (alternative provider vs. dropping/deferring Urdu) back to the
architect before any dependent work proceeds.

**Q3 — RTL handling; are assistant UIs recorded in the target language?**
*Proposal:* cards and captions go full RTL (`dir="rtl"`, Noto Naskh Arabic /
Noto Nastaliq Urdu fonts, verified rendering of embedded LTR URLs). Assistant
**UIs stay as recorded in English** for v1: re-recording three assistants ×
two more UI languages triples recording work and adds per-locale UI variance
(the most fragile pipeline stage), while localized narration + captions carry
the instructional load. Counterpoint: fully-localized screenshots are more
welcoming; a viewer whose ChatGPT is in Arabic sees different menu labels
than the video shows. Narration can bridge this ("the Settings menu — may be
labeled الإعدادات on your device").

**Q4 — Where do localized articles live; who publishes?**
*Proposal:* this project **authors** the localized article source (markdown +
images/GIFs, one per language) and hands it to the iaser.ai workspace
architect via `afx send` cross-workspace coordination; that workspace owns
URL structure (e.g. `/ar/articles/...` vs `?lang=ar`), site RTL styling, and
publishing. Deliverable boundary for this spec: article source + assets
delivered and acknowledged, not published.

**Q5 — Upload mechanics: browser automation vs YouTube Data API?**
*Proposal:* **keep Playwright browser automation** for this project, hardened
with the known gotchas (wedged-Chrome restart recovery, draft-resume,
channel-pinned Studio URLs). Rationale: the API path's OAuth caveat is
disqualifying for our flow — videos uploaded by unverified API projects are
**locked private** and cannot be published later without an app audit, and
these videos exist to eventually be public. Browser automation is proven (EN
run worked cleanly) and the volume (9 videos) is modest. Revisit the API +
verification audit if uploads become genuinely recurring.

**Q6 — Reuse EN recordings with re-dubbed narration vs fresh recordings?**
*Proposal:* **reuse the EN UI clips** for all three languages, with
per-language narration, cards, and captions. This follows from Q3 (UIs stay
English): the pixels would be identical, so re-recording buys nothing but
risk. The clip files land with the pipeline as versioned inputs. Fresh
recordings happen only where a language-specific interaction difference must
be shown (none known today; the Gemini two-part paste behaves the same in
the EN clip regardless of narration language). If Q1/Q3 are decided the
other way, this flips to fresh recordings and the recording stage's
`--lang` path gets exercised for real.

## 6. Success criteria

1. **Pipeline landed**: `apps/companion-pipeline/` (or approved location) in
   the repo, with README runbook; the EN config **rebuilds
   `youtube-chatgpt.mp4` + `.srt` reproducing the shipped EN timeline** (same
   segment structure; byte-identity not required — TTS is nondeterministic).
2. **Language configs** for ar, ur, id: voice (listen-test approved), style
   prompt, translated VO with reviewed translations, RTL-correct cards,
   spell-out tables.
3. **9 videos + 9 `.srt`** built with no timeline collisions (`***` check),
   uploaded **Private** to the iaser-ai channel with correct Video language
   and captions attached; video IDs recorded and sent to the architect for
   review.
4. **3 localized article sources** (+ GIFs/screenshots) delivered to the
   iaser.ai workspace; handoff acknowledged.
5. **Re-runnability demonstrated**, not asserted: at least one asset
   regenerated end-to-end from a clean checkout following only the README.
6. Translation review pass recorded for each language (who/what checked it).
7. RTL spot-checks: Arabic/Urdu cards render correctly (direction, font,
   embedded URLs), YouTube caption display verified on the uploaded videos.

## 7. Out of scope

- Publishing anything (videos go Private; articles are handed off).
- Translating GUIDE_MIN v3 itself, or JaleesBench validation of translated
  prompts (explicitly a follow-up if Q1 is decided toward translation).
- Languages beyond ar/ur/id.
- YouTube Data API OAuth setup (unless Q5 is decided the other way).
- Site-side RTL/i18n work in the iaser.ai repo.

## 8. Consultation log

*(populated during 3-way review)*
