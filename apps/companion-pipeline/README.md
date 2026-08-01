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

  **The profile lives at `~/jaleesbench-rec/rec-profile`.** It is not
  reproducible — rebuilding it means re-authenticating four surfaces by
  hand — so it must stay on a durable path. It spent 07-29 to 07-31
  inside a dead Claude session's scratchpad under `/private/tmp`, one
  purge away from gone, which stalled every take for two days. Never
  point `--user-data-dir` at a scratchpad, a temp dir, or anything inside
  the repo. macOS launch:

  ```bash
  "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
    --user-data-dir="$HOME/jaleesbench-rec/rec-profile" \
    --remote-debugging-port=9222 --lang=<code>
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

## Card fonts (vendored, and why)

Card faces are **checked into `assets/fonts/`** and embedded as data-URI
`@font-face` rules, not named-and-hoped-for. Chrome substitutes a missing
family **silently**, so naming one bought nothing: `ur` rendered correctly
only because macOS ships `NotoNastaliq.ttc`, and `ar` had been rendering
in a Geeza Pro fallback the whole time — nobody had ever seen an `ar` card
in the face its config named. A language's `[cards] require_font` must
name a family present in `cards.VENDORED_FONTS`, and `render_card` fails
before screenshotting if it doesn't resolve. Adding a language means
adding its woff2 + OFL text; see `assets/fonts/README.md`.

**`document.fonts.check()` cannot detect a missing font — it returns
`true` for families that do not exist.** Verified directly: a nonsense
name checks `true`. Anything relying on it to confirm a face loaded is
reading a constant. The working test is metric comparison — render the
same text under the target family and under a family that cannot exist,
both backed by the same generic, and compare widths; identical means the
target never resolved (`cards._FONT_PROBE_JS`). `document.fonts.load()` +
`document.fonts.ready` are still needed first, to await decoding — they
just can't tell you *what* you got. Belt-and-braces verification
(computed styles, plus self-hosting the file so there is nothing to miss)
is sound; `document.fonts.check()` alone is not.

## Gemini saved-info: read back every write (STANDING RULE)

**Every entry write, every language, gets a read-back verification.** The
submit dialog is not evidence. Three distinct failure modes have been
observed, and only one of them announces itself:

| Mode | Dialog | Actually stored |
|---|---|---|
| Hard refusal | `لا يستطيع Gemini حفظ هذه المعلومات` ("cannot save") | nothing |
| Retryable false-error | `حدث خطأ … يُرجى النقر على "إرسال"` | sometimes nothing, sometimes the entry |
| **Silent mangle** | **closes normally — reports success** | **a rewritten entry** |

The third is the dangerous one. On 2026-08-01 an Arabic part 2 closed the
dialog cleanly and stored a version with the prose lead-in stripped and
six second-person imperatives flipped to first person — turning
instructions *to* Gemini into claims *about the account holder*,
including the safeguarding and anti-fabrication clauses. Nothing errored.

**Read back the WHOLE list and compare, normalized for whitespace.** Do
NOT probe by searching for strings you sent: a rewriter that edits them
makes that search return nothing, which reads as "silently dropped" when
the truth is "silently rewritten". That exact mistake nearly entered the
record. `innerText` also collapses blank lines, so compare on
`re.sub(r"\s+", " ", …)` rather than raw length — a 1-char delta is
usually your reader, not the rewriter.

Truth is the list, never the dialog.

## Recording rules (each learned the hard way)

- Each recorded page needs its **own window** — background tabs render at
  the window's size, not their viewport. The split-screen drivers no
  longer reuse the rig's tabs (all of which share one window, so only one
  half could ever be foreground — that shipped a visibly shrunken,
  letterboxed right half). They call `Session.new_window()`, which opens a
  real separate window via `window.open` with explicit geometry. Note raw
  CDP `Target.createTarget` also opens a window, but an **already-connected
  Playwright session never attaches to it**, so the page is invisible to
  the driver — use the popup route.
- **Keep `out/recordings/frames-<name>-{0,1}/`** until a take is accepted.
  They are the take's negatives: any tail fix (a stray toast in the closing
  hold, a bad final frame) rebuilds from them in ONE encode instead of
  re-encoding the mp4 a second time. `stop_dual` purges them per take name,
  so they survive only until that clip is re-recorded.
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
  patiently (~3–4 min) before concluding a save failed — three false
  "did not persist" readings came from exactly this. The driver's reset
  verify loop is budgeted ~4 min for this reason; an earlier ~45s budget
  aborted an ar take whose reset had in fact succeeded (the field flipped
  to the saved value minutes later).
- **Per-language ChatGPT UI labels**: validate them off camera before the
  first take of a language. `save` only renders once the field is DIRTY
  (a clean-state probe won't find it), and `toast_substr` must be the FULL
  confirmation phrase — the short form also matches the always-visible
  "Custom instructions" section button, so the driver's toast wait can
  resolve against the heading and miss the actual toast beat.
- **Gemini saved-info automation specifics**: confirm buttons in its
  dialogs are `mat-tonal-button` (NOT `mat-primary`) — include it in
  selectors or clicks silently miss; entry rows expose kebab menus
  (`more_vert` icon), not always-visible delete icons; the header's
  Delete All button (+ tonal confirm) is the reliable bulk cleanup; the
  entry rewriter paraphrases every saved entry and can even
  language-switch (observed: Arabic part 2 rewritten into English).
- **Gemini submit dialogs LIE in both directions**: a "retryable error"
  dialog can appear when the entry actually SAVED (blind retries create
  duplicates), and a clean dialog-close can hide a silent drop (the
  rewriter appears to dedupe entries that closely echo an existing one).
  The ONLY save signal is the entry list itself — reload and check it
  grew before retrying, and select dialog buttons by TEXT (button order
  varies between dialog types).

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

## Target-language UI routes (per assistant)

Verified 2026-07-28 (read-only probes against the live products):

| Assistant | Route to ar/ur/id UI | Status |
|---|---|---|
| Gemini | `?hl=<code>` on the URL (e.g. `gemini.google.com/app?hl=ur`) | **VERIFIED** — ar/ur render full RTL-mirrored UIs (`lang`/`dir` set), id renders Indonesian |
| ChatGPT | ignores `?hl`; use Settings → Language (account setting — temporary write, restore after) or leave on Auto-detect and relaunch the recording Chrome with `--lang=<code>` | route identified; verify at recording time |
| Claude | ignores `?hl`; follows browser language — relaunch the recording Chrome with `--lang=<code>` | route identified; verify at recording time |

**Session-start check (standing, per Waleed)**: Claude ships no ar/ur/id
interface language today (21-language list verified 2026-07-28), so
Claude cells record with the EN UI + translated prompt + target-language
narration bridging — Waleed's explicit fallback. His standing preference
is native target-language UI wherever it exists: **re-check Claude's
Settings → Language list at the start of every recording session**; if
the target language has shipped, record Claude natively instead.

Per-language recording sessions therefore launch Chrome as:

```bash
google-chrome --user-data-dir=<rec-profile> --remote-debugging-port=9222 --lang=<code>
```

and pin Gemini pages with `?hl=<code>`. RTL UIs mirror layouts — drivers
must keep using role/label-based locators, never coordinates.

## Localized prompt pages (recording sources)

Live **public** per-language pages, byte-verified by iaser.ai against
`handoff/prompt-page/`: `iaser.ai/{ar,ur,id}/prompt`. Structure:
3 `<pre><code>` blocks (full prompt, Gemini part 1, part 2) with
**target-language** copy buttons — config `copy_button_label`: ar `نسخ`,
ur `نقل کریں`, id `Salin`; the EN page uses "Copy prompt". Re-check these
labels after any iaser.ai page revision: the earlier staging pages used a
plain English "Copy", and the public rollout localized it.
Each copy button flashes the copied char count on click —
**capture that flash in takes as the on-camera honesty check**; the
driver-level clipboard assert stays. Translation revisions route through
the architect for iaser.ai re-vendor + re-verify.

## Take log (accepted clips and any edits)

Accepted clips live in `inputs/clips/<lang>/`. Anything done to a clip
after capture is recorded here — a clip that is not a straight `companion
record` output must say so.

### Status: 2 of 9 clips accepted

| lang | chatgpt | claude | gemini |
|---|---|---|---|
| ar | SUPERSEDED — retake | SUPERSEDED — retake | SUPERSEDED — retake |
| ur | **accepted** | **accepted** | BLOCKED (see below) |
| id | not shot | not shot | not shot |

**ur (2026-07-29)** — `copypaste-chatgpt.mp4` and `copypaste-claude.mp4`
are unedited captures on the article-source flow. `gemini` is **blocked**,
not merely unshot: the ur part-2 paste triggers a hard Gemini saved-info
refusal (`Gemini اس معلومات کو محفوظ نہیں کر سکتا`), root-caused to
bullet 2 — the safeguarding line — refusing on its own in a 253-char
minimal repro. Three rewordings that preserve the duty-of-care verbatim
were all refused, so the fix is not a wording change; it is with the
architect. This is also a live user-facing bug: ur readers following the
published article cannot save that instruction to Gemini at all.

**ar (2026-07-29) — SUPERSEDED, all three need retakes.** The clips still
in `inputs/clips/ar/` were shot entering at `/ar/prompt`, before the
directive that takes must enter on the **official article page** (one URL
on camera, `s.iaser.ai/prompt`, then the language link clicked on camera).
They are kept only as reference until the retakes land. What follows
documents the trim technique on the old gemini clip — the technique and
the "keep frames-dirs until a take is accepted" rule stand, the clip does
not.

The raw 46.3s ar gemini take picked up a Gemini-side
`تعذّر عرض المحادثات الأخيرة` ("couldn't load recent
conversations") error toast at t≈43.3s, which sat through the whole closing
hold. Waleed's call was fix-in-edit, not retake. Rebuilt from the take's
own frames at `frames-copypaste-gemini-ar-{0,1}` — frames 0..518
(t≤43.167s) plus a 1.6s clone-hold on the last clean frame, one encode, no
second generation (PSNR 48.6dB vs the raw take over the shared range):

```bash
ffmpeg -framerate 12 -i out/recordings/frames-copypaste-gemini-ar-0/f%05d.png \
       -framerate 12 -i out/recordings/frames-copypaste-gemini-ar-1/f%05d.png \
  -filter_complex "[0:v]trim=end_frame=519,setpts=PTS-STARTPTS,scale=720:550:force_original_aspect_ratio=decrease,pad=720:550:(ow-iw)/2:(oh-ih)/2:color=#0d0d0d[l];[1:v]trim=end_frame=519,setpts=PTS-STARTPTS,scale=720:550:force_original_aspect_ratio=decrease,pad=720:550:(ow-iw)/2:(oh-ih)/2:color=#0d0d0d[r];[l][r]hstack=inputs=2,tpad=stop_mode=clone:stop_duration=1.6[v]" \
  -map "[v]" -c:v libx264 -pix_fmt yuv420p -crf 21 out.mp4
```

The trim lands the clip on Gemini's own `تم حفظ التعليمات` ("instructions
saved") toast — the same confirmation beat the ChatGPT and Claude clips end
on, so the edit improves the ending rather than merely salvaging it.

## Adding a language

1. `languages/<lang>/`: `config.toml` (dir, voice, style, recording
   strings, YouTube language), `prompt.txt` (translated prompt),
   `vo/{chatgpt,claude,gemini}.toml`, `cards/{intro,outro}.html`,
   `spellouts.toml`.
2. RTL languages: set `dir = "rtl"` and add font/line-height overrides in
   `[cards] css` (Nastaliq needs taller line metrics than Naskh).
3. **Rec the assistant UIs before the first take.** Open ChatGPT and Gemini
   under the target locale off-camera and read the labels live into
   `[recording.chatgpt_ui]` / `[recording.gemini_ui]`. `load_language`
   refuses a non-EN language that has neither section — the EN fallback
   would send the driver hunting for "Personalization" in a localized
   interface, which is how the first Urdu take died. Partial sections are
   legal and merge over the EN defaults. Two labels don't render in a
   clean state: ChatGPT's `save` only appears once the field is **dirty**
   (and Cancel precedes it in DOM order — don't grab the first new
   button), and Gemini's `delete_all` only appears with a **non-empty**
   list. Watch for one string serving two roles: `personalization` is the
   ACCOUNT-MENU item, which in ur differs from the settings dialog's own
   tab label, while ar uses one string for both.
4. Record clips (`companion record`), then build, captions, listen-check,
   watch-through, upload.

**Outstanding**: `id` has neither UI section yet — its recon is the first
step of the id recording session.

## Privacy sweep before committing a clip or uploading a video (STANDING RULE)

**Every clip gets a sidebar/recents pass before it is committed or
uploaded.** This is not optional and it is not a spot check.

It exists because it already failed: `inputs/clips/{ar,ur}/copypaste-chatgpt.mp4`
open the ChatGPT sidebar as an on-camera beat, and by the time those takes
were shot the Recents list was populated — seven real conversation titles,
legible, committed to a **public** repo. The EN clip was clean only by
luck of timing: it was recorded while that list happened to be empty.

Two things that did NOT work, so don't repeat them:

- **Sampling.** A 1-in-5-frames pass over the same clips found nothing.
  `companion_pipeline.privacy.distinct_frames()` reads every frame.
- **A whole-frame hash.** A 16×16 average hash cannot see a 250px sidebar
  appear in a 1376px frame. Change detection is per-block on a 160×120
  grid, which is what makes a panel or dropdown opening visible.

```python
from companion_pipeline.privacy import distinct_frames, contact_sheet
kept = distinct_frames(Path("inputs/clips/xx/copypaste-chatgpt.mp4"))
contact_sheet(kept, Path("out/privacy/xx-chatgpt.png"))   # then LOOK at it
```

The tool flags candidate frames; a human reads them against
`privacy.CHECKLIST`. It deliberately does not classify — the failure mode
was never detection, it was that nobody looked. `IDENTITY_CHECKLIST` is
tracked separately: the author's own name and handle are usually intended,
but they get inventoried rather than assumed.

**Upstream fix, better than any check**: the recording drivers should
clear or collapse Recents during their off-camera reset, the same way the
ChatGPT driver already empties the custom-instructions field. A guard that
depends on someone remembering to look is the weaker half of this.
