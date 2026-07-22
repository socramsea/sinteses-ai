"""Transforma o roteiro em plano de cenas (shot list) para o gerador de vídeo.

Cada cena => um prompt de geração + tipo de plano. Tipos de visual:
  - 'ai_clip'   : cena cinematográfica gerada (Kling/Veo) — reconstituição
  - 'geo'       : voo de mapa / diagrama geográfico (Earth Studio asset)
  - 'data'      : timeline / gráfico (data-viz)
A mistura é o diferencial do canal: explicação geográfica, não só 'imagem bonita'.
"""
from __future__ import annotations

from app.core.budget import guard_scene_count


def plan(script: dict) -> list[dict]:
    beats = script.get("beats", [])
    scenes: list[dict] = []
    for i, beat in enumerate(beats):
        scenes.append({
            "idx": i,
            "kind": beat.get("kind", "ai_clip"),     # ai_clip | geo | data
            "prompt": beat.get("visual_prompt", ""),
            "duration_s": float(beat.get("duration_s", 5)),
            "narration": beat.get("narration", ""),
            "source_ref": beat.get("source_ref"),     # índice em script['sources']
        })
    n = guard_scene_count(len(scenes))
    return scenes[:n]
