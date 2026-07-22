"""Estágio de pesquisa+roteiro via Anthropic, COM web_search (fatos atuais)."""
from __future__ import annotations

import json
from pathlib import Path

import anthropic

from app.config import settings

_SYSTEM = Path("prompts/research_system.md").read_text(encoding="utf-8")


def _system_blocks() -> list[dict]:
    block: dict = {"type": "text", "text": _SYSTEM}
    if settings.anthropic_enable_prompt_cache:
        block["cache_control"] = {"type": "ephemeral"}
    return [block]


def _extract_json(text: str) -> dict:
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end == -1:
        raise ValueError("modelo não retornou JSON")
    return json.loads(text[start:end + 1])


def build_script(topic: str, lang: str = "pt-BR") -> dict:
    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    msg = client.messages.create(
        model=settings.anthropic_model,
        max_tokens=8000,
        system=_system_blocks(),
        tools=[{"type": "web_search_20250305", "name": "web_search", "max_uses": 5}],
        messages=[{
            "role": "user",
            "content": f"Idioma: {lang}\nTema/evento: {topic}\n"
                       "Pesquise fontes reais e atuais (priorize USGS e agências oficiais) "
                       "e gere o roteiro do documentário em JSON, com as fontes citadas.",
        }],
    )
    text = "".join(b.text for b in msg.content if getattr(b, "type", "") == "text")
    return _extract_json(text)
