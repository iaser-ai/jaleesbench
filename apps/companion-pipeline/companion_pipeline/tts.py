"""TTS engine adapters. Gemini is the default engine; a fallback engine is
added here as a new synth function + ENGINES entry only if a language fails
the listen test (see the plan's Phase 2 decision rule).

Segments are cached in out/tts/<lang>/ keyed by SHA1(cache_prefix + text) —
bump the language's tts.cache_prefix to force full re-generation.
"""

import base64
import hashlib
import subprocess
from pathlib import Path

import httpx

from .config import LanguageConfig, OUT_DIR, gemini_api_key


def _cache_dir(lang: str) -> Path:
    d = OUT_DIR / "tts" / lang
    d.mkdir(parents=True, exist_ok=True)
    return d


def gemini_generate(text: str, style: str, voice: str, model: str,
                    wav: Path) -> Path:
    """One Gemini TTS call -> wav at 24 kHz mono. Shared by the normal
    build path and the voice listen-test spike, so the spike exercises the
    exact code that production narration uses."""
    url = ("https://generativelanguage.googleapis.com/v1beta/models/"
           f"{model}:generateContent?key={gemini_api_key()}")
    resp = httpx.post(
        url,
        json={
            "contents": [{"parts": [{"text": style + text}]}],
            "generationConfig": {
                "responseModalities": ["AUDIO"],
                "speechConfig": {"voiceConfig": {
                    "prebuiltVoiceConfig": {"voiceName": voice}}}},
        },
        timeout=120.0,
    )
    if resp.status_code != 200:
        raise RuntimeError(
            f"Gemini TTS HTTP {resp.status_code}: {resp.text[:300]}")
    d = resp.json()
    try:
        pcm = base64.b64decode(
            d["candidates"][0]["content"]["parts"][0]["inlineData"]["data"])
    except (KeyError, IndexError) as e:
        raise RuntimeError(
            f"Gemini TTS response missing audio data ({e}); "
            f"response head: {str(d)[:300]}") from e
    raw = wav.with_suffix(".pcm")
    raw.write_bytes(pcm)
    subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error", "-f", "s16le", "-ar", "24000",
         "-ac", "1", "-i", str(raw), str(wav)], check=True)
    return wav


def _gemini_synth(text: str, cfg: LanguageConfig, wav: Path) -> None:
    gemini_generate(text, cfg.tts.style, cfg.tts.voice, cfg.tts.model, wav)


ENGINES = {"gemini": _gemini_synth}


def synthesize(text: str, cfg: LanguageConfig) -> Path:
    """Return a cached (or newly generated) wav for this narration text."""
    if cfg.tts.engine not in ENGINES:
        raise RuntimeError(
            f"unknown TTS engine {cfg.tts.engine!r} for language "
            f"{cfg.lang!r} — available: {', '.join(ENGINES)}")
    key = hashlib.sha1(
        (cfg.tts.cache_prefix + ":" + text).encode()).hexdigest()[:16]
    wav = _cache_dir(cfg.lang) / f"seg-{key}.wav"
    if wav.exists():
        return wav
    ENGINES[cfg.tts.engine](text, cfg, wav)
    return wav


def media_duration(p: Path) -> float:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "csv=p=0", str(p)], capture_output=True, text=True)
    if out.returncode != 0 or not out.stdout.strip():
        raise RuntimeError(f"ffprobe failed for {p}: {out.stderr[:200]}")
    return float(out.stdout)
