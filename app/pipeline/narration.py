"""Narração via edge-tts (mesmo motor do NutriDeby). Async -> wrapper sync.

A voz é resolvida a partir do `lang` do job: um job em inglês narrado por voz
pt-BR era um bug silencioso — o texto saía traduzido, a locução não.
"""
from __future__ import annotations

import asyncio
from pathlib import Path

import edge_tts

VOICE_PTBR = "pt-BR-FranciscaNeural"   # voz grave, tom documentário
VOICE_EN = "en-US-AriaNeural"          # mesmo registro em inglês

# Chaves em minúsculas. O prefixo do idioma serve de fallback ("en-GB" -> "en"),
# então um lang novo degrada para a voz do idioma em vez de quebrar a narração.
VOICES: dict[str, str] = {
    "pt-br": VOICE_PTBR,
    "pt": VOICE_PTBR,
    "en-us": VOICE_EN,
    "en": VOICE_EN,
}
DEFAULT_VOICE = VOICE_PTBR


def voice_for(lang: str | None) -> str:
    """Resolve a voz do idioma do job. Idioma desconhecido cai no default."""
    key = (lang or "").strip().lower()
    if key in VOICES:
        return VOICES[key]
    return VOICES.get(key.split("-")[0], DEFAULT_VOICE)


async def _synth(text: str, out_path: str, voice: str) -> None:
    await edge_tts.Communicate(text, voice).save(out_path)


def narrate(
    text: str,
    out_path: str,
    voice: str | None = None,
    lang: str | None = None,
) -> str:
    """Narra `text` em `out_path`.

    `voice` explícito ganha de `lang`. Sem os dois, cai no default pt-BR — assim
    chamadores antigos no formato `narrate(text, path)` seguem funcionando.
    """
    chosen = voice or voice_for(lang)
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    asyncio.run(_synth(text, out_path, chosen))
    return out_path
