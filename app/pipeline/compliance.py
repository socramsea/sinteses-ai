"""Guard-rails de compliance — inegociáveis. Rodam ANTES e DEPOIS da geração.

Regras:
 1. Disclosure de IA queimado no vídeo (overlay) em todos os formatos.
 2. Toda afirmação factual precisa de fonte; sem fonte -> bloqueia render.
 3. Proibido modo 'photoreal' tentando passar IA como filmagem real de evento
    real (desinformação + política de plataforma). Visual de IA é sempre
    declarado como reconstituição/ilustração.
 4. Evento sensível (tragédia/vítimas) força enquadramento educativo e
    sinaliza risco de desmonetização pra revisão humana.
"""
from __future__ import annotations

from dataclasses import dataclass

from app.config import settings
from app.core.errors import ComplianceBlock

SENSITIVE_HINTS = (
    "terremoto", "tsunami", "acidente", "ataque", "guerra", "morte",
    "vítima", "vitima", "desastre", "incêndio", "incendio", "tragédia", "tragedia",
)


@dataclass
class ComplianceVerdict:
    sensitive: bool
    notes: list[str]


def pre_generation_check(topic: str, script: dict) -> ComplianceVerdict:
    notes: list[str] = []

    if settings.require_sources and not script.get("sources"):
        raise ComplianceBlock("roteiro sem fontes citadas — render bloqueado")

    if script.get("photoreal_real_event") and not settings.allow_photoreal_real_event:
        raise ComplianceBlock(
            "modo photoreal de evento real desabilitado: IA não pode se passar por filmagem real"
        )

    sensitive = any(h in topic.lower() for h in SENSITIVE_HINTS)
    if sensitive:
        notes.append("evento sensível: enquadramento educativo obrigatório; risco de desmonetização — revisar tom")
        notes.append("garantir respeito às vítimas; nada de sensacionalismo de catástrofe")

    return ComplianceVerdict(sensitive=sensitive, notes=notes)


def disclosure_overlay_spec() -> dict:
    """Spec do overlay que assembly.py queima em cada export."""
    return {
        "label": settings.ai_disclosure_label,
        "position": "bottom",
        "persistent": True,           # visível o vídeo inteiro, não só 1 frame
        "font": "DejaVuSans",
        "opacity": 0.85,
    }


def platform_flags() -> dict:
    """Flags pra setar no upload (disclosure de conteúdo alterado/sintético)."""
    return {"youtube_altered_content": True, "tiktok_ai_label": True, "meta_ai_label": True}
