"""Language-config loading.

Everything language-dependent lives under languages/<lang>/ as data:
config.toml (voice/style/direction/recording params), prompt.txt (the
companion prompt in that language), vo/<video>.toml (narration scripts +
beat offsets), cards/{intro,outro}.html (card body templates), and
spellouts.toml (TTS spell-out -> written-form mappings for captions).

Loading is fail-fast: a missing file or key aborts with an error naming the
language and path — no defaults, no fallbacks.
"""

import os
import tomllib
from dataclasses import dataclass
from pathlib import Path

PIPELINE_ROOT = Path(__file__).resolve().parents[1]
LANGUAGES_DIR = PIPELINE_ROOT / "languages"
INPUTS_DIR = PIPELINE_ROOT / "inputs"
OUT_DIR = PIPELINE_ROOT / "out"

VIDEOS = ("chatgpt", "claude", "gemini")


class ConfigError(RuntimeError):
    pass


@dataclass(frozen=True)
class TtsConfig:
    engine: str
    model: str
    voice: str
    style: str
    cache_prefix: str


@dataclass(frozen=True)
class Segment:
    offset: float
    text: str


@dataclass(frozen=True)
class VideoConfig:
    name: str            # chatgpt | claude | gemini
    clip: str            # filename under inputs/clips/<lang>/
    product: str         # display name used in card templates
    others: str          # "the other two" phrase for outro card/VO
    intro_vo: str
    outro_vo: str
    segments: tuple[Segment, ...]


@dataclass(frozen=True)
class LanguageConfig:
    lang: str
    name: str
    direction: str       # "ltr" | "rtl"
    tts: TtsConfig
    card_css: str        # per-language CSS override block (may be empty)
    prompt: str
    prompt_url: str
    prompt_url_display: str   # short form shown on recorded cards
    prompt_chars: int
    gemini_part_min: int      # expected char bounds for the two-part paste
    gemini_part_max: int
    card_goto_line: str       # recorded card text: "In your browser, go to"
    card_open_line: str       # recorded card text: "Now open"
    account_label: str
    youtube_language: str
    videos: dict[str, VideoConfig]
    spellouts: tuple[tuple[str, str], ...]  # (spoken, written), in order
    intro_card_html: str
    outro_card_html: str

    @property
    def clips_dir(self) -> Path:
        return INPUTS_DIR / "clips" / self.lang

    def clip_path(self, video: str) -> Path:
        p = self.clips_dir / self.videos[video].clip
        if not p.exists():
            raise ConfigError(
                f"[{self.lang}/{video}] clip not found: {p} — record it "
                f"first (companion record) or add it to inputs/clips/")
        return p


def _need(table: dict, key: str, ctx: str):
    if key not in table:
        raise ConfigError(f"[{ctx}] missing required key: {key!r}")
    return table[key]


def _read(path: Path, ctx: str) -> str:
    if not path.exists():
        raise ConfigError(f"[{ctx}] missing required file: {path}")
    return path.read_text(encoding="utf-8")


def _load_toml(path: Path, ctx: str) -> dict:
    if not path.exists():
        raise ConfigError(f"[{ctx}] missing required file: {path}")
    with open(path, "rb") as f:
        return tomllib.load(f)


def available_languages() -> list[str]:
    return sorted(p.name for p in LANGUAGES_DIR.iterdir()
                  if (p / "config.toml").exists())


def _parse_core(base: Path, ctx: str) -> dict:
    """Validate + parse the phase-independent core of a language: what
    config.toml and spellouts.toml must contain from the moment a language
    skeleton exists. Later-phase assets (prompt.txt, vo/, cards/) are NOT
    required here — load_language() layers those on top."""
    cfg = _load_toml(base / "config.toml", ctx)

    direction = _need(cfg, "dir", ctx)
    if direction not in ("ltr", "rtl"):
        raise ConfigError(f"[{ctx}] dir must be 'ltr' or 'rtl', "
                          f"got {direction!r}")

    t = _need(cfg, "tts", ctx)
    tts = TtsConfig(
        engine=_need(t, "engine", f"{ctx}.tts"),
        model=_need(t, "model", f"{ctx}.tts"),
        voice=_need(t, "voice", f"{ctx}.tts"),
        style=_need(t, "style", f"{ctx}.tts"),
        cache_prefix=_need(t, "cache_prefix", f"{ctx}.tts"),
    )

    rec = _need(cfg, "recording", ctx)
    yt = _need(cfg, "youtube", ctx)

    sp = _load_toml(base / "spellouts.toml", f"{ctx}/spellouts")
    spellouts = tuple(
        (_need(r, "spoken", f"{ctx}/spellouts"),
         _need(r, "written", f"{ctx}/spellouts"))
        for r in sp.get("replacements", []))

    return {
        "name": _need(cfg, "name", ctx),
        "direction": direction,
        "tts": tts,
        "card_css": cfg.get("cards", {}).get("css", ""),
        "rec": rec,
        "yt": yt,
        "spellouts": spellouts,
    }


def _lang_base(lang: str) -> Path:
    base = LANGUAGES_DIR / lang
    if not base.is_dir():
        raise ConfigError(
            f"unknown language {lang!r} — expected directory {base} "
            f"(available: {', '.join(available_languages()) or 'none'})")
    return base


def validate_skeleton(lang: str) -> list[str]:
    """Validate a language's core config without requiring later-phase
    assets. Returns the later-phase files still missing (empty when the
    language is complete). Raises ConfigError when the core itself is
    invalid — a skeleton must always have a fully valid core."""
    base = _lang_base(lang)
    _parse_core(base, lang)
    later_phase = [base / "prompt.txt",
                   *(base / "vo" / f"{v}.toml" for v in VIDEOS),
                   base / "cards" / "intro.html",
                   base / "cards" / "outro.html"]
    return [str(p.relative_to(base)) for p in later_phase if not p.exists()]


def load_language(lang: str) -> LanguageConfig:
    base = _lang_base(lang)
    ctx = lang
    core = _parse_core(base, ctx)
    rec, yt = core["rec"], core["yt"]

    prompt = _read(base / "prompt.txt", ctx)
    declared = int(_need(rec, "prompt_chars", f"{ctx}.recording"))
    if len(prompt) != declared:
        raise ConfigError(
            f"[{ctx}] prompt.txt is {len(prompt)} chars but config.toml "
            f"declares prompt_chars = {declared} — the file is copied "
            f"byte-for-byte by recording drivers and the prompt page, so "
            f"these must match exactly (watch for trailing newlines)")

    videos: dict[str, VideoConfig] = {}
    for name in VIDEOS:
        vctx = f"{ctx}/vo/{name}"
        v = _load_toml(base / "vo" / f"{name}.toml", vctx)
        raw_segs = _need(v, "segments", vctx)
        if not raw_segs:
            raise ConfigError(f"[{vctx}] segments must not be empty")
        segs = tuple(
            Segment(offset=float(_need(s, "offset", vctx)),
                    text=_need(s, "text", vctx))
            for s in raw_segs)
        videos[name] = VideoConfig(
            name=name,
            clip=_need(v, "clip", vctx),
            product=_need(v, "product", vctx),
            others=_need(v, "others", vctx),
            intro_vo=_need(v, "intro_vo", vctx),
            outro_vo=_need(v, "outro_vo", vctx),
            segments=segs,
        )

    return LanguageConfig(
        lang=lang,
        name=core["name"],
        direction=core["direction"],
        tts=core["tts"],
        card_css=core["card_css"],
        prompt=prompt,
        prompt_url=_need(rec, "prompt_url", f"{ctx}.recording"),
        prompt_url_display=_need(rec, "prompt_url_display",
                                 f"{ctx}.recording"),
        prompt_chars=int(_need(rec, "prompt_chars", f"{ctx}.recording")),
        gemini_part_min=int(_need(rec, "gemini_part_min",
                                  f"{ctx}.recording")),
        gemini_part_max=int(_need(rec, "gemini_part_max",
                                  f"{ctx}.recording")),
        card_goto_line=_need(rec, "card_goto_line", f"{ctx}.recording"),
        card_open_line=_need(rec, "card_open_line", f"{ctx}.recording"),
        account_label=_need(rec, "account_label", f"{ctx}.recording"),
        youtube_language=_need(yt, "video_language", f"{ctx}.youtube"),
        videos=videos,
        spellouts=core["spellouts"],
        intro_card_html=_read(base / "cards" / "intro.html", ctx),
        outro_card_html=_read(base / "cards" / "outro.html", ctx),
    )


def gemini_api_key() -> str:
    """GEMINI_API_KEY from the environment, else the repo root .env."""
    key = os.environ.get("GEMINI_API_KEY")
    if key:
        return key
    env_file = PIPELINE_ROOT.parents[1] / ".env"
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            if line.startswith("GEMINI_API_KEY"):
                return line.split("=", 1)[1].strip()
    raise ConfigError(
        "GEMINI_API_KEY not set — export it or add it to the repo-root .env")
