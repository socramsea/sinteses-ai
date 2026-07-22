from __future__ import annotations

import hashlib

from pydantic import BaseModel, Field


class JobRequest(BaseModel):
    topic: str = Field(..., min_length=4, description="Evento/tema do documentário")
    lang: str = "pt-BR"
    formats: list[str] = Field(default_factory=lambda: ["16:9", "9:16"])

    def idempotency_id(self) -> str:
        raw = f"{self.topic}|{self.lang}|{','.join(sorted(self.formats))}".encode()
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
