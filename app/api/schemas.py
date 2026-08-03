from __future__ import annotations
import hashlib
from pydantic import BaseModel, Field


class Scene(BaseModel):
    """Cena pronta para o modo criativo (marketing). Alimenta o scene_director
    e o modelo image-to-video sem passar pela pesquisa factual."""
    visual_prompt: str = Field(..., min_length=8,
        description="Descrição visual: câmera (movimento), lente, luz, ação")
    duration_s: float = Field(2.0, ge=0.5, le=8.0,
        description="Duração-alvo da cena em segundos")
    overlay: str | None = Field(None,
        description="Sobreposição na montagem (ex.: tela do app, logo, legenda)")
    narration: str | None = Field(None,
        description="Texto de narração desta cena (opcional)")


class JobRequest(BaseModel):
    topic: str = Field(..., min_length=4,
        description="Evento/tema (documentary) ou nome do promo (creative)")
    lang: str = "pt-BR"
    formats: list[str] = Field(default_factory=lambda: ["16:9", "9:16"])
    # --- modo criativo (marketing) ---
    mode: str = Field("documentary",
        description="'documentary' = pesquisa+fonte; 'creative' = cenas prontas, sem fonte")
    scenes: list[Scene] | None = Field(None,
        description="Cenas prontas — obrigatório quando mode='creative'")
    disclosure: bool = Field(True,
        description="Mantém disclosure de IA (sempre recomendado)")

    def idempotency_id(self) -> str:
        scene_sig = ""
        if self.scenes:
            joined = "||".join(s.visual_prompt for s in self.scenes)
            scene_sig = "|" + hashlib.sha256(joined.encode()).hexdigest()[:8]
        raw = (f"{self.mode}|{self.topic}|{self.lang}|"
               f"{','.join(sorted(self.formats))}{scene_sig}").encode()
        return hashlib.sha256(raw).hexdigest()[:16]


class JobAccepted(BaseModel):
    job_id: str
    stage: str


class JobStatus(BaseModel):
    job_id: str
    stage: str
    cost_brl: float
    error: str | None = None
    artifacts: dict = {}
