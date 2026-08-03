"""Resolução de voz por idioma (app/pipeline/narration.py).

O job bilíngue depende disto: `lang` do job precisa virar voz correspondente,
senão um roteiro em inglês sai narrado com voz pt-BR.
"""
import pytest

from app.pipeline import narration


@pytest.mark.parametrize("lang, esperado", [
    ("pt-BR", narration.VOICE_PTBR),
    ("pt-br", narration.VOICE_PTBR),
    ("pt", narration.VOICE_PTBR),
    ("en", narration.VOICE_EN),
    ("en-US", narration.VOICE_EN),
    ("en-GB", narration.VOICE_EN),      # variante desconhecida cai no prefixo
])
def test_voice_for_resolve_o_idioma(lang, esperado):
    assert narration.voice_for(lang) == esperado


@pytest.mark.parametrize("lang", [None, "", "   ", "klingon"])
def test_voice_for_nunca_estoura(lang):
    """Idioma ausente ou desconhecido degrada para o default, não quebra o job."""
    assert narration.voice_for(lang) == narration.DEFAULT_VOICE


def test_pt_e_en_resolvem_vozes_diferentes():
    assert narration.voice_for("pt-BR") != narration.voice_for("en")


def test_voice_explicito_ganha_do_lang(monkeypatch, tmp_path):
    """Quem passa voice manda; lang é só o fallback."""
    capturado = {}

    async def fake_synth(text, out_path, voice):
        capturado["voice"] = voice

    monkeypatch.setattr(narration, "_synth", fake_synth)
    destino = str(tmp_path / "vo.mp3")

    narration.narrate("texto", destino, voice="en-US-GuyNeural", lang="pt-BR")

    assert capturado["voice"] == "en-US-GuyNeural"


def test_narrate_usa_a_voz_do_lang_quando_voice_nao_vem(monkeypatch, tmp_path):
    capturado = {}

    async def fake_synth(text, out_path, voice):
        capturado["voice"] = voice

    monkeypatch.setattr(narration, "_synth", fake_synth)
    destino = str(tmp_path / "vo.mp3")

    narration.narrate("text", destino, lang="en")

    assert capturado["voice"] == narration.VOICE_EN
