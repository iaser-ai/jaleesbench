# companion-pipeline

Reproducible pipeline for the companion-prompt outreach assets: per-assistant
UI walkthrough recordings, TTS-narrated YouTube videos (ChatGPT / Claude /
Gemini), exact-timeline `.srt` captions, and the guarded YouTube upload.

Everything language-dependent lives in **data** under `languages/<lang>/` —
adding a language means adding one config directory plus translations and
re-running; no code changes. English (`en`) is the reference config,
reproduced verbatim from the shipped EN production run: rebuilding EN and
comparing against `reference/en-shipped/` is the pipeline's standing
regression test.

## Pipeline stages

```
(1) record UI clips   →  (2+3) TTS + assemble   →  (4) SRT captions  →  (5) upload
    companion record         companion build          companion captions    companion upload
```

## Layout

```
companion_pipeline/       code (language-neutral)
  cli.py                  Typer CLI (`companion`)
  config.py               language-config loading (fail-fast)
  timing.py               shared narration-timeline rules (unit-tested)
  tts.py                  TTS engine adapters (gemini default) + cache
  cards.py                intro/outro card HTML -> PNG
  assemble.py             ffmpeg assembly (uses timing.py)
  captions.py             SRT generation (uses the SAME timing.py)
  recorder.py             CDP screencast harness + fake cursor
  drivers/                per-assistant recording drivers
  upload.py               Studio connect + channel preflight guard
languages/<lang>/         ALL per-language content (config + text + cards)
inputs/clips/<lang>/      committed walkthrough recordings (pipeline inputs)
reference/en-shipped/     the shipped EN .srt files (parity baseline)
out/                      gitignored: TTS cache, cards, built videos, srt
handoff/                  committed deliverables staging (articles, GIFs)
```

## Setup

- **Python**: `uv sync` in this directory (installs typer, playwright,
  httpx; dev group adds pytest). Playwright uses the *installed* Chrome via
  CDP — no `playwright install` needed for recording; card rendering
  launches headless Chrome via `channel='chrome'`.
- **ffmpeg / ffprobe** on PATH.
- **GEMINI_API_KEY**: exported in the environment, or present in the
  repo-root `.env`. Never commit keys.
- **Recording/upload only** — a dedicated Chrome profile with CDP:

  ```bash
  google-chrome --user-data-dir=<rec-profile> --remote-debugging-port=9222
  ```

  The macOS re-hide helper finds this Chrome by matching a substring of
  its `--user-data-dir`; the default match is `rec-profile`, so either
  name your profile directory accordingly or set
  `COMPANION_REC_PROFILE_MATCH=<substring>`. A non-default CDP port/host
  is set with `COMPANION_CDP_URL` (default `http://localhost:9222`).

  The profile must be logged into the assistant products being recorded
  (chatgpt.com, claude.ai, gemini.google.com) and into the Google account
  owning the iaser-ai YouTube channel. The profile directory stays outside
  the repo; never commit cookies/profile artifacts.

## Commands

```bash
uv run companion languages                      # list configured languages
uv run companion build --lang en                # TTS + assemble all 3 videos
uv run companion build --lang en --video chatgpt
uv run companion captions --lang en             # .srt for all 3
uv run companion record --lang en --video gemini   # one take (CDP Chrome)
uv run companion upload --lang en               # NOT YET IMPLEMENTED (see below)
uv run pytest -q                                # unit tests
```

`companion upload` is a placeholder until the uploads plan phase lands the
automated flow — it exits with an error pointing at the manual Studio flow
documented below. The channel preflight guard
(`companion_pipeline.upload.preflight_channel()`) is already real.

Outputs land in `out/videos/<lang>/`. The build prints the narration
timeline — **inspect it for `***` collision markers** (a pushed segment
means narration would have overlapped; retime the offsets rather than
shipping a shoved timeline).

## EN parity (the regression test)

After any change to timing, TTS, assembly, or captions:

```bash
uv run companion build --lang en --video chatgpt
uv run companion captions --lang en --video chatgpt
diff out/videos/en/youtube-chatgpt.srt reference/en-shipped/youtube-chatgpt.srt
```

Parity means: same cue count and text, cue starts within TTS-duration
drift (the Gemini TTS is nondeterministic, so segment durations — and
therefore clamped starts — move by fractions of a second). Byte-identity
is NOT expected; structurally different timelines (missing cues, reordered
segments, big start shifts) are regressions.

## Recording rules (each learned the hard way)

- Each recorded page needs its **own window** — background tabs render at
  the window's size, not their viewport.
- Set **viewport BEFORE goto** — Gemini decides element visibility at load
  and never re-evaluates on resize.
- Gemini requires **trusted locator clicks and a visible window**;
  synthetic events and hidden windows silently fail.
- Tail frames freeze at paint-idle — append a real-state screenshot as the
  final frame.
- Purge stale frames between takes (stop_dual does this — the bug bit
  twice).
- macOS un-hides the app when a new window opens; `hide_chrome()` re-hides
  by PID. But long-hidden windows eventually wedge the renderer — prefer
  visible-but-backgrounded during long sessions.
- The split-screen takes pin BOTH halves to identical viewports; the
  composite depends on every captured frame having the same geometry.
- The two-part Gemini paste exists because Gemini's entry rewriter rejects
  the full prompt (error 13). Re-verify per language.
- **Claude read-after-write lag is minutes**: after Save, reloads keep
  showing the OLD field value for a long time before flipping. Poll
  patiently (~3–4 min) before concluding a save failed — two false
  "did not persist" readings came from exactly this.

## TTS notes

- Default engine: Gemini (`gemini-3.1-flash-tts-preview`), voice per
  language config. Segments cached in `out/tts/<lang>/` by SHA1 of
  (cache_prefix + text) — bump `tts.cache_prefix` to force regeneration.
- The TTS mangles novel words — **spell them out** in VO text ("iaser" is
  written `I-A-S-E-R dot A-I`), and map spoken forms back to readable text
  in `spellouts.toml` so captions show `s.iaser.ai/prompt`. Expect a
  listen-check on every new language/voice.

## Upload (YouTube Studio)

Channel: **iaser-ai**, id `UCF1yEgoyLfbgTUpeMn2ruqA`. The Google login's
DEFAULT channel is a personal one — **never upload there**. All Studio
navigation is pinned to
`studio.youtube.com/channel/UCF1yEgoyLfbgTUpeMn2ruqA` and
`upload.preflight_channel()` must pass (it aborts on any mismatch) before
any upload action.

Manual flow (automated flow ships in the uploads plan phase):
1. Content page → Create → Upload videos → `input[type=file]`.
2. Details: title + description, audience `VIDEO_MADE_FOR_KIDS_NOT_MFK`,
   **Show more → Video language** (must be set or the captions row is
   locked).
3. Next ×3 → Visibility **PRIVATE** → Done. Always Private; publishing is
   a human decision.
4. Captions: `studio.youtube.com/video/<id>/translations` → language row →
   pencil → Upload file → **With timing** → select `.srt` → Publish.

Gotchas:
- A long-running/hidden Chrome **wedges** (blank tabs, hanging gotos,
  wizard resets). Restart Chrome with the same profile; logins and drafts
  survive. Don't fight a wedged browser.
- If the upload dialog dies mid-flow the video persists as a **Draft**
  with every field saved — resume via "Edit draft".
- `pages[0]` over CDP is not stable; verify `pg.url` before acting.

## Adding a language

1. `languages/<lang>/`: `config.toml` (dir, voice, style, recording
   strings, YouTube language), `prompt.txt` (translated prompt),
   `vo/{chatgpt,claude,gemini}.toml`, `cards/{intro,outro}.html`,
   `spellouts.toml`.
2. RTL languages: set `dir = "rtl"` and add font/line-height overrides in
   `[cards] css` (Nastaliq needs taller line metrics than Naskh).
3. Record clips (`companion record`), then build, captions, listen-check,
   watch-through, upload.
