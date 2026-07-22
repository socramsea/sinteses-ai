"""Multi-formato a partir do master 16:9.

Um render vira muitos: 16:9 longo (YouTube) + 9:16 (Shorts/Reels/TikTok).
9:16 usa crop central + barras seguras pra legenda.
"""
from __future__ import annotations

from pathlib import Path


TARGETS = {
    "16:9": (1920, 1080),
    "9:16": (1080, 1920),
    "1:1": (1080, 1080),
}


def export(master_path: str, formats: list[str], out_dir: str) -> dict[str, str]:
    from moviepy import VideoFileClip
    Path(out_dir).mkdir(parents=True, exist_ok=True)
    src = VideoFileClip(master_path)
    out: dict[str, str] = {}
    for fmt in formats:
        w, h = TARGETS[fmt]
        if fmt == "16:9":
            clip = src.resized((w, h))
        else:
            target_ratio = w / h
            cw = int(src.h * target_ratio)
            clip = src.cropped(x_center=src.w / 2, width=min(cw, src.w)).resized((w, h))
        path = str(Path(out_dir) / f"video_{fmt.replace(':', 'x')}.mp4")
        clip.write_videofile(path, fps=30, codec="libx264", audio_codec="aac")
        out[fmt] = path
    return out
