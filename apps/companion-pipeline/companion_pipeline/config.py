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
    copy_button_label: str    # PROMPT PAGE's copy-button text
    # Takes open on the official article — that is what a real reader
    # lands on — so the article is a second copy SOURCE with its own
    # button label. The two pages are localized independently, so these
    # stay separate keys rather than one overloaded label.
    #
    # ONE url, every language: the short link is the only address that
    # appears on camera or in config, because it is the only one a viewer
    # can realistically retype. It lands on the EN article and the take
    # clicks that page's own language link on camera to reach the
    # localized one — the localized URL is never navigated to directly,
    # so it is deliberately NOT stored here.
    article_entry_url: str        # short link, identical for all languages
    article_url_display: str      # what the on-camera card shows
    article_lang_link: str        # native label on the EN article ("" = EN)
    article_copy_button_label: str
    prompt_chars: int
    gemini_part_min: int      # expected char bounds for the two-part paste
    gemini_part_max: int
    # Which bullet the two-part split falls after. 3 (an even 3/3) is the
    # shipped default and what EN/ar/id use. ur moved to 5 because Gemini
    # hard-REFUSES its bullet 5 — the safeguarding line — as a saved-info
    # entry when it arrives in part 2, and no rewording that preserved the
    # duty of care got past it. Riding in part 1 it saves, so the boundary
    # moves and the words do not. See reference/translation-review.md.
    gemini_split_after: int
    # Prose line prepended to Gemini part 2 ONLY (not part of the
    # canonical prompt): Gemini's entry rewriter keeps entries in-language
    # when they open with prose but can language-switch bare-bullet
    # openings (observed: Arabic part 2 rewritten into English). Empty
    # for EN (shipped without it).
    gemini_part2_leadin: str
    # Gemini UI labels for the recording driver (localized per ?hl=).
    # Keys: add, submit, delete_all. Verified live per language before
    # takes; the driver also uses locale-independent fallbacks.
    gemini_ui: dict[str, str]
    # ChatGPT UI labels for the recording driver (localized). Keys:
    # personalization, ci_placeholder_substr, save, toast_substr.
    chatgpt_ui: dict[str, str]
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
        if video not in self.videos:
            raise ConfigError(
                f"[{self.lang}/{video}] no VO config — this LanguageConfig "
                f"was loaded with require_later_assets=False (the recording "
                f"path). Reload with load_language({self.lang!r}) to build.")
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


def _ui_section(rec: dict, key: str, lang: str, ctx: str,
                en_defaults: dict[str, str]) -> dict[str, str]:
    """Merge a language's assistant-UI labels over the EN defaults.

    A *partial* section is fine and merges. A section that is absent
    entirely, on a non-EN language, is refused: it means nobody has recced
    that assistant's UI in this language yet, and the silent EN fallback
    sends the driver hunting for "Personalization" under a localized
    interface — the exact way the first Urdu take died.
    """
    if lang != "en" and key not in rec:
        raise ConfigError(
            f"[{ctx}.recording] missing [{ctx}.recording.{key}] — the "
            f"assistant's UI labels for {lang!r} have not been observed "
            f"yet. Falling back to the EN labels would make the driver "
            f"hunt for English strings in a {lang} interface. Open the "
            f"assistant under the {lang} locale, read the labels live, and "
            f"add them (see README 'Adding a language').")
    return {**en_defaults, **rec.get(key, {})}


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


def load_language(lang: str, *,
                  require_later_assets: bool = True) -> LanguageConfig:
    """Load a language config.

    `require_later_assets=False` skips the later-phase assets named by
    `validate_skeleton` — the `vo/*.toml` scripts and the cards — leaving
    `videos` empty and the card HTML blank. The recording drivers read only
    the core `[recording]` block, and clips are captured a phase before VO
    and cards are authored, so a take must not be blocked on assets that do
    not exist yet. Every other caller keeps the fail-fast default.
    """
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
    for name in VIDEOS if require_later_assets else ():
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
        copy_button_label=_need(rec, "copy_button_label",
                                f"{ctx}.recording"),
        article_entry_url=_need(rec, "article_entry_url",
                                f"{ctx}.recording"),
        article_url_display=_need(rec, "article_url_display",
                                  f"{ctx}.recording"),
        article_lang_link=rec.get("article_lang_link", ""),
        article_copy_button_label=_need(rec, "article_copy_button_label",
                                        f"{ctx}.recording"),
        prompt_chars=int(_need(rec, "prompt_chars", f"{ctx}.recording")),
        gemini_part_min=int(_need(rec, "gemini_part_min",
                                  f"{ctx}.recording")),
        gemini_part_max=int(_need(rec, "gemini_part_max",
                                  f"{ctx}.recording")),
        gemini_split_after=int(rec.get("gemini_split_after", 3)),
        gemini_part2_leadin=_need(rec, "gemini_part2_leadin",
                                  f"{ctx}.recording"),
        # MERGE over the EN defaults, don't replace them: a language that
        # localizes some keys and not others (labels are discovered live,
        # a few at a time) would otherwise KeyError at use instead of
        # falling back. _ui_section refuses the *wholly absent* case, which
        # is not partial localization but a language nobody has recced yet.
        gemini_ui=_ui_section(
            rec, "gemini_ui", lang, ctx,
            {"add": "Add", "submit": "Submit", "delete_all": "Delete all"}),
        chatgpt_ui=_ui_section(
            rec, "chatgpt_ui", lang, ctx,
            {"personalization": "Personalization",
             "ci_placeholder_substr": "Additional behavior",
             "save": "Save",
             "toast_substr": "Custom instructions updated"}),
        card_goto_line=_need(rec, "card_goto_line", f"{ctx}.recording"),
        card_open_line=_need(rec, "card_open_line", f"{ctx}.recording"),
        account_label=_need(rec, "account_label", f"{ctx}.recording"),
        youtube_language=_need(yt, "video_language", f"{ctx}.youtube"),
        videos=videos,
        spellouts=core["spellouts"],
        intro_card_html=(_read(base / "cards" / "intro.html", ctx)
                         if require_later_assets else ""),
        outro_card_html=(_read(base / "cards" / "outro.html", ctx)
                         if require_later_assets else ""),
    )


def gemini_parts(cfg: LanguageConfig) -> tuple[str, str]:
    """The two Gemini saved-info paste blocks: header + the bullets up to
    `gemini_split_after`, then (optional prose lead-in +) the rest.
    Single source of truth — the prompt page's part blocks, the recording
    driver's clipboard asserts, and the tests all derive from this."""
    return split_prompt(cfg.prompt, cfg.gemini_part2_leadin,
                        cfg.gemini_split_after, cfg.lang)


def split_prompt(prompt: str, leadin: str, split_after: int,
                 ctx: str) -> tuple[str, str]:
    """The split itself, over plain text — so callers that hold the prompt
    without a fully-loaded config (the prompt-text tests, which cover
    languages whose UI recon hasn't happened yet) share this exact
    implementation rather than restating it."""
    bullets = prompt.split("\n- ")
    if len(bullets) != 7:
        raise ConfigError(
            f"[{ctx}] prompt must be header + 6 bullets for the "
            f"two-part split, found {len(bullets) - 1} bullets")
    if not 1 <= split_after <= 5:
        raise ConfigError(
            f"[{ctx}] gemini_split_after must leave both parts "
            f"non-empty (1-5), got {split_after}")
    p1 = bullets[0] + "\n- " + "\n- ".join(bullets[1:split_after + 1])
    tail = "- " + "\n- ".join(bullets[split_after + 1:])
    return p1, (leadin + "\n" + tail if leadin else tail)


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
