"""Video assembly: intro card + walkthrough clip + outro card, with TTS
narration segments mixed at the timeline positions from timing.py.

The ffmpeg filtergraph is ported as-is from the proven EN seed — do not
"simplify" it; the concat + adelay + amix structure with computed input
indices is load-bearing.
"""

import subprocess
from pathlib import Path

from .cards import render_card
from .config import LanguageConfig, OUT_DIR
from .timing import Timeline, plan_timeline, print_timeline
from .tts import media_duration, synthesize


def compute_timeline(cfg: LanguageConfig, video: str) -> tuple[Timeline, list[Path]]:
    """Synthesize (or fetch cached) narration and plan the timeline.

    Returns the timeline plus the wav paths aligned with timeline.all_cues.
    """
    v = cfg.videos[video]
    clip_dur = media_duration(cfg.clip_path(video))

    intro_wav = synthesize(v.intro_vo, cfg)
    seg_wavs = [synthesize(s.text, cfg) for s in v.segments]
    outro_wav = synthesize(v.outro_vo, cfg)

    tl = plan_timeline(
        intro_vo_dur=media_duration(intro_wav),
        clip_dur=clip_dur,
        segments=[(s.offset, media_duration(w), s.text)
                  for s, w in zip(v.segments, seg_wavs)],
        outro_vo_dur=media_duration(outro_wav),
        intro_text=v.intro_vo,
        outro_text=v.outro_vo,
    )
    return tl, [intro_wav, *seg_wavs, outro_wav]


def build_video(cfg: LanguageConfig, video: str) -> Path:
    v = cfg.videos[video]
    tl, wavs = compute_timeline(cfg, video)
    print_timeline(tl)

    intro_png = render_card(cfg, v, "intro")
    outro_png = render_card(cfg, v, "outro")
    clip = cfg.clip_path(video)

    vf_inputs = ["-loop", "1", "-t", str(tl.intro_s), "-i", str(intro_png),
                 "-i", str(clip),
                 "-loop", "1", "-t", str(tl.outro_len), "-i", str(outro_png)]
    af_inputs, amix, filt = [], [], []
    for i, (cue, wav) in enumerate(zip(tl.all_cues, wavs)):
        af_inputs += ["-i", str(wav)]
        ms = int(cue.start * 1000)
        filt.append(f"[{3+i}:a]adelay={ms}|{ms}[a{i}]")
        amix.append(f"[a{i}]")
    cell = ("fps=12,scale=1920:1080:force_original_aspect_ratio=decrease:"
            "flags=lanczos,pad=1920:1080:(ow-iw)/2:(oh-ih)/2:color=black,"
            "setsar=1")
    filter_complex = (
        f"[0:v]{cell}[v0];[1:v]{cell}[v1];[2:v]{cell}[v2];"
        "[v0][v1][v2]concat=n=3:v=1[vout];"
        + ";".join(filt) + ";"
        + "".join(amix)
        + f"amix=inputs={len(wavs)}:normalize=0[aout]")

    videos_dir = OUT_DIR / "videos" / cfg.lang
    videos_dir.mkdir(parents=True, exist_ok=True)
    out_path = videos_dir / f"youtube-{video}.mp4"
    subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error"] + vf_inputs + af_inputs +
        ["-filter_complex", filter_complex, "-map", "[vout]",
         "-map", "[aout]", "-t", str(tl.total), "-c:v", "libx264",
         "-pix_fmt", "yuv420p", "-crf", "20", "-c:a", "aac",
         "-b:a", "160k", str(out_path)], check=True)
    print("wrote", out_path)
    return out_path
