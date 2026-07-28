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
    cfg = load_language(lang)
    if video not in VIDEOS:
        raise typer.BadParameter(f"video must be one of {', '.join(VIDEOS)}")
    driver = importlib.import_module(f".drivers.{video}",
                                     package="companion_pipeline")
    driver.record(cfg)


@app.command()
def upload(lang: str = typer.Option(...),
           video: str = typer.Option(None)):
    """Upload built videos Private to the iaser-ai channel (guarded)."""
    load_language(lang)
    raise typer.Exit(  # implemented in the uploads plan phase
        "upload flow ships in the uploads plan phase; use the README's "
        "manual Studio flow meanwhile. The channel preflight guard lives "
        "in companion_pipeline/upload.py.")


@app.command()
def languages():
    """List available language configs."""
    from .config import available_languages
    for code in available_languages():
        cfg = load_language(code)
        print(f"{code}  {cfg.name}  dir={cfg.direction}  "
              f"voice={cfg.tts.voice} ({cfg.tts.engine})")
