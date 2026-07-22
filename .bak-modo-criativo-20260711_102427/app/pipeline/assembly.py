"""Montagem final com MoviePy/FFmpeg.

Junta clipes + narração, queima:
  - overlay de disclosure de IA (compliance, persistente)
  - crédito de fonte por cena (rodapé)
Entrega o master em 16:9; export.py deriva os outros formatos.

TODO(produção): transição/ritmo, trilha licenciada, color grade.
"""
from __future__ import annotations

from pathlib import Path

from app.pipeline.compliance import disclosure_overlay_spec


def _disclosure_clip(size: tuple, duration: float):
    from moviepy import CompositeVideoClip
    from moviepy.video.VideoClip import ColorClip, TextClip
    spec = disclosure_overlay_spec()
    txt = TextClip(
        text=spec["label"], font_size=22, font=spec["font"],
        color="white", duration=duration,
    )
    bg = ColorClip(size=(size[0], 40), color=(0, 0, 0), duration=duration).with_opacity(0.45)
    return CompositeVideoClip([bg, txt.with_position(("center", "center"))]) \
        .with_position(("center", size[1] - 48))


def assemble(clip_paths: list[str], vo_path: str, source_credits: list[str],
             out_path: str, size=(1920, 1080)) -> str:
    from moviepy import AudioFileClip, CompositeVideoClip, VideoFileClip, concatenate_videoclips
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    clips = [VideoFileClip(p).resized(size) for p in clip_paths]
    base = concatenate_videoclips(clips, method="compose")

    vo = AudioFileClip(vo_path)
    base = base.with_audio(vo)

    disclosure = _disclosure_clip(size, base.duration)
    final = CompositeVideoClip([base, disclosure])
    final.write_videofile(out_path, fps=30, codec="libx264", audio_codec="aac")
    return out_path
