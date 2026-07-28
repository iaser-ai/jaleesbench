# Plan: Multilingual companion-prompt assets (Arabic, Urdu, Bahasa Indonesia) on a reproducible pipeline

## Metadata
- **ID**: plan-2026-07-28-multilingual-companion-prompt
- **Status**: draft
- **Specification**: codev/specs/14-multilingual-companion-prompt-.md
- **Created**: 2026-07-28

## Executive Summary

Implements the spec's chosen Approach 1: a **single data-driven pipeline**
landed in-repo, where everything language-dependent lives in per-language
config/data. The plan front-loads the two things that can invalidate
everything else — the EN parity rebuild (proves the port didn't break the
working flow) and the TTS listen-test spike (Urdu is the flight risk) —
then moves through translated prompts, fresh target-language recordings,
localized builds, uploads, and article handoffs in dependency order.

Binding gate decisions shape the phases: translated prompts (Q1), Gemini
TTS default with fallback chain (Q2), fresh target-language UI recordings
(Q3/Q6), browser-automation uploads (Q5), articles handed to the iaser.ai
workspace (Q4). North star: highest-quality videos — each build phase ends
with a full watch-through quality review, and quality findings reopen work
rather than ship.

**Decision needed at plan-approval gate** (spec's open Critical question):
JaleesBench validation of translated prompts. Options and costs are in the
spec (§ Open Questions). Recommendation remains: light validation for
Arabic (an Arabic arm already exists), spot-checks only for ur/id, full
validation as a possible follow-up project. **If the gate picks option 2 or
3, this plan gains a validation phase (amended before implementation
starts); as drafted it assumes option 1-for-ur/id + option 2-for-ar is NOT
yet decided, so no validation phase is included.**

## Success Metrics

- [ ] All specification success criteria met (spec § Success Criteria —
      parity rebuild, translated prompts within entry limits, 9 recordings,
      9 videos + 9 srt uploaded Private with captions, 3 article handoffs
      acknowledged, clean-checkout re-runnability, recorded translation
      reviews, RTL spot-checks).
- [ ] Timing/caption/config logic covered by unit tests (media outputs are
      human-reviewed; blanket >90% coverage is N/A per spec).
- [ ] Zero credentials/profile artifacts in the repo.
- [ ] Pipeline README sufficient to re-run from a clean checkout.

## Phases (Machine Readable)

```json
{
  "phases": [
    {"id": "land_pipeline", "title": "Land EN pipeline in-repo with language-config architecture (parity rebuild)"},
    {"id": "tts_spike", "title": "TTS listen-test spike and per-language voice configs"},
    {"id": "translated_prompts", "title": "Translated prompts: produce, review, verify entry constraints"},
    {"id": "recordings", "title": "Target-language UI recordings (locale routes + 9 clips)"},
    {"id": "localized_content", "title": "Localized VO scripts, cards, and spell-out tables (ar/ur/id)"},
    {"id": "localized_builds", "title": "Build 9 videos + 9 srt with quality review and re-run proof"},
    {"id": "uploads", "title": "Private uploads with channel guard and captions"},
    {"id": "articles", "title": "Localized article sources and iaser.ai handoff packages"}
  ]
}
```

## Phase Breakdown

### Phase 1: Land EN pipeline in-repo with language-config architecture (parity rebuild)
**Dependencies**: None

#### Objectives
- Port the rescued seed into a first-class in-repo pipeline whose
  language-dependent surface is entirely config/data, proving nothing broke
  via an EN parity rebuild.

#### Seed access (prerequisite — the seed is NOT in this worktree)
The authoritative seed is `tmp/companion-video-pipeline/` in the **main
checkout** (`/Users/mwk/Development/fftn/taqwabench/tmp/companion-video-pipeline/`);
`tmp/` is gitignored, so builder worktrees don't contain it. From the
`.builders/<id>/` worktree it is readable at
`../../tmp/companion-video-pipeline/`. Phase 1's first step copies the
needed scripts + EN clips from that path into the repo (that copy IS the
"landing"); if the path is missing, stop and ask the architect — do not
reconstruct from memory.

#### Deliverables
- [ ] `apps/companion-pipeline/` uv project (Typer CLI, name `companion`;
      dependencies include `typer`, `playwright`, `httpx` — matching the
      seed's imports — with `pytest` in the dev group):

```
apps/companion-pipeline/
  pyproject.toml                  # uv project; console script `companion`
  README.md                       # runbook: PIPELINE.md content + gotchas
  companion_pipeline/
    cli.py                        # record | build | captions | upload | all  (--lang)
    config.py                     # language-config loading + validation
    timing.py                     # segment clamping / outro rules (pure, unit-tested)
    recorder.py                   # CDP harness (from seed clips/recorder.py)
    drivers/                      # per-assistant recording drivers
    tts.py                        # engine adapters: gemini (default); fallback slots
    cards.py                      # HTML→PNG cards, per-language CSS overrides
    assemble.py                   # ffmpeg assembly (from build_video.py)
    captions.py                   # SRT from shared timing (from make_srt.py), BiDi marks
    upload.py                     # Studio automation + channel preflight guard
  languages/
    en/config.toml                # engine, voice, style, dir, fonts, YT metadata
    en/prompt.txt                 # canonical prompt text (EN: GUIDE_MIN v3)
    en/vo/{chatgpt,claude,gemini}.toml   # segments: (offset, text) + intro/outro VO
    en/cards/{intro,outro}.html   # card TEMPLATES with product-name substitution
                                  #   (6 renders per language: 3 assistants ×
                                  #   intro/outro, as in the seed's cfgs()) +
                                  #   per-language CSS block
    en/spellouts.toml             # TTS spell-outs + SRT readable-text mappings
  inputs/clips/en/                # committed EN reference recordings (~2 MB)
  handoff/                        # COMMITTED deliverables staging (articles,
                                  #   GIFs, prompt text) — Phase 8; not output
  out/                            # gitignored: tts cache, cards, videos, srt
                                  #   (out/ is the ONLY ignored directory here)
```

- [ ] EN language config reproducing the seed's VO text, offsets, cards,
      spell-outs verbatim.
- [ ] `.gitignore` entries for `out/`; EN clips committed; no
      credentials/profile artifacts (verified).
- [ ] Unit tests (pytest via uv) for `timing.py` (clamping, outro stretch,
      collision detection), `captions.py` (cue generation, spell-out
      mapping, BiDi insertion), `config.py` (schema validation, missing-key
      fail-fast).
- [ ] README runbook covering setup (.env, Chrome profile, ffmpeg), each
      stage, and the seed's hard-won gotchas.

#### Implementation Details
- Port, don't rewrite: keep the seed's proven ffmpeg filtergraphs, CDP
  patterns, and timing rules; extract the timing math into `timing.py` so
  video assembly and SRT generation share one tested implementation
  (they already share logic in the seed — make that literal).
- Fail-fast config validation (no fallbacks): a missing voice/font/VO key
  aborts with a clear error naming the language file.
- TTS adapter interface takes (text, style, voice, engine) from config —
  Gemini implemented now; fallback engines are additional adapters later
  only if the Phase 2 decision rule triggers.
- The seed's machine-specific paths (profile dir, ports, output dirs)
  become config/env with README documentation.

#### Acceptance Criteria
- [ ] `companion build --lang en --video chatgpt` + `companion captions
      --lang en` rebuild the ChatGPT video + `.srt` meeting the spec's
      mechanical parity definition (same segment count/VO/offsets; SRT cue
      starts within TTS-duration drift of the shipped EN `.srt`).
- [ ] Timeline print shows no `***` collisions.
- [ ] All unit tests pass; `uv run pytest` green from clean checkout.
- [ ] README walkthrough executed once end-to-end (build path) from a clean
      checkout.

#### Test Plan
- **Unit**: timing clamps (overlap → non-overlap), outro stretch rule,
  collision detector, SRT cue math, BiDi wrapping, spell-out mapping,
  config validation failures.
- **Integration**: EN parity rebuild (the standing regression test).
- **Manual**: watch the rebuilt EN video against the shipped one.

#### Rollback Strategy
Purely additive (new directory); revert the phase commit. Seed in `tmp/`
remains untouched as reference.

#### Risks
- **Risk**: refactor subtly changes timing/audio behavior.
  - **Mitigation**: parity rebuild + shared `timing.py` under unit test;
    keep seed available for diffing.

---

### Phase 2: TTS listen-test spike and per-language voice configs
**Dependencies**: Phase 1

#### Objectives
- Establish a listen-test-approved voice + style prompt for ar, ur, id on
  Gemini TTS — or trigger the fallback decision rule early, before any
  dependent work.

#### Deliverables
- [ ] Spike script/short doc: for each language, the same short narration
      sample generated with 2–3 candidate Gemini TTS voices.
- [ ] Human listen-check results recorded (sent to architect with samples;
      their pick/quality call is the approval).
- [ ] `languages/{ar,ur,id}/config.toml` skeletons with chosen engine +
      voice + style prompt + `dir` + fonts.
- [ ] Initial per-language spell-out tables seeded (I-A-S-E-R etc.,
      language-appropriate phonetics), refined later during builds.
- [ ] If Urdu (or any language) fails on Gemini TTS: fallback chain
      evaluated (ElevenLabs multilingual → Azure `ur-PK` → OpenAI TTS) with
      the same listen test; if none passes, **escalation to architect via
      afx send and phase marked blocked** — other languages proceed.

#### Implementation Details
- Samples generated through the Phase 1 `tts.py` adapter (exercises the
  real code path, not a one-off curl).
- Listen-test artifacts (small mp3/wav samples) go under `out/` (gitignored);
  results table goes in the phase notes + architect message.

#### Acceptance Criteria
- [ ] For each of ar/ur/id: either a listen-test-approved voice recorded in
      config, or a documented escalation with architect decision.
- [ ] Style prompts reviewed for register (warm tutorial narrator) per
      language.

#### Test Plan
- **Manual**: the listen tests themselves (human ears are the test).
- **Unit**: config skeletons pass validation.

#### Rollback Strategy
Config-only changes; revert commit.

#### Risks
- **Risk**: Urdu unsupported/poor on all engines (spec's top risk).
  - **Mitigation**: spike is first dependent work; decision rule +
    escalation path; ar/id continue.

---

### Phase 3: Translated prompts: produce, review, verify entry constraints
**Dependencies**: Phase 1 (config home); independent of Phase 2

#### Objectives
- Produce reviewed ar/ur/id translations of GUIDE_MIN v3 that fit every
  assistant's entry constraints, verified empirically — the artifact every
  recording and article depends on.

#### Deliverables
- [ ] `languages/{ar,ur,id}/prompt.txt` — translated GUIDE_MIN v3.
- [ ] Translation review recorded per language (minimum: strong-model
      cross-check against EN source via `consult`; human speaker review if
      available — reviewer noted in phase notes and review doc).
- [ ] Empirical entry-constraint matrix (3 assistants × 3 languages):
      fits ChatGPT custom-instructions field (~1,500 chars), Claude
      settings, Gemini saved-info; **Gemini two-part paste re-verified per
      language** (error-13 workaround).
- [ ] Translated prompt text packaged for the iaser.ai prompt page and
      sent to that workspace's architect (handoff can be bundled with
      Phase 8's package if they prefer — coordination message sent now
      regardless, since the prompt page gates public usefulness).

#### Implementation Details
- Translation approach: draft with a strong model, then independent
  cross-check by a *different* model (via `consult`), reconciling
  divergences; flag any theologically/tonally sensitive phrasing to the
  architect rather than guessing.
- Length discipline: translations are re-drafted to fit limits — never
  silently truncated (fail-fast rule).
- Entry-constraint checks happen live in each assistant UI (same Chrome
  profile used for recording) — they double as rehearsal for Phase 4
  recordings.

#### Acceptance Criteria
- [ ] 3 reviewed prompt files committed; char counts documented.
- [ ] 9/9 cells of the entry-constraint matrix verified, two-part paste
      confirmed for Gemini in all 3 languages (or deviations documented
      and escalated).
- [ ] Prompt-page coordination message sent to iaser.ai workspace.

#### Test Plan
- **Unit**: prompt files load via config; char-limit assertions in config
  validation (limit per assistant recorded in config).
- **Manual**: the 9-cell entry matrix; review pass records.

#### Rollback Strategy
Config/data-only; revert commit. EN prompt remains canonical publicly
until iaser.ai publishes translations.

#### Risks
- **Risk**: a translation cannot express GUIDE_MIN within ~1,500 chars.
  - **Mitigation**: iterate wording (Arabic is typically more compact than
    EN; Urdu/Indonesian near parity); if genuinely impossible, escalate
    with a proposed trimmed variant for architect sign-off.

---

### Phase 4: Target-language UI recordings (locale routes + 9 clips)
**Dependencies**: Phase 3 (translated prompts are what gets pasted)

#### Objectives
- Fresh walkthrough recordings for all 9 (assistant × language) cells with
  the assistant UI displayed in the target language.

#### Deliverables
- [ ] Locale-route investigation, documented in README: per assistant, how
      to get the UI into ar/ur/id — try `?hl=` first (known for Gemini);
      ChatGPT/Claude likely account-setting or browser-locale
      (`--lang`/Accept-Language) routes; findings recorded per assistant.
- [ ] Recording drivers parameterized by language: prompt-page copy (of the
      translated prompt) → assistant settings → paste (two-part for
      Gemini) → save → verification exchange in the target language.
- [ ] 9 recordings committed under `inputs/clips/{ar,ur,id}/` (quality bar:
      clean cursor motion, correct viewport, verification frame appended —
      per README recording rules).
- [ ] Screenshot/GIF source frames captured for Phase 8 articles.

#### Implementation Details
- Follow the seed's recording rules (own window per page, viewport before
  goto, trusted clicks + visible window for Gemini, purge stale frames,
  re-hide via PID but avoid long-hidden renderer wedge).
- RTL UIs will mirror layouts — drivers must locate elements by role/label,
  not coordinates; verify selectors hold in ar/ur.
- If an assistant offers no target-language UI: **escalate to architect**
  (options: browser-locale forcing, or that cell records EN UI with the
  translated prompt) — no silent fallback.

#### Acceptance Criteria
- [ ] 9 clips reviewed frame-by-frame at the take level (correct language
      UI, correct prompt pasted, verification exchange visible, no
      personal-content leakage) and committed.
- [ ] Locale routes documented per assistant.

#### Test Plan
- **Manual**: per-take review checklist (the north-star quality gate for
  the raw footage).
- **Integration**: drivers run end-to-end per cell without manual
  intervention beyond documented prerequisites.

#### Rollback Strategy
Clips are additive inputs; revert commit removes them. Re-record any cell
independently.

#### Risks
- **Risk**: RTL layout mirroring breaks selectors/cursor choreography.
  - **Mitigation**: role/label-based locators; per-cell dry run before
    recording take.
- **Risk**: assistant UI drift since EN run.
  - **Mitigation**: drivers fixed as encountered; runbook updated.

---

### Phase 5: Localized VO scripts, cards, and spell-out tables (ar/ur/id)
**Dependencies**: Phases 2 (voices), 4 (clips — offsets are timed against
the new clips)

#### Objectives
- Author and review all localized *content* — VO scripts, cards,
  spell-outs — as committed config, separately from the build/QA push so
  content review lands incrementally.

#### Deliverables
- [ ] `languages/{ar,ur,id}/vo/*.toml` — translated VO scripts with
      per-clip segment offsets (retimed against the *new* clips, not EN
      offsets); translation review recorded (same bar as Phase 3).
- [ ] Localized intro/outro card templates: translated text, `dir="rtl"` +
      Noto Naskh Arabic / Noto Nastaliq Urdu with per-language CSS
      overrides (line-height/size — no vertical clipping), verified as
      standalone card renders.
- [ ] Initial spell-out + SRT readable-text tables per language (refined
      further during Phase 6 listen checks).

#### Implementation Details
- VO timing: offsets derived per new clip (clips differ per language);
  clamping rules absorb TTS duration variance — verify, don't assume (spec
  nice-to-know question resolved across Phases 5–6).
- Cards rendered per language via `cards.py` overrides; visual diff against
  EN composition for framing consistency.

#### Acceptance Criteria
- [ ] 3 languages × 3 videos of VO config committed with recorded reviews;
      card renders for ar/ur/id pass RTL/font inspection.
- [ ] Config validation green for all four languages.

#### Test Plan
- **Unit**: config validation over the new language files.
- **Manual**: card render inspection; translation review records.

#### Rollback Strategy
Config/data-only; revert commit per language.

#### Risks
- **Risk**: narration text runs long vs clip length (ar/ur/id verbosity).
  - **Mitigation**: write VO for concision now; Phase 6's timeline print +
    outro-stretch rule catch what remains.

---

### Phase 6: Build 9 videos + 9 srt with quality review and re-run proof
**Dependencies**: Phase 5

#### Objectives
- Build all 9 videos and caption files from config alone, to the
  north-star quality bar, and prove clean-checkout re-runnability.

#### Deliverables
- [ ] 9 videos (1080p) + 9 `.srt` built; collision check clean.
- [ ] Refined spell-out tables from listen checks on every video's
      narration (loop: listen → fix spell-out → rebuild → re-listen).
- [ ] Full watch-through quality review per video (narration sync, card
      timing, UI legibility, caption/BiDi rendering in a local player)
      before any upload.
- [ ] Clean-checkout re-runnability demonstrated on at least one non-EN
      language (spec criterion): fresh clone → README → build + captions.

#### Acceptance Criteria
- [ ] 9/9 videos + srt built from config alone (`companion build/captions
      --lang X`); zero collisions; quality review checklist recorded per
      video.
- [ ] Re-run proof documented (commands + outcome) in phase notes.

#### Test Plan
- **Unit**: existing timing/caption tests exercised by 3 new configs; BiDi
  assertions on real ar/ur cue text.
- **Manual**: 9 watch-throughs; RTL caption rendering in a local player.

#### Rollback Strategy
Outputs are regenerable; spell-out/config fixes are revertible commits.

#### Risks
- **Risk**: TTS pronunciation defects surface late (novel words per
  language).
  - **Mitigation**: per-video listen checks with the spell-out loop before
    the quality gate.

---

### Phase 7: Private uploads with channel guard and captions
**Dependencies**: Phase 6

#### Objectives
- All 9 videos live as **Private** on the iaser-ai channel with correct
  metadata, language, and captions — safely and repeatably.

#### Deliverables
- [ ] `upload.py` hardened per seed gotchas: channel-pinned Studio URLs,
      **preflight asserting active channel ID on-page (mismatch aborts)**,
      wedged-Chrome recovery + draft-resume documented, `pg.url` verified
      before acting.
- [ ] Per-language YouTube metadata in config (title, description, Video
      language = ar/ur/id, `VIDEO_MADE_FOR_KIDS_NOT_MFK`, PRIVATE).
- [ ] 9 uploads completed; captions attached ("with timing" `.srt` flow)
      per video.
- [ ] Video IDs recorded in the plan/review notes and sent to the
      architect for review (north-star human review happens on YouTube).
- [ ] Caption display + BiDi behavior spot-checked on the uploaded videos
      (spec RTL criterion).

#### Implementation Details
- Uploads sequential, one video at a time, verifying Private visibility
  and language field before the next (fail-fast; no batch fire-and-forget).

#### Acceptance Criteria
- [ ] 9/9 Private on the correct channel (preflight log per upload),
      captions attached, IDs reported via `afx send`.

#### Test Plan
- **Manual/integration**: preflight abort tested against the wrong-channel
  condition (navigate to personal channel context → assert abort) before
  any real upload.

#### Rollback Strategy
Videos are Private; a bad upload is deleted in Studio and re-run. Drafts
resume per the runbook.

#### Risks
- **Risk**: wrong-channel upload (high impact).
  - **Mitigation**: mechanical preflight + pinned URLs + tested abort.
- **Risk**: wedged Chrome mid-upload.
  - **Mitigation**: documented restart/resume; per-video verification.

---

### Phase 8: Localized article sources and iaser.ai handoff packages
**Dependencies**: Phase 7 (video IDs), Phase 4 (GIF/screenshot sources)

#### Objectives
- Deliver publish-ready localized articles (+ prompt text) to the iaser.ai
  workspace and get the handoff acknowledged — closing the project's
  deliverable boundary.

#### Deliverables
- [ ] Walkthrough GIFs/screenshots generated from the target-language
      recordings (per assistant, mirroring the EN article's set).
- [ ] `handoff/article/{ar,ur,id}/index.md` with frontmatter (`title`,
      `lang`, `dir`, `slug` mirroring EN, video IDs) + relative-path
      assets; structure mirrors the EN article section-for-section,
      including the per-language Gemini two-part paste instructions;
      translation review recorded (Phase 3 bar).
- [ ] Translated prompt text included for the prompt page (if not already
      handed off in Phase 3).
- [ ] Pinned EN article snapshot committed at
      `apps/companion-pipeline/handoff/article/en-reference.md` (fetched
      once at phase start) — the translation source, immune to live-site
      drift mid-implementation.
- [ ] Handoff sent via `afx send` to the iaser.ai workspace architect;
      **acknowledgement received and recorded**.

#### Implementation Details
- Handoff staging is `apps/companion-pipeline/handoff/` — a **committed**
  directory, sibling of (not inside) the gitignored `out/`; it holds
  deliverables (curated GIFs, article sources, prompt text), never
  regenerable build artifacts.
- Article translation derives from the pinned EN snapshot above, adapted
  where language-specific (paste instructions, prompt text, RTL notes).
  If the live EN article changes materially before handoff, refresh the
  snapshot deliberately in a visible commit — never implicitly.

#### Acceptance Criteria
- [ ] 3 packages complete per the agreed format; acknowledgement from the
      iaser.ai workspace recorded in thread + review doc.

#### Test Plan
- **Manual**: package renders correctly (markdown preview, RTL direction);
  links/IDs verified against the uploaded videos.

#### Rollback Strategy
Handoff is additive; corrections ship as package updates + re-send.

#### Risks
- **Risk**: handoff stalls (cross-workspace).
  - **Mitigation**: early coordination (Phase 3 message); architect
    escalation if unacknowledged.

## Dependency Map
```
Phase 1 ──→ Phase 2 ──────────────┐
   │                              ▼
   └──────→ Phase 3 ──→ Phase 4 ──→ Phase 5 ──→ Phase 6 ──→ Phase 7 ──→ Phase 8
                          (Phase 4 also feeds Phase 8's GIFs)
```
(Phases 2 and 3 are independent of each other; executed sequentially in
the listed order. Phase 5 = localized content, Phase 6 = builds/QA,
Phase 7 = uploads, Phase 8 = articles.)

## Resource Requirements
### Development Resources
- **Environment**: macOS with installed Chrome (dedicated profile logged
  into chatgpt.com, claude.ai, gemini.google.com, and the YouTube-owning
  Google account), ffmpeg/ffprobe, uv, `GEMINI_API_KEY` in repo-root
  `.env`.
- Human in the loop: listen tests, per-video quality review, gate
  decisions, YouTube review (Waleed).

### Infrastructure
- None (offline pipeline; no services, no DB). Possible fallback-TTS API
  keys only if Phase 2's decision rule triggers.

## Integration Points
### External Systems
- **Gemini TTS API** — Phases 2/6; fallback chain per decision rule.
- **Assistant products (ChatGPT/Claude/Gemini)** — Phases 3/4; UI drift
  handled as encountered; no fallback (escalate).
- **YouTube Studio (browser automation)** — Phase 7; wedge-recovery
  runbook; drafts resume.

### Internal Systems
- **iaser.ai workspace** — Phases 3/8 handoffs via `afx send`; boundary =
  acknowledged handoff.
- **JaleesBench harness/Arabic arm** — only if the plan-gate validation
  decision adds a phase.

## Risk Analysis
### Technical Risks
| Risk | Probability | Impact | Mitigation | Owner |
|------|------------|--------|------------|-------|
| Urdu TTS unacceptable on all engines | M | H | Phase 2 spike first; fallback chain; architect scope escalation | builder |
| Translated prompt exceeds entry limits | M | H | Phase 3 empirical matrix; redraft, never truncate | builder |
| No target-language UI route for an assistant | M | M | Phase 4 investigation first; escalate, no silent EN fallback | builder |
| RTL mirroring breaks recording drivers | M | M | Role/label locators; per-cell dry runs | builder |
| Port breaks EN flow | M | M | Phase 1 parity rebuild as regression test | builder |
| Wrong-channel upload | L | H | Mechanical preflight, tested abort | builder |

### Schedule Risks
*(No time estimates per protocol.)* Sequencing risk only: Phases 2/3 are
the invalidators — both run before the expensive recording/build work;
escalations pause only the affected language.

## Validation Checkpoints
1. **After Phase 1**: EN parity rebuild reviewed; unit tests green.
2. **After Phase 2**: voices approved (human listen check) or escalation
   resolved.
3. **After Phase 3**: 9-cell entry matrix complete; translations reviewed.
4. **After Phase 4**: 9 clips pass take-level review.
5. **After Phase 5**: VO/card configs reviewed; RTL card renders pass.
6. **After Phase 6**: 9 watch-throughs pass; clean-checkout re-run shown.
7. **After Phase 7**: 9 Private uploads verified; IDs with architect.
8. **After Phase 8**: handoffs acknowledged.

## Monitoring and Observability
N/A — offline batch pipeline with human review at every stage. The
pipeline's "observability" is its timeline print (collision markers) and
fail-fast config validation.

## Documentation Updates Required
- [ ] `apps/companion-pipeline/README.md` (runbook — created Phase 1,
      updated through Phase 7 with locale routes + upload gotchas)
- [ ] arch docs (hot/cold tiers) at Review phase per protocol
- [ ] Review doc `codev/reviews/14-multilingual-companion-prompt-.md`

## Post-Implementation Tasks
- [ ] Waleed reviews/publishes videos (outside project boundary)
- [ ] iaser.ai publishes articles + prompt page (outside boundary)
- [ ] JaleesBench validation follow-up if gate decision defers it
- [ ] Verify phase after PR merge (porch)

## Expert Review
**Date**: 2026-07-28 · **Models**: Gemini (APPROVE), Codex
(REQUEST_CHANGES), Claude (APPROVE with observations)

**Key feedback and adjustments** (all accepted):
- Seed not present in builder worktrees (`tmp/` gitignored) — Phase 1 now
  states the authoritative main-checkout path, the worktree-relative
  access path, and a stop-and-ask rule if missing (Codex, Claude).
- `handoff/` vs gitignored `out/` contradiction — handoff is now
  explicitly a committed sibling directory; `out/` is the only ignored
  path (Codex).
- Original Phase 5 too large for one atomic commit — split into Phase 5
  (localized content: VO/cards/spell-outs) and Phase 6 (builds + QA +
  re-run proof) (Codex).
- EN article fetched live would drift — Phase 8 pins a committed EN
  snapshot as the translation source; refreshes are deliberate commits
  (Codex).
- Playwright named as an explicit dependency alongside Typer (Claude).
- Card templates' product-name substitution made explicit — 6 renders per
  language, matching the seed's `cfgs()` (Claude).
- Claude verified against the seed code that the shared-`timing.py`
  extraction, TTS adapter shape, and new channel preflight are the right
  moves; ffmpeg filtergraph is ported, not redesigned.

## Approval
- [x] Plan-approval gate **APPROVED (Waleed, 2026-07-28)**. Validation
      decision: **Option 1 — no bench validation of translated prompts in
      this project** (spot-checks only; follow-up project if warranted).
      No validation phase added; plan proceeds as drafted. Gate record on
      issue #14.
- [x] Expert AI consultation complete (round 1; all feedback incorporated)

## Change Log
| Date | Change | Reason | Author |
|------|--------|--------|--------|
| 2026-07-28 | Initial draft | — | builder spir-14 |
| 2026-07-28 | Seed-access prerequisite; handoff/ path fixed; Phase 5 split (now 8 phases); EN article snapshot pinned; deps named | 3-way plan review round 1 | builder spir-14 |

## Notes
- Phase commits use `[Spec 14][Phase: <id>] type: description`; one atomic
  commit per phase (git commits, not PRs — single PR at the end unless the
  architect requests otherwise).
- The seed directory `tmp/companion-video-pipeline/` stays untouched as
  reference until the Review phase confirms parity, after which its
  disposition (delete vs keep) is an architect call.
