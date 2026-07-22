"""Narração via edge-tts (mesmo motor do NutriDeby). Async -> wrapper sync."""
from __future__ import annotations

import asyncio
from pathlib import Path

import edge_tts

VOICE_PTBR = "pt-BR-FranciscaNeural"   # voz grave, tom documentário


async def _synth(text: str, out_path: str, voice: str) -> None:
    await edge_tts.Communicate(text, voice).save(out_path)


def narrate(text: str, out_path: str, voice: str = VOICE_PTBR) -> str:
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    asyncio.run(_synth(text, out_path, voice))
    return out_path
