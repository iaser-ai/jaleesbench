"""TTS listen-test spike (plan phase tts_spike).

Generates the same short narration sample per language with each candidate
Gemini TTS voice, via the exact production code path (tts.gemini_generate).
A HUMAN listens and picks — the samples and printed table exist to make
that decision fast. Urdu is the flight risk: Gemini's documented TTS
language list has included Arabic and Indonesian but not Urdu, so the ur
samples decide whether the fallback chain (ElevenLabs -> Azure ur-PK ->
OpenAI TTS) gets evaluated at all.

Sample texts are SPIKE material only — short intro-style lines drafted for
voice evaluation. Production VO ships in later phases with the full
translation-review bar.
"""

from pathlib import Path

from .config import OUT_DIR
from .tts import gemini_generate, media_duration

SPIKE_MODEL = "gemini-3.1-flash-tts-preview"

# EN seed style, minus the trailing colon-space handling (kept identical).
SPIKE_STYLE = ("Say this as a warm, confident, genuinely engaging tutorial "
               "narrator — clearly glad to share it, good energy and "
               "momentum, but respectful and grounded, not hyped: ")

# Warm-tutorial candidates from the Gemini prebuilt voice roster, chosen to
# span character: Sulafat (warm), Achird (friendly), Charon (informative).
# Puck is the EN-shipped baseline, included for reference comparison.
CANDIDATE_VOICES = ("Sulafat", "Achird", "Charon", "Puck")

SAMPLE_TEXTS = {
    "ar": ("السلام عليكم! هل تودّ أن تجعل مساعدك الذكي رفيقًا إسلاميًا "
           "أفضل لك؟ إليك تغيير بسيط في الإعدادات يساعده على ذلك تمامًا — "
           "مدعوم ببحث حقيقي."),
    "ur": ("السلام علیکم! کیا آپ چاہتے ہیں کہ آپ کا اے آئی معاون آپ کے "
           "لیے ایک بہتر اسلامی ساتھی بنے؟ یہ ایک سادہ سی ترتیب کی تبدیلی "
           "ہے جو اس میں مدد دیتی ہے — حقیقی تحقیق کی بنیاد پر۔"),
    "id": ("Assalamualaikum! Apakah Anda ingin menjadikan asisten AI Anda "
           "sahabat Islami yang lebih baik? Berikut perubahan pengaturan "
           "sederhana yang membantunya melakukan itu — didukung riset "
           "yang nyata."),
}


def run_spike(langs: tuple[str, ...], voices: tuple[str, ...]) -> Path:
    """Generate lang x voice samples into out/spike/; return that dir."""
    out = OUT_DIR / "spike"
    out.mkdir(parents=True, exist_ok=True)
    rows = []
    for lang in langs:
        if lang not in SAMPLE_TEXTS:
            raise RuntimeError(
                f"no spike sample text for {lang!r} "
                f"(have: {', '.join(SAMPLE_TEXTS)})")
        for voice in voices:
            wav = out / f"{lang}-{voice.lower()}.wav"
            if not wav.exists():
                gemini_generate(SAMPLE_TEXTS[lang], SPIKE_STYLE, voice,
                                SPIKE_MODEL, wav)
            rows.append((lang, voice, media_duration(wav), wav))
            print(f"  {lang}  {voice:<8} {rows[-1][2]:5.1f}s  {wav}")
    print(f"\n{len(rows)} samples in {out} — listen and pick per language.")
    return out
