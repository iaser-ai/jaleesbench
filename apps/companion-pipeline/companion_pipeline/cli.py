"""companion — the companion-prompt asset pipeline CLI.

Stages:  record -> build -> captions -> upload   (each takes --lang)
See README.md for the full runbook including prerequisites and the
hard-won recording/upload gotchas.
"""

import importlib

import typer

from .config import VIDEOS, load_language

app = typer.Typer(no_args_is_help=True, add_completion=False)


def _videos(video: str | None) -> tuple[str, ...]:
    if video is None:
        return VIDEOS
    if video not in VIDEOS:
        raise typer.BadParameter(
            f"video must be one of {', '.join(VIDEOS)}")
    return (video,)


@app.command()
def build(lang: str = typer.Option(..., help="Language code, e.g. en"),
          video: str = typer.Option(None, help="chatgpt|claude|gemini "
                                    "(default: all three)")):
    """TTS narration + card render + ffmpeg assembly -> out/videos/<lang>/."""
    from .assemble import build_video
    cfg = load_language(lang)
    for v in _videos(video):
        print(f"=== build {lang}/{v} ===")
        build_video(cfg, v)


@app.command()
def captions(lang: str = typer.Option(...),
             video: str = typer.Option(None)):
    """Exact-timeline .srt files -> out/videos/<lang>/."""
    from .captions import build_srt
    cfg = load_language(lang)
    for v in _videos(video):
        print(f"=== captions {lang}/{v} ===")
        build_srt(cfg, v)


@app.command()
def record(lang: str = typer.Option(...),
           video: str = typer.Option(..., help="chatgpt|claude|gemini — "
                                     "one take at a time")):
    """Record a walkthrough clip via the CDP Chrome (see README setup)."""
    # Recording precedes VO authoring; drivers read only [recording].
    cfg = load_language(lang, require_later_assets=False)
    if video not in VIDEOS:
        raise typer.BadParameter(f"video must be one of {', '.join(VIDEOS)}")
    driver = importlib.import_module(f".drivers.{video}",
                                     package="companion_pipeline")
    driver.record(cfg)


@app.command()
def upload(lang: str = typer.Option(...),
           video: str = typer.Option(None)):
    """NOT YET IMPLEMENTED — the guarded upload flow ships in the uploads
    plan phase. Use the README's manual Studio flow meanwhile."""
    load_language(lang)
    typer.echo(
        "companion upload is not implemented yet: the automated flow ships "
        "in the uploads plan phase. Use the README's manual Studio flow; "
        "the channel preflight guard is available as "
        "companion_pipeline.upload.preflight_channel().", err=True)
    raise typer.Exit(code=2)


@app.command()
def all(lang: str = typer.Option(..., help="Language code, e.g. en")):
    """Run the full automatable chain for a language: build + captions for
    all three videos. (record and upload are excluded — they need a live,
    logged-in CDP Chrome; run them explicitly.)"""
    from .assemble import build_video
    from .captions import build_srt
    cfg = load_language(lang)
    for v in VIDEOS:
        print(f"=== build {lang}/{v} ===")
        build_video(cfg, v)
        print(f"=== captions {lang}/{v} ===")
        build_srt(cfg, v)


@app.command()
def languages():
    """List language configs (incomplete ones show what's missing)."""
    from .config import available_languages, validate_skeleton
    for code in available_languages():
        missing = validate_skeleton(code)  # raises if the core is invalid
        cfg = None if missing else load_language(code)
        if cfg:
            print(f"{code}  {cfg.name}  dir={cfg.direction}  "
                  f"voice={cfg.tts.voice} ({cfg.tts.engine})")
        else:
            print(f"{code}  skeleton OK — awaiting {', '.join(missing)}")


@app.command("spike-tts")
def spike_tts(lang: str = typer.Option(None, help="ar|ur|id (default: "
                                       "all three)"),
              voices: str = typer.Option(None, help="comma-separated "
                                         "candidate voices (default: the "
                                         "spike's candidate set)")):
    """Listen-test spike: generate lang x voice narration samples into
    out/spike/ for human evaluation (plan phase tts_spike)."""
    from .spike import CANDIDATE_VOICES, SAMPLE_TEXTS, run_spike
    langs = (lang,) if lang else tuple(SAMPLE_TEXTS)
    vv = tuple(v.strip() for v in voices.split(",")) if voices \
        else CANDIDATE_VOICES
    run_spike(langs, vv)
